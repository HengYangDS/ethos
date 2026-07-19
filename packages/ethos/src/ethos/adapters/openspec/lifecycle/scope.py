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

from ethos.repository.profile import load_repository_profile
from ethos_core.contracts.openspec.models import AdopterOpenSpecPolicy
from ethos_core.contracts.openspec.models import ChangeScopeDeclaration

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
    profile_bootstrap: dict[str, str] | None
    recovery: dict[str, str] | None


def _base_report(paths: tuple[str, ...]) -> dict[str, Any]:
    return {"ok": True, "state": "invalid", "changed_paths": list(paths), "material_patterns": [], "material_paths": [], "changes": [], "covered_paths": [], "uncovered_paths": [], "required_gaps": [], "advisory_gaps": [], "bootstrap": {}, "profile_bootstrap": {}, "recovery": {}}


def material_change_scope_report(root: Path, *, changed_paths: tuple[str, ...] = (), active_change_names: tuple[str, ...] | None = None) -> dict[str, Any]:
    """Bind each changed material path to a valid selected Change companion."""
    paths = tuple(dict.fromkeys(filter(None, changed_paths)))
    report = _base_report(paths)
    profile = load_repository_profile(root)
    if not profile.exists:
        report["state"] = "not_applicable"
        return report
    return _blocked(report, "openspec_material_paths_profile_invalid") if not profile.valid else _material_scope_report(root, paths, active_change_names, profile.tables.get("openspec"), report)


def _material_scope_report(root: Path, paths: tuple[str, ...], active_change_names: tuple[str, ...] | None, policy: object, report: dict[str, Any]) -> dict[str, Any]:
    if bootstrap := _profile_bootstrap(root, paths, policy, active_change_names):
        report.update(state="profile_material_paths_bootstrap", profile_bootstrap=bootstrap)
        return report
    if not isinstance(policy, dict) or "material_paths" not in policy or (isinstance(policy.get("material_paths"), list) and not policy.get("material_paths")):
        report["state"] = "material_paths_missing"
        return _blocked(report, "openspec_material_paths_missing")
    try:
        patterns = AdopterOpenSpecPolicy.model_validate(policy).material_paths
    except ValidationError:
        return _blocked(report, "openspec_material_paths_invalid")
    material = tuple(path for path in paths if any(_matches(path, glob) for glob in patterns))
    report.update(material_patterns=list(patterns), material_paths=list(material))
    if not material:
        report["state"] = "no_material_paths"
        return report
    changes = tuple(_declaration(root, path, state, archive) for path, state, archive in _change_roots(root, active_change_names, paths))
    report["changes"] = list(changes)
    report["advisory_gaps"] = [str(gap) for change in changes for gaps in (change.get("required_gaps"),) if isinstance(gaps, (list, tuple)) for gap in gaps]
    if exception := _scope_exception(root, material, changes):
        report.update(exception)
        return report
    covered = [{"path": path, "changes": [str(change["name"]) for change in changes for globs in (change.get("paths"),) if change["ok"] is True and isinstance(globs, (list, tuple)) and any(_matches(path, str(glob)) for glob in globs)]} for path in material]
    uncovered = [item["path"] for item in covered if not item["changes"]]
    report.update(state="uncovered" if uncovered else "covered", covered_paths=[item for item in covered if item["changes"]], uncovered_paths=uncovered, required_gaps=[f"openspec_material_path_uncovered:{path}" for path in uncovered], ok=not uncovered)
    return report


def _blocked(report: dict[str, Any], gap: str) -> dict[str, Any]:
    return report | {"ok": False, "required_gaps": [gap]}


def _profile_bootstrap(root: Path, paths: tuple[str, ...], policy: object, names: tuple[str, ...] | None) -> dict[str, str] | None:
    profile_path, selected = ".ethos/profile.toml", tuple(names or ())
    return {"change": selected[0], "profile_path": profile_path} if (not isinstance(policy, dict) or "material_paths" not in policy) and paths == (profile_path,) and _tracked(root, profile_path) and len(selected) == 1 and (root / "openspec" / "changes" / selected[0]).is_dir() else None


def _scope_exception(root: Path, paths: tuple[str, ...], changes: tuple[dict[str, object], ...]) -> dict[str, object] | None:
    if len(paths) != 1:
        return None
    requested = paths[0]
    matches = [change for change in changes if change["state"] == "missing" and str(change["scope_path"]) == requested]
    if len(matches) == 1:
        change = matches[0]
        change_root = root / "openspec" / "changes" / str(change["name"])
        if change_root.is_dir() and not (change_root / "scope.toml").exists() and _tracked(root, requested, expected=1):
            return {"state": "bootstrap_scope_creation", "advisory_gaps": [], "bootstrap": {"change": str(change["name"]), "scope_path": requested}}
    matches = [change for change in changes if change["state"] == "invalid" and str(change["scope_path"]) == requested]
    if len(matches) == 1 and _tracked(root, requested):
        return {"state": "tracked_scope_repair_admitted", "advisory_gaps": [], "recovery": {"change": str(matches[0]["name"]), "scope_path": requested}}
    return None


def _tracked(root: Path, path: str, *, expected: int = 0) -> bool:
    return subprocess.run(["git", "ls-files", "--error-unmatch", "--", path], cwd=root, text=True, capture_output=True, check=False).returncode == expected


def _change_roots(root: Path, names: tuple[str, ...] | None, changed_paths: tuple[str, ...]) -> tuple[tuple[Path, str, bool], ...]:
    changes_root, selected = root / "openspec" / "changes", set(names) if names is not None else None
    scans = ((changes_root, "active_or_archiving", False, lambda path: path.name != "archive" and (selected is None or path.name in selected)), (changes_root / "archive", "current_archive", True, lambda path: any(changed == relative or changed.startswith(f"{relative}/") for relative in (path.relative_to(root).as_posix(),) for changed in changed_paths)))
    return tuple((path, state, archive) for parent, state, archive, include in scans if parent.is_dir() for path in sorted(parent.iterdir()) if path.is_dir() and include(path))


def _declaration(root: Path, change_root: Path, state: str, archive: bool) -> dict[str, object]:  # noqa: FBT001
    scope_path = change_root / "scope.toml"
    try:
        paths, issue = list(ChangeScopeDeclaration.model_validate(tomllib.loads(scope_path.read_text(encoding="utf-8"))).paths), ""
    except (OSError, tomllib.TOMLDecodeError, ValidationError):
        paths, issue = [], "missing" if not scope_path.exists() else "invalid"
    if archive and not issue:
        paths.append(f"{change_root.relative_to(root).as_posix()}/**")
    prefix = "openspec_archive_scope" if archive else "openspec_scope"
    return {"name": change_root.name, "state": f"{'archive_' if archive else ''}{issue}" if issue else state, "scope_path": scope_path.relative_to(root).as_posix(), "paths": paths, "ok": not issue, "required_gaps": [] if not issue else [f"{prefix}_{issue}:{change_root.name}"]}


def _matches(path: str, pattern: str) -> bool:
    return path == pattern[:-3] or path.startswith(f"{pattern[:-3]}/") if pattern.endswith("/**") else fnmatch.fnmatchcase(path, pattern)
