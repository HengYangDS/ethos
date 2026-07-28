"""Bind material repository paths to active Commitment scope."""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.semantic import load_commitment_file
from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.audit import change_tasks_complete
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path


def material_change_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    active_change_names: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Report material paths covered by active Commitment declarations."""
    paths = tuple(dict.fromkeys(filter(None, changed_paths)))
    report: dict[str, Any] = {
        "ok": True,
        "state": "invalid",
        "changed_paths": list(paths),
        "material_patterns": [],
        "material_paths": [],
        "changes": [],
        "covered_paths": [],
        "uncovered_paths": [],
        "required_gaps": [],
        "advisory_gaps": [],
    }
    profile = load_repository_profile(root)
    if not profile.exists:
        report["state"] = "not_applicable"
        return report
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    assert profile.declaration is not None
    if profile.declaration.openspec is None:
        report["state"] = "not_applicable"
        return report
    patterns = profile.declaration.openspec.material_paths
    material = tuple(path for path in paths if any(_matches(path, glob) for glob in patterns))
    report.update(material_patterns=list(patterns), material_paths=list(material))
    names = _active_change_names(root, active_change_names)
    changes = [commitment_report(root, name) for name in names]
    invalid_gaps = [
        gap for change in changes for gap in string_sequence(change.get("required_gaps"))
    ]
    if not material:
        report.update(
            ok=not invalid_gaps,
            state="invalid" if invalid_gaps else "no_material_paths",
            changes=changes,
            required_gaps=invalid_gaps,
        )
        return report
    covered: list[dict[str, object]] = [
        {
            "path": path,
            "changes": [
                str(change.get("name", ""))
                for change in changes
                if change.get("ok") is True
                and any(_matches(path, pattern) for pattern in string_sequence(change.get("scope")))
            ],
        }
        for path in material
    ]
    uncovered = [item["path"] for item in covered if not item["changes"]]
    report.update(
        ok=not uncovered,
        state="uncovered" if uncovered else "covered",
        changes=changes,
        covered_paths=[item for item in covered if item["changes"]],
        uncovered_paths=uncovered,
        required_gaps=[
            *invalid_gaps,
            *(f"openspec_material_path_uncovered:{path}" for path in uncovered),
        ],
    )
    report["ok"] = not report["required_gaps"]
    return report


def _active_change_names(root: Path, names: tuple[str, ...] | None) -> tuple[str, ...]:
    if names is not None:
        return names
    changes = root / "openspec" / "changes"
    return tuple(
        path.parent.name
        for path in sorted(changes.glob("*/commitment.toml"))
        if path.parent.name != "archive" and not change_tasks_complete(root, path.parent.name)
    )


def commitment_report(root: Path, name: str) -> dict[str, object]:
    """Load one active Commitment and project only coverage facts."""
    try:
        repository = load_commitment_file(root / ".ethos" / "commitment.toml")
        contract = load_commitment_file(
            root / "openspec" / "changes" / name / "commitment.toml",
            repository_id=repository.id,
        )
    except (OSError, UnicodeError, TypeError, ValueError):
        return {
            "name": name,
            "ok": False,
            "scope": [],
            "required_gaps": [f"commitment_invalid:{name}"],
        }
    return {"name": name, "ok": True, "scope": list(contract.scope), "required_gaps": []}


def _matches(path: str, pattern: str) -> bool:
    if pattern == "**":
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(path, pattern)
