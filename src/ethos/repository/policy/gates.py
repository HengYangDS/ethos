from __future__ import annotations

import hashlib
import sys
import tomllib
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
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import RepositoryProfile

_PACKAGED_GATE_DECLARATION = load_gate_registry_declaration()


@dataclass(frozen=True, slots=True)
class ResolvedGatePolicy:
    """One profile-selected declaration, proof closure, and source-bound identity."""

    declaration: GateRegistryDeclaration
    profile: RepositoryProfile | None
    gates: tuple[Gate, ...]
    python_executable: str = sys.executable
    sources: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()
    gaps: tuple[str, ...] = ()

    @property
    def registry(self) -> dict[str, Gate]:
        return self.declaration.registry("runtime", python_executable=self.python_executable)

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

    @property
    def projection(self) -> dict[str, object]:
        """Return the exact policy projection bound by a transition plan."""
        sources = dict(self.sources)
        return {
            "owner": _owner_projection(self.declaration, self.profile),
            "gates": [gate_policy_fields(gate, sources.get(gate.id, ())) for gate in self.gates],
            "gaps": list(self.gaps),
        }

    @property
    def digest(self) -> str:
        return canonical_json_digest(self.projection)


def _owner_projection(
    declaration: GateRegistryDeclaration, profile: RepositoryProfile | None
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
        return {"kind": "registry", "path": proof.gate_registry, **identity}
    return {
        "kind": "profile",
        "code_correctness_gates": list(proof.code_correctness_gates),
        "code_correctness_map": dict(proof.code_correctness_map),
        **identity,
    }


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
                    "toolchain": "repository-native",
                    "execution_mode": "subprocess",
                    "tool_adapter": "repository-native",
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
    providers = tuple(
        f"src/{reference.partition(':')[0].replace('.', '/')}.py" for reference in gate.providers
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
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
) -> ResolvedGatePolicy:
    declaration, profile = _gate_declaration(
        profile,
        gate_registry_source=gate_registry_source,
    )
    if gate_ids:
        requested = set(gate_ids)
        owned = declaration.registry("runtime").keys()
        packaged = _PACKAGED_GATE_DECLARATION.registry("runtime").keys()
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
    payload = gate.model_dump(
        mode="json",
        exclude={"command", "providers", "registries"},
    )
    payload["execution_identity"] = list(gate_execution_identity(gate))
    payload["sources"] = [{"path": path, "sha256": digest} for path, digest in sources]
    return payload
