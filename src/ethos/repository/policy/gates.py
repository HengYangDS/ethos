"""Resolve gate obligations and bind execution identities to selected sources."""

from __future__ import annotations

import hashlib
import sys
import tomllib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import bind_gate_command
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.proof.plan import AcceptancePurpose
from ethos.contracts.proof.plan import proof_acceptance_purpose
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.verdict import execution_succeeded
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.code_subjects import source_binding_gaps
from ethos.repository.policy.quality.obligations import INTEGRITY_PROVIDER
from ethos.repository.policy.quality.obligations import QUALITY_PROVIDERS
from ethos.repository.policy.quality.obligations import quality_obligation_gaps
from ethos.repository.policy.quality.obligations import quality_verifier_gaps
from ethos.repository.policy.quality.obligations import source_verifier_gaps
from ethos.repository.policy.quality.sources import source_contract_paths
from ethos.repository.policy.references.commands import python_module
from ethos.repository.policy.references.python_syntax import module_source_paths
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import SourceContract

if TYPE_CHECKING:
    from ethos.repository.policy.quality.dependency_acceptance import AuditScope

_PACKAGED_GATE_DECLARATION = load_gate_registry_declaration()
PRODUCT_PROVIDER_SOURCE = "@ethos/"


@dataclass(frozen=True, slots=True)
class ResolvedGatePolicy:
    """One profile-selected declaration, proof closure, and source-bound identity."""

    declaration: GateRegistryDeclaration
    profile: RepositoryProfile | None
    gates: tuple[Gate, ...]
    python_executable: str = sys.executable
    sources: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()
    gaps: tuple[str, ...] = ()
    repository_paths: tuple[str, ...] = ()
    script_paths: tuple[str, ...] = ()
    carrier_roles: tuple[tuple[str, str], ...] = ()
    acceptance_purpose: AcceptancePurpose = "repository"
    product_source: bool = False

    @property
    def registry(self) -> dict[str, Gate]:
        return self.declaration.registry(python_executable=self.python_executable)

    @property
    def gate_ids(self) -> tuple[str, ...]:
        return tuple(gate.id for gate in self.gates)

    @property
    def nodes(self) -> tuple[PlanNode, ...]:
        return TransitionPlan.closure(
            tuple(
                PlanNode(
                    id=gate.id,
                    kind="check",
                    command=gate_execution_identity(gate),
                    depends_on=gate.depends_on,
                )
                for gate in self.gates
            )
        )

    def result_gaps(self, checks: object, *, source_tree: str = "") -> tuple[str, ...]:
        """Require one successful, identity-matching result per declared obligation."""
        if not isinstance(checks, (list, tuple)) or any(
            not isinstance(check, Mapping) or not isinstance(check.get("action_id"), str)
            for check in checks
        ):
            return ("gate_results_invalid",)
        counts = Counter(check["action_id"] for check in checks)
        expected = {node.id: node.command for node in self.nodes}
        gaps = [f"gate_missing:{key}" for key in sorted(expected.keys() - counts.keys())]
        gaps += [f"gate_unknown:{key}" for key in sorted(counts.keys() - expected.keys())]
        gaps += [f"gate_duplicate:{key}" for key, count in sorted(counts.items()) if count != 1]
        for check in checks:
            name, command = check["action_id"], check.get("command")
            if name in expected and (
                not isinstance(command, (list, tuple)) or tuple(command) != expected[name]
            ):
                gaps.append(f"gate_identity_mismatch:{name}")
            if not execution_succeeded(check):
                gaps.append(f"gate_execution_not_proven:{name}")
        gaps.extend(quality_obligation_gaps(self.projection, checks, source_tree=source_tree))
        return tuple(gaps) if checks else ("gate_results_empty", *gaps)

    @property
    def projection(self) -> dict[str, object]:
        """Return the exact policy projection bound by a transition plan."""
        sources = dict(self.sources)
        return {
            "owner": _owner_projection(
                self.declaration,
                self.profile,
                self.repository_paths,
                self.script_paths,
                self.carrier_roles,
                product_source=self.product_source,
            ),
            "gates": [gate_policy_fields(gate, sources.get(gate.id, ())) for gate in self.gates],
            "gaps": list(self.gaps),
            **(
                {"acceptance_purpose": self.acceptance_purpose}
                if self.acceptance_purpose != "repository"
                else {}
            ),
        }

    @property
    def digest(self) -> str:
        return canonical_json_digest(self.projection)


