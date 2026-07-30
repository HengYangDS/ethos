from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from ethos.contracts.gates import GateDescriptor
from ethos.contracts.gates import GateEntry
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.normalization.coercion import string_mapping
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import load_repository_profile

_PACKAGED_GATE_DECLARATION = load_gate_registry_declaration()
_GIT = shutil.which("git") or "/usr/bin/git"


@dataclass(frozen=True, slots=True)
class ResolvedGatePolicy:
    """One profile-selected declaration, proof closure, and source-bound identity."""

    declaration: GateRegistryDeclaration
    profile: RepositoryProfile | None
    gates: tuple[GateDescriptor, ...]
    sources: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()
    gaps: tuple[str, ...] = ()

    @property
    def registry(self) -> dict[str, GateDescriptor]:
        return self.declaration.registry("runtime", python_executable=sys.executable)

    @property
    def gate_ids(self) -> tuple[str, ...]:
        return tuple(gate.id for gate in self.gates)

    @property
    def nodes(self) -> tuple[PlanNode, ...]:
        return tuple(
            PlanNode(
                id=gate.id,
                kind="check",
                command=gate.command,
                depends_on=gate.depends_on,
            )
            for gate in self.gates
        )

    @property
    def digest(self) -> str:
        sources = dict(self.sources)
        payload = {
            "owner": _owner_projection(self.declaration, self.profile),
            "gates": [gate_policy_fields(gate, sources.get(gate.id, ())) for gate in self.gates],
            "gaps": list(self.gaps),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def conformance_gaps(self, runs: object) -> list[str]:
        if not isinstance(runs, list):
            return []
        if self.gaps:
            return list(self.gaps)
        by_action = {
            str(payload.get("action_id", "")): payload
            for run in runs
            if isinstance(run, dict)
            for payload in (string_mapping(run),)
        }
        gaps: list[str] = []
        for gate in self.gates:
            run = by_action.get(gate.id)
            if run is None:
                continue
            raw_command = run.get("command")
            command = (
                tuple(str(token) for token in raw_command)
                if isinstance(raw_command, (list, tuple))
                else ()
            )
            if not (
                canonical_gate_command(command) == gate_execution_identity(gate)
                and run.get("trust_bearing") == gate.trust_bearing
                and run.get("evidence_class") == gate.evidence_class
            ):
                gaps.append(f"proof_gate_not_policy_conformant:{gate.id}")
        return gaps


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
        "required_gates": list(proof.required_gates),
        "code_axes": dict(proof.code_axes),
        **identity,
    }


def _git_blob(root: Path, tree_ref: str, path: str) -> bytes | None:
    completed = subprocess.run(
        [_GIT, "-C", str(root), "cat-file", "blob", f"{tree_ref}:{path}"],
        capture_output=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else None


def _local_blob(root: Path, relative: str) -> bytes | None:
    path = root / relative
    if path.is_symlink():
        return None
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved.read_bytes() if resolved.is_file() else None


def _blob(root: Path, tree_ref: str | None, relative: str) -> bytes | None:
    return (
        _git_blob(root, tree_ref, relative) if tree_ref is not None else _local_blob(root, relative)
    )


def _profile_declaration(profile: RepositoryProfile) -> GateRegistryDeclaration:
    declaration = profile.declaration
    if declaration is None:
        raise ValueError(INVALID_PROFILE_ERROR)
    proof = declaration.proof
    return GateRegistryDeclaration(
        id=f"profile:{declaration.profile_id}",
        proof_sets=GateProofSets(
            default=proof.required_gates,
            full=proof.required_gates,
        ),
        gates=tuple(
            GateEntry.model_validate(gate.model_dump() | {"registries": ("runtime",)})
            for gate in proof.gates
        ),
    )


def _gate_declaration(
    root: Path | None, *, tree_ref: str | None = None
) -> tuple[GateRegistryDeclaration, RepositoryProfile | None]:
    if root is None:
        return _PACKAGED_GATE_DECLARATION, None
    profile = load_repository_profile(root, tree_ref=tree_ref)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    if profile.declaration is None:
        return _PACKAGED_GATE_DECLARATION, profile
    proof = profile.declaration.proof
    if not proof.gate_registry:
        return _profile_declaration(profile), profile
    source = _blob(root, tree_ref, proof.gate_registry)
    try:
        if source is None:
            raise FileNotFoundError(proof.gate_registry)
        declaration = GateRegistryDeclaration.model_validate(tomllib.loads(source.decode()))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, ValidationError, ValueError) as error:
        message = f"gate_registry_invalid:{proof.gate_registry}"
        raise ValueError(message) from error
    return declaration, profile


