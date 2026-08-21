"""Bind material repository paths to exact Commitment scope."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.contracts.semantic import load_commitment_file
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_sequence
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


def material_change_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    active_change_names: tuple[str, ...] = (),
) -> dict[str, object]:
    """Report material paths covered by active Commitment declarations."""
    paths, patterns, material, applicable = _scope_inputs(root, changed_paths)
    if not applicable:
        return _scope_report(paths, patterns, material, state="not_applicable")
    changes = [commitment_report(root, name) for name in active_change_names]
    invalid = [gap for change in changes for gap in string_sequence(change.get("required_gaps"))]
    if not material:
        return _scope_report(
            paths,
            patterns,
            material,
            changes=changes,
            state="invalid" if invalid else "no_material_paths",
            gaps=invalid,
        )
    covered: list[dict[str, object]] = [
        {
            "path": path,
            "changes": [
                str(change.get("name", ""))
                for change in changes
                if change.get("verdict") == "pass"
                and any(
                    repository_path_matches(path, pattern)
                    for pattern in string_sequence(change.get("scope"))
                )
            ],
        }
        for path in material
    ]
    uncovered = [str(item["path"]) for item in covered if not item["changes"]]
    return _scope_report(
        paths,
        patterns,
        material,
        changes=changes,
        covered=[item for item in covered if item["changes"]],
        uncovered=uncovered,
        state="uncovered" if uncovered else "covered",
        gaps=[*invalid, *_uncovered_gaps(uncovered)],
    )


def prepared_change_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    change: str,
    commitment: Commitment,
) -> dict[str, object]:
    """Bind one exact prepared Change-start delta to its compiled Commitment."""
    paths, patterns, material, applicable = _scope_inputs(root, changed_paths)
    if not applicable:
        return _scope_report(paths, patterns, material, state="not_applicable")
    change_root = f"openspec/changes/{change}"
    effect_paths = {f"{change_root}/.openspec.yaml", f"{change_root}/commitment.toml"}
    uncovered = [
        path
        for path in material
        if path not in effect_paths
        and not any(repository_path_matches(path, pattern) for pattern in commitment.scope)
    ]
    changes: list[dict[str, object]] = [
        {"name": change, "path": change_root, "scope": list(commitment.scope)}
    ]
    return _scope_report(
        paths,
        patterns,
        material,
        changes=changes,
        covered=[{"path": path, "changes": [change]} for path in material if path not in uncovered],
        uncovered=uncovered,
        state="change_start_transition",
        gaps=_uncovered_gaps(uncovered),
    )


def commitment_report(root: Path, name: str) -> dict[str, object]:
    """Load one active Commitment and project only coverage facts."""
    try:
        load_commitment_file(root / ".ethos" / "commitment.toml")
        contract = load_commitment_file(root / "openspec" / "changes" / name / "commitment.toml")
    except (OSError, UnicodeError, TypeError, ValueError):
        return {
            "name": name,
            "verdict": "block",
            "scope": [],
            "required_gaps": [f"commitment_invalid:{name}"],
        }
    return {"name": name, "verdict": "pass", "scope": list(contract.scope), "required_gaps": []}


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
    uncovered: list[str] | None = None,
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
        "uncovered_paths": uncovered or [],
        "required_gaps": required,
        "advisory_gaps": [],
    }


def _uncovered_gaps(paths: list[str]) -> list[str]:
    return [f"openspec_material_path_uncovered:{path}" for path in paths]
