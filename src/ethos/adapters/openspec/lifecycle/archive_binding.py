"""Recognize official OpenSpec archive roots and exact Git relocations."""

from __future__ import annotations

import hashlib

from ethos.normalization.coercion import repository_path_matches
from ethos.repository.openspec.identifiers import OPEN_SPEC_ARCHIVE_ROOT
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import parse_archived_change_root


def archived_change_from_path(path: str) -> tuple[str, str] | None:
    """Return the official archive root and logical Change containing ``path``."""
    prefix = f"{OPEN_SPEC_ARCHIVE_ROOT}/"
    if not path.startswith(prefix):
        return None
    parts = path.split("/", 4)
    candidate = "/".join(parts[:4]) if len(parts) >= 4 else path
    parsed = parse_archived_change_root(candidate)
    if parsed is None:
        return None
    return candidate, parsed[0]


def archive_root_from_path(path: str, change: str) -> str:
    """Return the official archive root containing ``path`` or ``""``."""
    parsed = archived_change_from_path(path)
    return parsed[0] if parsed is not None and parsed[1] == change else ""


def collision_preservation_path(path: str, tree: str, head: str) -> str:
    """Return the deterministic immutable preservation path for a collision."""
    suffix = hashlib.sha256(f"{tree}\0{head}".encode()).hexdigest()[:12]
    return f"{path}-{suffix}"


def archive_material_scope(
    paths: tuple[str, ...],
    patterns: tuple[str, ...],
    *,
    change: str,
    archive_root: str,
    completion_artifacts: tuple[str, ...],
    projection_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    """Compile archive coverage from completed source values, without reading authority."""
    active_root = active_change_root(change)
    active_prefix, delta_prefix = f"{active_root}/", f"{active_root}/specs/"
    destinations = set(projection_paths)
    for source in completion_artifacts:
        if source == active_root or source.startswith(active_prefix):
            destinations.add(archive_root + source.removeprefix(active_root))
        if source.startswith(active_prefix):
            destinations.add(source)
        if source.startswith(delta_prefix):
            destinations.add("openspec/specs/" + source.removeprefix(delta_prefix))
    material = tuple(
        path for path in paths if any(repository_path_matches(path, glob) for glob in patterns)
    )
    uncovered = [path for path in material if path not in destinations]
    gaps = [f"openspec_material_path_uncovered:{path}" for path in uncovered]
    return {
        "verdict": "block" if gaps else "pass",
        "state": "archive_transition",
        "changed_paths": list(paths),
        "material_patterns": list(patterns),
        "material_paths": list(material),
        "changes": [{"name": change, "path": archive_root}],
        "covered_paths": [
            {"path": path, "changes": [change]} for path in material if path in destinations
        ],
        "uncovered_paths": uncovered,
        "required_gaps": gaps,
        "advisory_gaps": [],
    }
