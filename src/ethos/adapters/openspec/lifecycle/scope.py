"""Adopter material-path coverage for OpenSpec lifecycle reports."""

# ruff: noqa: E501 - source-budget closeout keeps equivalent scope tables compact.

from __future__ import annotations

import fnmatch
import subprocess
import tomllib
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from pydantic import ValidationError

from ethos.contracts.openspec.models import AdopterOpenSpecPolicy
from ethos.contracts.openspec.models import ChangeScopeDeclaration
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path

# fmt: off

class MaterialScopeBinding(NamedTuple):
    """Immutable intermediate state retained as a public compatibility type."""
    state: str
    changed_paths: tuple[str, ...]
    material_patterns: tuple[str, ...]
    material_paths: tuple[str, ...]
    changes: tuple[dict[str, object], ...]
    covered: tuple[dict[str, object], ...]
    uncovered: tuple[str, ...]
    required_gaps: tuple[str, ...]
    advisory_gaps: tuple[str, ...]
    bootstrap: dict[str, str] | None
    recovery: dict[str, str] | None


def _base_report(paths: tuple[str, ...]) -> dict[str, Any]:
    return {"ok": True, "state": "invalid", "changed_paths": list(paths), "material_patterns": [], "material_paths": [], "changes": [], "covered_paths": [], "uncovered_paths": [], "required_gaps": [], "advisory_gaps": [], "bootstrap": {}, "recovery": {}}


def material_change_scope_report(root: Path, *, changed_paths: tuple[str, ...] = (), active_change_names: tuple[str, ...] | None = None) -> dict[str, Any]:
    """Bind each changed material path to a valid selected Change companion."""
    paths = tuple(dict.fromkeys(filter(None, changed_paths)))
    report = _base_report(paths)
    profile = load_repository_profile(root)
    if not profile.exists:
        report["state"] = "not_applicable"
        return report
    if profile.state == "invalid":
        return _blocked(report, "openspec_material_paths_profile_invalid")
    assert profile.declaration is not None
    return _material_scope_report(root, paths, active_change_names, profile.declaration.openspec, report)


def _material_scope_report(root: Path, paths: tuple[str, ...], active_change_names: tuple[str, ...] | None, policy: AdopterOpenSpecPolicy, report: dict[str, Any]) -> dict[str, Any]:
    patterns = policy.material_paths
    material = tuple(path for path in paths if any(_matches(path, glob) for glob in patterns))
    report.update(material_patterns=list(patterns), material_paths=list(material))
    if not material:
        report["state"] = "no_material_paths"
        return report
    changes = tuple(_declaration(root, path, state, archive) for path, state, archive in _change_roots(root, active_change_names, paths))
    report["changes"] = list(changes)
    report["advisory_gaps"] = [str(gap) for change in changes for gaps in (change.get("required_gaps"),) if isinstance(gaps, (list, tuple)) for gap in gaps]
    if bootstrap := _bootstrap_scope_creation(root, material, changes):
        report.update(state="bootstrap_scope_creation", advisory_gaps=[], bootstrap=bootstrap)
        return report
    if recovery := _tracked_scope_repair(root, material, changes):
        report.update(state="tracked_scope_repair_admitted", advisory_gaps=[], recovery=recovery)
        return report
    covered = [{"path": path, "changes": [str(change["name"]) for change in changes for globs in (change.get("paths"),) if change["ok"] is True and isinstance(globs, (list, tuple)) and any(_matches(path, str(glob)) for glob in globs)]} for path in material]
    uncovered = [item["path"] for item in covered if not item["changes"]]
    report.update(state="uncovered" if uncovered else "covered", covered_paths=[item for item in covered if item["changes"]], uncovered_paths=uncovered, required_gaps=[f"openspec_material_path_uncovered:{path}" for path in uncovered], ok=not uncovered)
    return report


def _blocked(report: dict[str, Any], gap: str) -> dict[str, Any]:
    return report | {"ok": False, "required_gaps": [gap]}


def _bootstrap_scope_creation(root: Path, paths: tuple[str, ...], changes: tuple[dict[str, object], ...]) -> dict[str, str] | None:
    if len(paths) != 1:
        return None
    requested = paths[0]
    matches = [change for change in changes if change["state"] == "missing" and str(change["scope_path"]) == requested]
    if len(matches) != 1:
        return None
    change = matches[0]
    change_root = root / "openspec" / "changes" / str(change["name"])
    return {"change": str(change["name"]), "scope_path": requested} if change_root.is_dir() and not (change_root / "scope.toml").exists() and _untracked(root, requested) else None


def _tracked_scope_repair(root: Path, paths: tuple[str, ...], changes: tuple[dict[str, object], ...]) -> dict[str, str] | None:
    if len(paths) != 1:
        return None
    requested = paths[0]
    matches = [change for change in changes if change["state"] == "invalid" and str(change["scope_path"]) == requested]
    return {"change": str(matches[0]["name"]), "scope_path": requested} if len(matches) == 1 and _tracked(root, requested) else None


def _git_tracked_state(root: Path, path: str) -> int:
    return subprocess.run(["git", "ls-files", "--error-unmatch", "--", path], cwd=root, text=True, capture_output=True, check=False).returncode


def _untracked(root: Path, path: str) -> bool:
    return _git_tracked_state(root, path) == 1


def _tracked(root: Path, path: str) -> bool:
    return _git_tracked_state(root, path) == 0


def _change_roots(root: Path, names: tuple[str, ...] | None, changed_paths: tuple[str, ...]) -> tuple[tuple[Path, str, bool], ...]:
    changes_root, selected = root / "openspec" / "changes", set(names) if names is not None else None
    scans = ((changes_root, "active_or_archiving", False, lambda path: path.name != "archive" and (selected is None or path.name in selected)), (changes_root / "archive", "current_archive", True, lambda path: any(changed == relative or changed.startswith(f"{relative}/") for relative in (path.relative_to(root).as_posix(),) for changed in changed_paths)))
    return tuple((path, state, archive) for parent, state, archive, include in scans if parent.is_dir() for path in sorted(parent.iterdir()) if path.is_dir() and include(path))


def _declaration(root: Path, change_root: Path, state: str, archive: bool) -> dict[str, object]:  # noqa: FBT001
    scope_path = change_root / "scope.toml"
    try:
        paths, issue = list(ChangeScopeDeclaration.model_validate(tomllib.loads(scope_path.read_text(encoding="utf-8"))).paths), ""
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, ValidationError):
        paths, issue = [], "missing" if not scope_path.exists() else "invalid"
    if archive and not issue:
        paths.append(f"{change_root.relative_to(root).as_posix()}/**")
    prefix = "openspec_archive_scope" if archive else "openspec_scope"
    return {"name": change_root.name, "state": f"{'archive_' if archive else ''}{issue}" if issue else state, "scope_path": scope_path.relative_to(root).as_posix(), "paths": paths, "ok": not issue, "required_gaps": [] if not issue else [f"{prefix}_{issue}:{change_root.name}"]}


def _matches(path: str, pattern: str) -> bool:
    return path == pattern[:-3] or path.startswith(f"{pattern[:-3]}/") if pattern.endswith("/**") else fnmatch.fnmatchcase(path, pattern)
