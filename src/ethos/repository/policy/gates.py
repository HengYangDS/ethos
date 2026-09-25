"""Resolve gate obligations and bind execution identities to selected sources."""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.verdict import execution_succeeded
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import RepositoryProfile

_PACKAGED_GATE_DECLARATION = load_gate_registry_declaration()
PRODUCT_PROVIDER_SOURCE = "@ethos/"
_QUALITY_PROVIDERS = {
    "behavior": (
        "ethos.adapters.gates.python_quality:behavior_report",
        "ethos.adapters.gates.code_quality:behavior_report",
    ),
    "static-analysis": (
        "ethos.adapters.gates.python_quality:static_report",
        "ethos.adapters.gates.code_quality:static_report",
    ),
}


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
            ),
            "gates": [gate_policy_fields(gate, sources.get(gate.id, ())) for gate in self.gates],
            "gaps": list(self.gaps),
        }

    @property
    def digest(self) -> str:
        return canonical_json_digest(self.projection)


def quality_obligation_gaps(
    policy: Mapping[str, object], checks: object, *, source_tree: str
) -> tuple[str, ...]:
    """Keep execution success distinct from evidence for observed code axes."""
    owner = policy.get("owner")
    if not isinstance(owner, Mapping):
        return ()
    version = owner.get("quality_floor_version")
    if version is None:
        return ()
    if version not in (1, 2):
        return (f"quality_floor_version_unsupported:{version}",)
    axes = owner.get("code_correctness_map")
    if not isinstance(axes, Mapping) or not axes:
        return ()
    gates = policy.get("gates")
    if not isinstance(gates, (list, tuple)) or not isinstance(checks, (list, tuple)):
        return tuple(f"quality_obligation_unproven:{axis}" for axis in axes)
    by_gate = {
        gate.get("id"): gate for gate in gates if isinstance(gate, Mapping) and gate.get("id")
    }
    by_check = {
        check.get("action_id"): check
        for check in checks
        if isinstance(check, Mapping) and check.get("action_id")
    }
    gaps: list[str] = []
    for axis, gate_id in axes.items():
        if (
            not isinstance(axis, str)
            or not isinstance(gate_id, str)
            or not _qualified_quality_check(
                by_gate.get(gate_id),
                by_check.get(gate_id),
                axis,
                source_tree,
                owner.get("quality_subjects"),
            )
        ):
            gaps.append(f"quality_obligation_unproven:{axis}")
    return tuple(gaps)


def _qualified_quality_check(
    gate: object, check: object, axis: str, source_tree: str, subjects: object
) -> bool:
    """Accept only a product provider's scoped native-evidence result."""
    if not isinstance(gate, Mapping) or not isinstance(check, Mapping) or not source_tree:
        return False
    identity = gate.get("execution_identity")
    if (
        gate.get("execution_mode") != "provider"
        or gate.get("tool_adapter") != "ethos"
        or not isinstance(identity, (list, tuple))
        or len(identity) < 2
        or identity[0] != "provider"
    ):
        return False
    providers = identity[1:]
    try:
        payload = json.loads(str(check.get("stdout") or ""))
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, Mapping) or payload.get("gate") != gate.get("id"):
        return False
    observations = payload.get("providers")
    if not isinstance(observations, list):
        return False
    return any(
        isinstance(item, Mapping)
        and item.get("provider") in providers
        and _quality_evidence_matches(item.get("report"), axis, source_tree, subjects)
        for item in observations
    )


def _quality_evidence_matches(
    report: object, axis: str, source_tree: str, subjects: object
) -> bool:
    if not isinstance(report, Mapping) or report.get("verdict") != "pass":
        return False
    evidence = report.get("quality_evidence")
    selected = evidence.get("selected_paths") if isinstance(evidence, Mapping) else None
    expected = subjects.get(axis) if isinstance(subjects, Mapping) else None
    return (
        isinstance(evidence, Mapping)
        and evidence.get("axis") == axis
        and evidence.get("source_tree") == source_tree
        and isinstance(selected, (list, tuple))
        and bool(selected)
        and all(isinstance(path, str) and path for path in selected)
        and (expected is None or list(selected) == expected)
    )