def _owner_projection(
    declaration: GateRegistryDeclaration,
    profile: RepositoryProfile | None,
    repository_paths: tuple[str, ...],
    script_paths: tuple[str, ...],
    carrier_roles: tuple[tuple[str, str], ...],
    *,
    product_source: bool,
) -> dict[str, object]:
    identity: dict[str, object] = {
        "id": declaration.id,
        "schema_version": declaration.schema_version,
        "source_refs": list(declaration.source_refs),
    }
    if profile is None or profile.declaration is None:
        return {"kind": "packaged", **identity}
    proof = profile.declaration.proof
    contracts = [contract.model_dump(mode="json") for contract in proof.source_contracts]
    code_subjects = observed_code_subjects(
        repository_paths,
        script_paths=script_paths,
        roles=dict(carrier_roles),
        source_kinds=proof.source_kinds,
    )
    prerequisites = source_binding_gaps(code_subjects)
    if proof.gate_registry:
        owner: dict[str, object] = {"kind": "registry", "path": proof.gate_registry, **identity}
        if contracts:
            owner["source_contracts"] = contracts
        if prerequisites:
            owner["source_binding_gaps"] = list(prerequisites)
        if product_source:
            return owner
        axes = {
            axis: next(
                (
                    gate.id
                    for gate in declaration.gates
                    if any(
                        provider in (*gate.providers, *gate.verification_providers)
                        for provider in providers
                    )
                ),
                "",
            )
            for axis, providers in QUALITY_PROVIDERS.items()
        }
    else:
        owner = {
            "kind": "profile",
            "code_correctness_gates": list(proof.code_correctness_gates),
            **identity,
        }
        axes = dict(proof.code_correctness_map)
    if contracts:
        owner["source_contracts"] = contracts
    if prerequisites:
        owner["source_binding_gaps"] = list(prerequisites)
    # A declared code obligation survives incomplete carrier discovery.
    if code_subjects or any(axes.values()):
        owner["quality_floor_version"] = 2
        owner["code_correctness_map"] = {axis: axes.get(axis, "") for axis in QUALITY_PROVIDERS}
        owner["quality_subjects"] = {
            "behavior": [subject.path for subject in code_subjects if subject.requires_behavior],
            "static-analysis": [subject.path for subject in code_subjects],
        }
        owner["quality_carrier_roles"] = {
            subject.path: subject.role or ("test" if subject.is_test else "code")
            for subject in code_subjects
        }
    return owner


def _profile_declaration(profile: RepositoryProfile) -> GateRegistryDeclaration:
    declaration = profile.declaration
    if declaration is None:
        raise ValueError(INVALID_PROFILE_ERROR)
    proof = declaration.proof
    return GateRegistryDeclaration(
        id=f"profile:{declaration.profile_id}",
        proof_sets=GateProofSets(
            default=proof.code_correctness_gates,
            full=proof.code_correctness_gates,
        ),
        gates=tuple(
            gate.model_copy(
                update={
                    "profile": "repository",
                    "toolchain": "ethos"
                    if gate.providers or gate.verification_providers
                    else "repository-native",
                    "execution_mode": "verified-command"
                    if gate.verification_providers
                    else "provider"
                    if gate.providers
                    else "subprocess",
                    "tool_adapter": "ethos"
                    if gate.providers or gate.verification_providers
                    else "repository-native",
                }
            )
            for gate in proof.gates
        ),
    )


def resolve_gate_declaration(
    profile: RepositoryProfile | None,
    *,
    gate_registry_source: bytes | None = None,
) -> tuple[GateRegistryDeclaration, RepositoryProfile | None]:
    """Validate the selected native declaration without observing execution materials."""
    if profile is None:
        return _PACKAGED_GATE_DECLARATION, None
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    if profile.declaration is None:
        return _PACKAGED_GATE_DECLARATION, profile
    proof = profile.declaration.proof
    if not proof.gate_registry:
        return _profile_declaration(profile), profile
    try:
        if gate_registry_source is None:
            raise FileNotFoundError(proof.gate_registry)
        declaration = GateRegistryDeclaration.model_validate(
            tomllib.loads(gate_registry_source.decode())
        )
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValidationError, ValueError) as error:
        message = f"gate_registry_invalid:{proof.gate_registry}"
        raise ValueError(message) from error
    return declaration, profile