def _source_paths(gate: GateDescriptor) -> tuple[str, ...]:
    providers = tuple(
        f"src/{reference.partition(':')[0].replace('.', '/')}.py" for reference in gate.providers
    )
    command = canonical_gate_command(gate.command)
    script = (
        (command[0],)
        if command
        and command[0] not in {"python", "ethos"}
        and "/" in command[0]
        and not Path(command[0]).is_absolute()
        and ".." not in Path(command[0]).parts
        else ()
    )
    return (*providers, *script)


def _bind_sources(
    root: Path | None,
    tree_ref: str | None,
    gates: tuple[GateDescriptor, ...],
) -> tuple[tuple[tuple[str, tuple[tuple[str, str], ...]], ...], tuple[str, ...]]:
    if root is None:
        return (), ()
    bound: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    gaps: list[str] = []
    for gate in gates:
        sources: list[tuple[str, str]] = []
        for relative in _source_paths(gate):
            source = _blob(root, tree_ref, relative)
            if source is None:
                gaps.append(f"gate_policy_source_missing:{gate.id}:{relative}")
            else:
                sources.append((relative, hashlib.sha256(source).hexdigest()))
        bound.append((gate.id, tuple(sources)))
    return tuple(bound), tuple(dict.fromkeys(gaps))


def resolve_gate_policy(
    root: Path | None = None,
    *,
    tree_ref: str | None = None,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
) -> ResolvedGatePolicy:
    declaration, profile = _gate_declaration(root, tree_ref=tree_ref)
    if gate_ids:
        requested = set(gate_ids)
        owned = declaration.registry("runtime").keys()
        packaged = _PACKAGED_GATE_DECLARATION.registry("runtime").keys()
        if requested.isdisjoint(owned) and requested <= packaged:
            declaration, profile = _PACKAGED_GATE_DECLARATION, None
    gates = declaration.proof_gates(
        gate_ids,
        full=full,
        python_executable=sys.executable,
    )
    source_root = root if profile is not None and profile.declaration is not None else None
    sources, gaps = _bind_sources(source_root, tree_ref, gates)
    if profile is not None and profile.declaration is not None and not gates:
        gaps = (*gaps, "proof_floor_empty")
    return ResolvedGatePolicy(declaration, profile, gates, sources, tuple(dict.fromkeys(gaps)))


def canonical_gate_command(command: tuple[str, ...]) -> tuple[str, ...]:
    """Remove only a host-specific absolute Python interpreter path."""
    if not command:
        return command
    head, *rest = command
    name = Path(head).name
    return ("python", *rest) if Path(head).is_absolute() and name.startswith("python") else command


def gate_execution_identity(gate: GateDescriptor) -> tuple[str, ...]:
    return canonical_gate_command(gate.command) if gate.command else ("provider", *gate.providers)


def gate_policy_fields(
    gate: GateDescriptor, sources: tuple[tuple[str, str], ...] = ()
) -> dict[str, object]:
    payload = gate.model_dump(mode="json", exclude={"command", "providers"})
    payload["execution_identity"] = list(gate_execution_identity(gate))
    payload["sources"] = [{"path": path, "sha256": digest} for path, digest in sources]
    return payload
