"""Repository material observation for deterministic gate policy compilation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import committed_file_bytes
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.repository.policy.gates import ResolvedGatePolicy
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.policy.gates import source_paths_for_gates
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path


def resolve_gate_policy(
    root: Path | None = None,
    *,
    tree_ref: str | None = None,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
) -> ResolvedGatePolicy:
    """Observe repository materials and compile one content-bound gate policy."""
    if root is None:
        return compile_gate_policy(gate_ids=gate_ids, full=full)
    profile = (
        load_committed_repository_profile(root, tree_ref)
        if tree_ref is not None
        else load_repository_profile(root)
    )
    registry_path = (
        profile.declaration.proof.gate_registry if profile.declaration is not None else None
    )
    registry_source = _material(root, tree_ref, registry_path) if registry_path else None
    initial = compile_gate_policy(
        profile=profile,
        gate_registry_source=registry_source,
        repository_python=_repository_python(root),
        gate_ids=gate_ids,
        full=full,
    )
    materials = {
        relative: _material(root, tree_ref, relative)
        for relative in source_paths_for_gates(initial.gates)
    }
    return compile_gate_policy(
        profile=profile,
        gate_registry_source=registry_source,
        source_materials=materials,
        repository_python=_repository_python(root),
        gate_ids=gate_ids,
        full=full,
    )


def _material(root: Path, tree_ref: str | None, relative: str) -> bytes | None:
    if tree_ref is not None:
        source = committed_file_bytes(root, tree_ref, relative)
        return source or None
    path = root / relative
    if path.is_symlink():
        return None
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved.read_bytes() if resolved.is_file() else None


def _repository_python(root: Path) -> str | None:
    candidates = (root / ".venv/bin/python", root / ".venv/Scripts/python.exe")
    return next((path.as_posix() for path in candidates if path.is_file()), None)
