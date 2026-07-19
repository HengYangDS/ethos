"""Adopter material-path coverage for OpenSpec lifecycle reports."""

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


def material_change_scope_report(  # noqa: PLR0911, RUF100 - fail-closed scope exits preserve exact gaps
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    active_change_names: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Bind each changed material path to a valid selected Change companion."""
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
        "bootstrap": {},
        "profile_bootstrap": {},
    }
    profile = load_repository_profile(root)
    if not profile.exists:
        report["state"] = "not_applicable"
        return report
    if not profile.valid:
        return _blocked(report, "openspec_material_paths_profile_invalid")
    policy_payload = profile.tables.get("openspec")
    bootstrap = _profile_bootstrap(root, paths, policy_payload, active_change_names)
    if bootstrap:
        report.update(state="profile_material_paths_bootstrap", profile_bootstrap=bootstrap)
        return report
    if _material_paths_missing(policy_payload):
        report["state"] = "material_paths_missing"
        return _blocked(report, "openspec_material_paths_missing")
    try:
        patterns = AdopterOpenSpecPolicy.model_validate(policy_payload).material_paths
    except ValidationError:
        return _blocked(report, "openspec_material_paths_invalid")
    material = tuple(path for path in paths if any(_matches(path, glob) for glob in patterns))
    report.update(material_patterns=list(patterns), material_paths=list(material))
    if not material:
        report["state"] = "no_material_paths"
        return report
    changes = _declarations(root, active_change_names, paths)
    report["changes"] = list(changes)
    diagnostics = [
        str(gap)
        for change in changes
        for gaps in (change.get("required_gaps"),)
        if isinstance(gaps, (list, tuple))
        for gap in gaps
    ]
    report["advisory_gaps"] = diagnostics
    bootstrap = _scope_bootstrap(root, material, changes)
    if bootstrap:
        report.update(state="bootstrap_scope_creation", advisory_gaps=[], bootstrap=bootstrap)
        return report
    covered = [
        {
            "path": path,
            "changes": [
                str(change["name"])
                for change in changes
                for patterns in (change.get("paths"),)
                if change["ok"] is True
                and isinstance(patterns, (list, tuple))
                and any(_matches(path, str(glob)) for glob in patterns)
            ],
        }
        for path in material
    ]
    uncovered = [item["path"] for item in covered if not item["changes"]]
    report.update(
        state="uncovered" if uncovered else "covered",
        covered_paths=[item for item in covered if item["changes"]],
        uncovered_paths=uncovered,
        required_gaps=[f"openspec_material_path_uncovered:{path}" for path in uncovered],
        ok=not uncovered,
    )
    return report


def _blocked(report: dict[str, Any], gap: str) -> dict[str, Any]:
    report.update(ok=False, required_gaps=[gap])
    return report


def _profile_bootstrap(
    root: Path,
    paths: tuple[str, ...],
    policy: object,
    names: tuple[str, ...] | None,
) -> dict[str, str] | None:
    profile_path = ".ethos/profile.toml"
    selected = tuple(names or ())
    if (
        _material_declaration_absent(policy)
        and paths == (profile_path,)
        and _tracked(root, profile_path)
        and len(selected) == 1
        and (root / "openspec" / "changes" / selected[0]).is_dir()
    ):
        return {"change": selected[0], "profile_path": profile_path}
    return None


def _scope_bootstrap(
    root: Path,
    paths: tuple[str, ...],
    changes: tuple[dict[str, object], ...],
) -> dict[str, str] | None:
    if len(paths) != 1:
        return None
    requested = paths[0]
    matches = [
        change
        for change in changes
        if change["state"] == "missing" and change["scope_path"] == requested
    ]
    if len(matches) != 1:
        return None
    change = matches[0]
    change_root = root / "openspec" / "changes" / str(change["name"])
    if (
        change_root.is_dir()
        and not (change_root / "scope.toml").exists()
        and _tracked(root, requested, expected=1)
    ):
        return {"change": str(change["name"]), "scope_path": requested}
    return None


def _tracked(root: Path, path: str, *, expected: int = 0) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", path],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        ).returncode
        == expected
    )


def _material_paths_missing(policy: object) -> bool:
    if not isinstance(policy, dict):
        return True
    material_paths = policy.get("material_paths")
    return "material_paths" not in policy or (
        isinstance(material_paths, list) and not material_paths
    )


def _material_declaration_absent(policy: object) -> bool:
    return not isinstance(policy, dict) or "material_paths" not in policy


def _declarations(
    root: Path,
    names: tuple[str, ...] | None,
    changed_paths: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    changes_root = root / "openspec" / "changes"
    selected = set(names) if names is not None else None
    roots = (
        [
            (path, "active_or_archiving", False)
            for path in sorted(changes_root.iterdir())
            if path.is_dir()
            and path.name != "archive"
            and (selected is None or path.name in selected)
        ]
        if changes_root.exists()
        else []
    )
    archive_root = changes_root / "archive"
    if archive_root.is_dir():
        roots.extend(
            (path, "current_archive", True)
            for path in sorted(archive_root.iterdir())
            if path.is_dir()
            and any(
                changed == (relative := path.relative_to(root).as_posix())
                or changed.startswith(f"{relative}/")
                for changed in changed_paths
            )
        )
    return tuple(_declaration(root, path, state, archive) for path, state, archive in roots)


def _declaration(
    root: Path,
    change_root: Path,
    state: str,
    archive: bool,  # noqa: FBT001
) -> dict[str, object]:
    scope_path = change_root / "scope.toml"
    try:
        paths = list(
            ChangeScopeDeclaration.model_validate(
                tomllib.loads(scope_path.read_text(encoding="utf-8"))
            ).paths
        )
        issue = ""
    except (OSError, tomllib.TOMLDecodeError, ValidationError):
        paths, issue = [], "missing" if not scope_path.exists() else "invalid"
    if archive and not issue:
        paths.append(f"{change_root.relative_to(root).as_posix()}/**")
    prefix = "openspec_archive_scope" if archive else "openspec_scope"
    return {
        "name": change_root.name,
        "state": f"{'archive_' if archive else ''}{issue}" if issue else state,
        "scope_path": scope_path.relative_to(root).as_posix(),
        "paths": paths,
        "ok": not issue,
        "required_gaps": [] if not issue else [f"{prefix}_{issue}:{change_root.name}"],
    }


def _matches(path: str, pattern: str) -> bool:
    prefix = pattern[:-3] if pattern.endswith("/**") else None
    return (
        path == prefix or path.startswith(f"{prefix}/")
        if prefix is not None
        else fnmatch.fnmatchcase(path, pattern)
    )