def provider_module_sources(gate: Gate) -> tuple[tuple[str, str], ...]:
    """Pair each invoked provider with its implementation source, not all gate materials."""
    provider_root = (
        PRODUCT_PROVIDER_SOURCE
        if gate.profile == "repository" and gate.tool_adapter == "ethos"
        else "src/ethos/"
    )
    return tuple(
        (
            reference,
            provider_root
            + reference.partition(":")[0].removeprefix("ethos.").replace(".", "/")
            + ".py",
        )
        for reference in (*gate.providers, *gate.verification_providers)
    )


def source_paths_for_gate(
    gate: Gate,
    *,
    repository_paths: tuple[str, ...] = (),
    source_contracts: tuple[SourceContract, ...] = (),
    source_materials: Mapping[str, bytes | None] | None = None,
) -> tuple[str, ...]:
    providers = provider_module_sources(gate)
    artifacts: tuple[str, ...] = ()
    for reference, source in providers:
        if reference == INTEGRITY_PROVIDER:
            prefix = source.removesuffix("adapters/gates/provenance/observation.py")
            artifacts = (
                prefix + "adapters/gates/provenance/archive.mjs",
                prefix + "adapters/repo/content/observation.py",
                prefix + "repository/policy/quality/sources.py",
                *source_contract_paths(source_contracts, source_materials or {}),
            )
    command = canonical_gate_command(gate.command)
    module = python_module(command)
    noxfile = ("noxfile.py", "pyproject.toml", "uv.lock") if module == "nox" else ()
    script = (
        (command[0],)
        if command
        and not noxfile
        and command[0] not in {"python", "ethos"}
        and "/" in command[0]
        and not Path(command[0]).is_absolute()
        and ".." not in Path(command[0]).parts
        else ()
    )
    module_sources = module_source_paths(module, repository_paths) if module and not noxfile else ()
    return tuple(
        dict.fromkeys(
            (
                *[path for _reference, path in providers],
                *artifacts,
                *noxfile,
                *(output.configuration for output in gate.native_outputs if output.configuration),
                *module_sources,
                *script,
            )
        )
    )


def source_paths_for_gates(
    gates: tuple[Gate, ...],
    *,
    repository_paths: tuple[str, ...] = (),
    source_contracts: tuple[SourceContract, ...] = (),
    source_materials: Mapping[str, bytes | None] | None = None,
) -> tuple[str, ...]:
    """Return the unique repository materials needed by a gate closure."""
    return tuple(
        dict.fromkeys(
            path
            for gate in gates
            for path in source_paths_for_gate(
                gate,
                repository_paths=repository_paths,
                source_contracts=source_contracts,
                source_materials=source_materials,
            )
        )
    )


def bind_gate_source_digests(
    gates: tuple[Gate, ...],
    materials: Mapping[str, bytes | None],
    *,
    repository_paths: tuple[str, ...] = (),
    source_contracts: tuple[SourceContract, ...] = (),
) -> tuple[tuple[tuple[str, tuple[tuple[str, str], ...]], ...], tuple[str, ...]]:
    """Bind gate sources from already-observed repository materials."""
    bound: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    gaps: list[str] = []
    for gate in gates:
        sources: list[tuple[str, str]] = []
        try:
            paths = source_paths_for_gate(
                gate,
                repository_paths=repository_paths,
                source_contracts=source_contracts,
                source_materials=materials,
            )
        except (ValueError, UnicodeError) as error:
            gaps.append(f"gate_policy_source_invalid:{gate.id}:{error}")
            paths = source_paths_for_gate(
                gate, repository_paths=repository_paths, source_contracts=source_contracts
            )
        for relative in paths:
            source = materials.get(relative)
            if source is None:
                gaps.append(f"gate_policy_source_missing:{gate.id}:{relative}")
            else:
                sources.append((relative, hashlib.sha256(source).hexdigest()))
        bound.append((gate.id, tuple(sources)))
    return tuple(bound), tuple(dict.fromkeys(gaps))


