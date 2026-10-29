"""Resolve gate obligations and bind execution identities to selected sources."""

from __future__ import annotations

import hashlib
import sys
import tomllib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from ethos.contracts.gates import DECLARATION_PATH
from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.proof.plan import AcceptancePurpose
from ethos.contracts.proof.plan import proof_acceptance_purpose
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.verdict import execution_succeeded
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.code_subjects import source_binding_gaps
from ethos.repository.policy.quality.dependency_acceptance import native_dependency_audit_scope
from ethos.repository.policy.quality.gate_composition import canonical_gate_command
from ethos.repository.policy.quality.gate_composition import select_gate_declaration
from ethos.repository.policy.quality.obligations import QUALITY_PROVIDERS
from ethos.repository.policy.quality.obligations import quality_obligation_gaps
from ethos.repository.policy.quality.obligations import quality_verifier_gaps
from ethos.repository.policy.quality.obligations import source_verifier_gaps
from ethos.repository.policy.quality.sources import source_paths_for_gate
from ethos.repository.policy.quality.sources import source_paths_for_gates
from ethos.repository.policy.quality.tool_configuration import native_tool_configuration
from ethos.repository.policy.references.commands import python_module
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import SourceContract

_PACKAGED_GATE_DECLARATION = load_gate_registry_declaration()
_NATIVE_DEPENDENCY_AUDIT_COMMAND = ("python", "-m", "nox", "-s", "vulnerabilities")


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
    selected_obligations: bool = False

    @property
    def registry(self) -> dict[str, Gate]:
        """Overlay selected execution while retaining native declaration authority."""
        return {
            identity: _execution_gate(gate, self.acceptance_purpose)
            for identity, gate in self.declaration.registry(
                python_executable=self.python_executable
            ).items()
        } | {gate.id: gate for gate in self.gates}

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
                self.gates if self.selected_obligations else None,
            ),
            "gates": [gate_policy_fields(gate, sources.get(gate.id, ())) for gate in self.gates],
            "gaps": list(self.gaps),
            **(
                {"acceptance_purpose": self.acceptance_purpose}
                if self.acceptance_purpose != "repository"
                else {}
            ),
            **({"obligation_scope": "selected"} if self.selected_obligations else {}),
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
    selected_gates: tuple[Gate, ...] | None = None,
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
    if proof.gate_registry:
        owner: dict[str, object] = {"kind": "registry", "path": proof.gate_registry, **identity}
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
    if selected_gates is not None:
        inputs = set(
            source_paths_for_gates(
                selected_gates,
                repository_paths=repository_paths,
                source_contracts=proof.source_contracts,
            )
        )
        # A gate's own implementation is an input, not a checked subject; what the selected gates
        # verify decides whether code obligations apply.
        code_selected = any(
            gate.id in axes.values() or set(gate.dimensions).intersection(QUALITY_PROVIDERS)
            for gate in selected_gates
        )
        if not code_selected:
            code_subjects, axes = (), {}
            selected_ids = {gate.id for gate in selected_gates}
            contracts = [
                contract.model_dump(mode="json")
                for contract in proof.source_contracts
                if contract.integrity_gate in selected_ids or inputs.intersection(contract.members)
            ]
    prerequisites = source_binding_gaps(code_subjects)
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
    return _registry_declaration(gate_registry_source, proof.gate_registry), profile


def _registry_declaration(source: bytes | None, path: str) -> GateRegistryDeclaration:
    """Parse a declared or a supplied packaged registry by the same native contract."""
    try:
        if source is None:
            raise FileNotFoundError(path)
        return GateRegistryDeclaration.model_validate(tomllib.loads(source.decode()))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValidationError, ValueError) as error:
        message = f"gate_registry_invalid:{path}"
        raise ValueError(message) from error


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
        for tool in gate.tools:
            try:
                native_tool_configuration(repository_paths, tool)
            except ValueError as error:
                gaps.append(f"gate_policy_source_invalid:{gate.id}:{error}")
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
    packaged_registry_source: bytes | None = None,
    source_materials: Mapping[str, bytes | None] | None = None,
    repository_python: str | None = None,
    repository_paths: tuple[str, ...] = (),
    script_paths: tuple[str, ...] = (),
    carrier_roles: tuple[tuple[str, str], ...] = (),
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
    acceptance_purpose: AcceptancePurpose = "repository",
    selected_obligations: bool = False,
) -> ResolvedGatePolicy:
    acceptance_purpose = proof_acceptance_purpose({"acceptance_purpose": acceptance_purpose})
    selected_obligations = selected_obligations and bool(gate_ids) and not full
    declaration, profile = resolve_gate_declaration(
        profile,
        gate_registry_source=gate_registry_source,
    )
    selected = select_gate_declaration(
        declaration,
        gate_ids,
        _PACKAGED_GATE_DECLARATION
        if packaged_registry_source is None
        else _registry_declaration(packaged_registry_source, DECLARATION_PATH.as_posix()),
        repository_paths=repository_paths,
        full=full,
    )
    python_executable = repository_python or sys.executable
    gates = tuple(
        _execution_gate(gate, acceptance_purpose)
        for gate in selected.proof_gates(
            tuple(dict.fromkeys((*selected.proof_sets.full, *gate_ids))) if full else gate_ids,
            full=full,
            python_executable=python_executable,
        )
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
    selected_ids = {gate.id for gate in gates}
    if acceptance_purpose == "local-source" and any(
        gate.id not in selected_ids
        and native_dependency_audit_scope(
            _execution_gate(gate, acceptance_purpose).model_dump(mode="python")
        )
        == "local-development"
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
            gates if selected_obligations else None,
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
        selected_obligations,
    )


def _execution_gate(gate: Gate, purpose: AcceptancePurpose) -> Gate:
    """Bind native audit execution without changing declared quality ownership."""
    if (
        purpose == "local-source"
        and native_dependency_audit_scope(gate.model_dump(mode="python")) == "production-release"
    ):
        return gate.model_copy(
            update={
                "command": (
                    gate.command[0],
                    *_NATIVE_DEPENDENCY_AUDIT_COMMAND[1:],
                    "--",
                    "--scope",
                    "local-development",
                )
            }
        )
    return gate


def gate_execution_identity(gate: Gate) -> tuple[str, ...]:
    return canonical_gate_command(gate.command) if gate.command else ("provider", *gate.providers)


def gate_policy_fields(gate: Gate, sources: tuple[tuple[str, str], ...] = ()) -> dict[str, object]:
    payload = gate.to_dict()
    payload.pop("command" if gate.command else "providers")
    payload["execution_identity"] = list(gate_execution_identity(gate))
    payload["sources"] = [{"path": path, "sha256": digest} for path, digest in sources]
    return payload
