"""Attribute material changed paths to the selected official OpenSpec Change."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.normalization.coercion import repository_path_matches
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path


def material_change_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    active_change_names: tuple[str, ...] = (),
) -> dict[str, object]:
    """Attribute material paths when exactly one official Change owns the work."""
    paths, patterns, material, applicable = _scope_inputs(root, changed_paths)
    if not applicable:
        return _scope_report(paths, patterns, material, state="not_applicable")
    names = tuple(dict.fromkeys(active_change_names))
    if not material:
        return _scope_report(paths, patterns, material, state="no_material_paths")
    if len(names) != 1:
        gaps = (
            ["openspec_active_change_missing"]
            if not names
            else [f"openspec_active_change_ambiguous:{','.join(names)}"]
        )
        return _scope_report(paths, patterns, material, state="unattributed", gaps=gaps)
    change = names[0]
    owner = {"name": change, "path": f"openspec/changes/{change}"}
    covered: list[dict[str, object]] = [{"path": path, "changes": [change]} for path in material]
    return _scope_report(
        paths,
        patterns,
        material,
        changes=[owner],
        covered=covered,
        state="attributed",
    )


def _scope_inputs(
    root: Path, changed_paths: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], bool]:
    paths = tuple(dict.fromkeys(filter(None, changed_paths)))
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    policy = profile.declaration.openspec if profile.declaration else None
    patterns = policy.material_paths if policy else ()
    material = tuple(
        path for path in paths if any(repository_path_matches(path, glob) for glob in patterns)
    )
    return paths, patterns, material, policy is not None


def _scope_report(
    paths: tuple[str, ...],
    patterns: tuple[str, ...],
    material: tuple[str, ...],
    *,
    changes: list[dict[str, object]] | None = None,
    covered: list[dict[str, object]] | None = None,
    state: str,
    gaps: list[str] | None = None,
) -> dict[str, object]:
    required = gaps or []
    return {
        "verdict": "block" if required else "pass",
        "state": state,
        "changed_paths": list(paths),
        "material_patterns": list(patterns),
        "material_paths": list(material),
        "changes": changes or [],
        "covered_paths": covered or [],
        "uncovered_paths": [] if covered else list(material),
        "required_gaps": required,
        "advisory_gaps": [],
    }