def resolve_gate_policy(
    *,
    profile: RepositoryProfile | None = None,
    gate_registry_source: bytes | None = None,
    source_materials: Mapping[str, bytes | None] | None = None,
    repository_python: str | None = None,
    repository_paths: tuple[str, ...] = (),
    script_paths: tuple[str, ...] = (),
    carrier_roles: tuple[tuple[str, str], ...] = (),
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
    acceptance_purpose: AcceptancePurpose = "repository",
    product_source: bool = False,
) -> ResolvedGatePolicy:
    acceptance_purpose = proof_acceptance_purpose({"acceptance_purpose": acceptance_purpose})
    declaration, profile = resolve_gate_declaration(
        profile,
        gate_registry_source=gate_registry_source,
    )
    if gate_ids:
        requested = set(gate_ids)
        owned = declaration.registry().keys()
        packaged = _PACKAGED_GATE_DECLARATION.registry().keys()
        if requested.isdisjoint(owned) and requested <= packaged:
            declaration, profile = _PACKAGED_GATE_DECLARATION, None
    if acceptance_purpose == "local-source":
        declaration = declaration.model_copy(
            update={
                "gates": tuple(
                    gate.model_copy(
                        update={"command": (*gate.command, "--", "--scope", "local-development")}
                    )
                    if native_dependency_audit_scope(gate.model_dump(mode="python"))
                    == "production-release"
                    else gate
                    for gate in declaration.gates
                )
            }
        )
    python_executable = repository_python or sys.executable
    gates = declaration.proof_gates(
        gate_ids,
        full=full,
        python_executable=python_executable,
    )
    sources, gaps = (
        bind_gate_source_digests(
            gates,
            source_materials or {},
            repository_paths=repository_paths,
            source_contracts=profile.declaration.proof.source_contracts,
        )
        if profile is not None and profile.declaration is not None
        else ((), ())
    )
    if acceptance_purpose == "local-source" and any(
        gate.id not in {selected.id for selected in gates}
        and native_dependency_audit_scope(gate.model_dump(mode="python")) == "local-development"
        for gate in declaration.proof_gates(full=True, python_executable=python_executable)
    ):
        gaps = (*gaps, "proof_dependency_acceptance_audit_missing")
    if (
        profile is not None
        and repository_python is None
        and any(
            python_module(canonical_gate_command(gate.command)) for gate in gates if gate.command
        )
    ):
        gaps = (*gaps, "gate_runtime_missing:repository-python")
    if profile is not None and profile.declaration is not None and not gates:
        gaps = (*gaps, "proof_floor_empty")
    if profile is not None and profile.declaration is not None:
        owner = _owner_projection(
            declaration,
            profile,
            repository_paths,
            script_paths,
            carrier_roles,
            product_source=product_source,
        )
        gaps = (
            *gaps,
            *quality_verifier_gaps(owner, tuple(gate_policy_fields(gate) for gate in gates)),
            *source_verifier_gaps(owner, gates),
        )
    return ResolvedGatePolicy(
        declaration,
        profile,
        gates,
        python_executable,
        sources,
        tuple(dict.fromkeys(gaps)),
        repository_paths,
        script_paths,
        carrier_roles,
        acceptance_purpose,
        product_source,
    )


def canonical_gate_command(command: tuple[str, ...]) -> tuple[str, ...]:
    """Remove only a host-specific absolute Python interpreter path."""
    if not command:
        return command
    head, *rest = command
    name = Path(head).name
    return ("python", *rest) if Path(head).is_absolute() and name.startswith("python") else command


def native_dependency_audit_scope(gate: Mapping[str, object]) -> AuditScope | None:
    """Select only the canonical audit owner and its explicit execution scope."""
    command = gate.get("execution_identity", gate.get("command"))
    if gate.get("tool_adapter") != "vulnerabilities" or not isinstance(command, tuple | list):
        return None
    identity = canonical_gate_command(bind_gate_command(tuple(command), sys.executable))
    native = ("python", "-m", "nox", "-s", "vulnerabilities")
    if identity in (native, (*native, "--", "--scope", "production-release")):
        return "production-release"
    return (
        "local-development" if identity == (*native, "--", "--scope", "local-development") else None
    )


def gate_execution_identity(gate: Gate) -> tuple[str, ...]:
    return canonical_gate_command(gate.command) if gate.command else ("provider", *gate.providers)


def gate_policy_fields(gate: Gate, sources: tuple[tuple[str, str], ...] = ()) -> dict[str, object]:
    payload = gate.to_dict()
    payload.pop("command" if gate.command else "providers")
    payload["execution_identity"] = list(gate_execution_identity(gate))
    payload["sources"] = [{"path": path, "sha256": digest} for path, digest in sources]
    return payload