def _owner_projection(
    declaration: GateRegistryDeclaration,
    profile: RepositoryProfile | None,
    repository_paths: tuple[str, ...],
    script_paths: tuple[str, ...],
    carrier_roles: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    identity: dict[str, object] = {
        "id": declaration.id,
        "schema_version": declaration.schema_version,
        "source_refs": list(declaration.source_refs),
    }
    if profile is None or profile.declaration is None:
        return {"kind": "packaged", **identity}
    proof = profile.declaration.proof
    if proof.gate_registry:
        owner: dict[str, object] = {"kind": "registry", "path": proof.gate_registry, **identity}
        if declaration == _PACKAGED_GATE_DECLARATION:
            return owner
        axes = {
            axis: next(
                (
                    gate.id
                    for gate in declaration.gates
                    if any(provider in gate.providers for provider in providers)
                ),
                "",
            )
            for axis, providers in _QUALITY_PROVIDERS.items()
        }
    else:
        owner = {
            "kind": "profile",
            "code_correctness_gates": list(proof.code_correctness_gates),
            **identity,
        }
        axes = dict(proof.code_correctness_map)
    code_subjects = observed_code_subjects(
        repository_paths, script_paths=script_paths, roles=dict(carrier_roles)
    )
    # A declared code obligation survives incomplete carrier discovery.
    if code_subjects or any(axes.values()):
        owner["quality_floor_version"] = 2
        owner["code_correctness_map"] = {axis: axes.get(axis, "") for axis in _QUALITY_PROVIDERS}
        owner["quality_subjects"] = {
            "behavior": [subject.path for subject in code_subjects if not subject.is_test],
            "static-analysis": [subject.path for subject in code_subjects],
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
                    "toolchain": "ethos" if gate.providers else "repository-native",
                    "execution_mode": "provider" if gate.providers else "subprocess",
                    "tool_adapter": "ethos" if gate.providers else "repository-native",
                }
            )
            for gate in proof.gates
        ),
    )


def _gate_declaration(
    profile: RepositoryProfile | None,
    *,
    gate_registry_source: bytes | None = None,
) -> tuple[GateRegistryDeclaration, RepositoryProfile | None]:
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


def source_paths_for_gate(gate: Gate) -> tuple[str, ...]:
    provider_root = (
        PRODUCT_PROVIDER_SOURCE
        if gate.profile == "repository" and gate.tool_adapter == "ethos"
        else "src/ethos/"
    )
    providers = tuple(
        provider_root + reference.partition(":")[0].removeprefix("ethos.").replace(".", "/") + ".py"
        for reference in gate.providers
    )
    command = canonical_gate_command(gate.command)
    noxfile = (
        ("noxfile.py", "pyproject.toml", "uv.lock")
        if len(command) >= 3 and command[0] == "python" and command[1:3] == ("-m", "nox")
        else ()
    )
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
    return (*providers, *noxfile, *script)


def source_paths_for_gates(gates: tuple[Gate, ...]) -> tuple[str, ...]:
    """Return the unique repository materials needed by a gate closure."""
    return tuple(dict.fromkeys(path for gate in gates for path in source_paths_for_gate(gate)))


def bind_gate_source_digests(
    gates: tuple[Gate, ...],
    materials: dict[str, bytes | None],
) -> tuple[tuple[tuple[str, tuple[tuple[str, str], ...]], ...], tuple[str, ...]]:
    """Bind gate sources from already-observed repository materials."""
    bound: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    gaps: list[str] = []
    for gate in gates:
        sources: list[tuple[str, str]] = []
        for relative in source_paths_for_gate(gate):
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
    source_materials: dict[str, bytes | None] | None = None,
    repository_python: str | None = None,
    repository_paths: tuple[str, ...] = (),
    script_paths: tuple[str, ...] = (),
    carrier_roles: tuple[tuple[str, str], ...] = (),
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
) -> ResolvedGatePolicy:
    declaration, profile = _gate_declaration(
        profile,
        gate_registry_source=gate_registry_source,
    )
    if gate_ids:
        requested = set(gate_ids)
        owned = declaration.registry().keys()
        packaged = _PACKAGED_GATE_DECLARATION.registry().keys()
        if requested.isdisjoint(owned) and requested <= packaged:
            declaration, profile = _PACKAGED_GATE_DECLARATION, None
    python_executable = repository_python or sys.executable
    gates = declaration.proof_gates(
        gate_ids,
        full=full,
        python_executable=python_executable,
    )
    sources, gaps = (
        bind_gate_source_digests(gates, source_materials or {})
        if profile is not None and profile.declaration is not None
        else ((), ())
    )
    if (
        profile is not None
        and repository_python is None
        and any(canonical_gate_command(gate.command)[1:3] == ("-m", "nox") for gate in gates)
    ):
        gaps = (*gaps, "gate_runtime_missing:repository-python")
    if profile is not None and profile.declaration is not None and not gates:
        gaps = (*gaps, "proof_floor_empty")
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
    )


def canonical_gate_command(command: tuple[str, ...]) -> tuple[str, ...]:
    """Remove only a host-specific absolute Python interpreter path."""
    if not command:
        return command
    head, *rest = command
    name = Path(head).name
    return ("python", *rest) if Path(head).is_absolute() and name.startswith("python") else command


def gate_execution_identity(gate: Gate) -> tuple[str, ...]:
    return canonical_gate_command(gate.command) if gate.command else ("provider", *gate.providers)


def gate_policy_fields(gate: Gate, sources: tuple[tuple[str, str], ...] = ()) -> dict[str, object]:
    payload = gate.to_dict()
    payload.pop("command" if gate.command else "providers")
    payload["execution_identity"] = list(gate_execution_identity(gate))
    payload["sources"] = [{"path": path, "sha256": digest} for path, digest in sources]
    return payload
