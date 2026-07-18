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
    """Immutable intermediate state for material Change-scope projection."""

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


def material_change_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    active_change_names: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Bind each declared material path to an official active Change companion.

    Scope completeness is a path-coverage invariant, not a global Change
    hygiene gate. Missing or malformed companions remain diagnostic facts on
    their respective Change, but a changed material path is admitted whenever
    at least one official active or archiving Change supplies a valid matching
    companion. The caller supplies names selected from the official OpenSpec
    list; direct diagnostics may omit that selection and inspect unarchived
    directories without changing the command-plane reader semantics.
    """
    profile = load_repository_profile(root)
    normalized_paths = tuple(dict.fromkeys(path for path in changed_paths if path))
    binding = MaterialScopeBinding(
        state="invalid",
        changed_paths=normalized_paths,
        material_patterns=(),
        material_paths=(),
        changes=(),
        covered=(),
        uncovered=(),
        required_gaps=(),
        advisory_gaps=(),
        bootstrap=None,
        profile_bootstrap=None,
    )
    if not profile.exists:
        binding = binding._replace(state="not_applicable")
    elif not profile.valid:
        binding = binding._replace(required_gaps=("openspec_material_paths_profile_invalid",))
    else:
        binding = _material_scope_binding_for_profile(
            root,
            binding=binding,
            policy_payload=profile.tables.get("openspec"),
            active_change_names=active_change_names,
        )
    return _material_scope_payload(binding)


def _material_scope_binding_for_profile(
    root: Path,
    *,
    binding: MaterialScopeBinding,
    policy_payload: object,
    active_change_names: tuple[str, ...] | None,
) -> MaterialScopeBinding:
    """Project scope coverage after confirming an adopter profile exists and parses."""
    profile_bootstrap = _profile_material_paths_bootstrap(
        root=root,
        changed_paths=binding.changed_paths,
        policy_payload=policy_payload,
        active_change_names=active_change_names,
    )
    if profile_bootstrap is not None:
        return binding._replace(
            state="profile_material_paths_bootstrap",
            profile_bootstrap=profile_bootstrap,
        )
    if _material_paths_missing(policy_payload):
        return binding._replace(
            state="material_paths_missing",
            required_gaps=("openspec_material_paths_missing",),
        )
    try:
        policy = AdopterOpenSpecPolicy.model_validate(policy_payload)
    except ValidationError:
        return binding._replace(required_gaps=("openspec_material_paths_invalid",))
    material_patterns = policy.material_paths
    material_paths = tuple(
        path
        for path in binding.changed_paths
        if any(_path_matches(path, pattern) for pattern in material_patterns)
    )
    binding = binding._replace(
        material_patterns=material_patterns,
        material_paths=material_paths,
    )
    if not material_paths:
        return binding._replace(state="no_material_paths")
    changes = _change_scope_declarations(root, active_change_names=active_change_names)
    changes = (
        *changes,
        *_current_archive_scope_declarations(root, binding.changed_paths),
    )
    bootstrap = _bootstrap_scope_creation(
        root=root,
        material_paths=material_paths,
        changes=changes,
    )
    diagnostics = tuple(
        str(gap)
        for change in changes
        for gaps in (change.get("required_gaps"),)
        if isinstance(gaps, (list, tuple))
        for gap in gaps
    )
    binding = binding._replace(changes=changes, advisory_gaps=diagnostics)
    if bootstrap is not None:
        return binding._replace(
            state="bootstrap_scope_creation",
            advisory_gaps=(),
            bootstrap=bootstrap,
        )
    covered, uncovered = _scope_coverage(material_paths, changes)
    required_gaps = tuple(f"openspec_material_path_uncovered:{path}" for path in uncovered)
    return binding._replace(
        state="covered" if not required_gaps else "uncovered",
        covered=covered,
        uncovered=uncovered,
        required_gaps=required_gaps,
    )


def _scope_coverage(
    material_paths: tuple[str, ...], changes: tuple[dict[str, object], ...]
) -> tuple[tuple[dict[str, object], ...], tuple[str, ...]]:
    """Return valid companion coverage per changed material path."""
    covered: list[dict[str, object]] = []
    uncovered: list[str] = []
    for path in material_paths:
        change_names = [
            str(change["name"])
            for change in changes
            for patterns in (change.get("paths"),)
            if change["ok"] is True
            and isinstance(patterns, (list, tuple))
            and any(_path_matches(path, str(pattern)) for pattern in patterns)
        ]
        if change_names:
            covered.append({"path": path, "changes": change_names})
        else:
            uncovered.append(path)
    return tuple(covered), tuple(uncovered)


def _bootstrap_scope_creation(
    *,
    root: Path,
    material_paths: tuple[str, ...],
    changes: tuple[dict[str, object], ...],
) -> dict[str, str] | None:
    """Recognize the sole bootstrap exception: one absent Change-local companion."""
    if len(material_paths) != 1:
        return None
    requested = material_paths[0]
    matches = [
        change
        for change in changes
        if change["state"] == "missing" and str(change["scope_path"]) == requested
    ]
    if len(matches) != 1:
        return None
    change = matches[0]
    change_root = root / "openspec" / "changes" / str(change["name"])
    if (
        not change_root.is_dir()
        or (change_root / "scope.toml").exists()
        or not _is_untracked_scope_path(root, requested)
    ):
        return None
    return {"change": str(change["name"]), "scope_path": requested}


def _profile_material_paths_bootstrap(
    *,
    root: Path,
    changed_paths: tuple[str, ...],
    policy_payload: object,
    active_change_names: tuple[str, ...] | None,
) -> dict[str, str] | None:
    """Admit only the one tracked profile write that adds a missing declaration.

    Existing adopters predate the material-scope contract.  They need one
    recoverable first write: add ``[openspec].material_paths`` to their
    already-tracked profile, then use the normal exact ``scope.toml`` bootstrap.
    The exception never treats an empty or malformed declaration as valid and
    never admits an adjacent material path.
    """
    profile_path = ".ethos/profile.toml"
    if not _material_declaration_absent(policy_payload):
        return None
    if changed_paths != (profile_path,) or not _is_tracked_path(root, profile_path):
        return None
    names = tuple(active_change_names or ())
    if len(names) != 1:
        return None
    change_name = names[0]
    change_root = root / "openspec" / "changes" / change_name
    if not change_root.is_dir():
        return None
    return {"change": change_name, "profile_path": profile_path}


def _is_untracked_scope_path(root: Path, path: str) -> bool:
    """Return whether the exact bootstrap companion has never entered Git's index."""
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 1


def _is_tracked_path(root: Path, path: str) -> bool:
    """Return whether a path is already tracked by Git."""
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def _material_paths_missing(policy_payload: object) -> bool:
    """Return whether an adopter has not made the required material declaration."""
    if not isinstance(policy_payload, dict) or "material_paths" not in policy_payload:
        return True
    paths = policy_payload.get("material_paths")
    return isinstance(paths, list) and not paths


def _material_declaration_absent(policy_payload: object) -> bool:
    """Return true only when a legacy profile has no declaration at all."""
    return not isinstance(policy_payload, dict) or "material_paths" not in policy_payload


def _change_scope_declarations(
    root: Path, *, active_change_names: tuple[str, ...] | None
) -> tuple[dict[str, object], ...]:
    """Read every unarchived Change-local scope companion deterministically."""
    changes_root = root / "openspec" / "changes"
    if not changes_root.exists():
        return ()
    declarations: list[dict[str, object]] = []
    selected = set(active_change_names) if active_change_names is not None else None
    for change_root in sorted(path for path in changes_root.iterdir() if path.is_dir()):
        if change_root.name == "archive":
            continue
        if selected is not None and change_root.name not in selected:
            continue
        declarations.append(_scope_declaration(root, change_root, state="active_or_archiving"))
    return tuple(declarations)


def _current_archive_scope_declarations(
    root: Path, changed_paths: tuple[str, ...]
) -> tuple[dict[str, object], ...]:
    """Read only archives that participate in the supplied current change scope."""
    archive_root = root / "openspec" / "changes" / "archive"
    if not archive_root.is_dir():
        return ()
    declarations: list[dict[str, object]] = []
    for change_root in sorted(path for path in archive_root.iterdir() if path.is_dir()):
        relative_root = change_root.relative_to(root).as_posix()
        if not any(
            path == relative_root or path.startswith(f"{relative_root}/") for path in changed_paths
        ):
            continue
        declarations.append(
            _scope_declaration(root, change_root, state="current_archive", archive=True)
        )
    return tuple(declarations)


def _scope_declaration(
    root: Path, change_root: Path, *, state: str, archive: bool = False
) -> dict[str, object]:
    """Read one active or current-archive scope companion fail-closed."""
    scope_path = change_root / "scope.toml"
    try:
        paths = list(
            ChangeScopeDeclaration.model_validate(
                tomllib.loads(scope_path.read_text(encoding="utf-8"))
            ).paths
        )
        issue = ""
    except (OSError, tomllib.TOMLDecodeError, ValidationError):
        paths = []
        issue = "missing" if not scope_path.exists() else "invalid"
    if archive and not issue:
        paths.append(f"{change_root.relative_to(root).as_posix()}/**")
    prefix = "openspec_archive_scope" if archive else "openspec_scope"
    return {
        "name": change_root.name,
        "state": state if not issue else f"{'archive_' if archive else ''}{issue}",
        "scope_path": scope_path.relative_to(root).as_posix(),
        "paths": paths,
        "ok": not issue,
        "required_gaps": [] if not issue else [f"{prefix}_{issue}:{change_root.name}"],
    }


def _path_matches(path: str, pattern: str) -> bool:
    """Match repository paths using the same trailing-`/**` semantics as plan."""
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatch.fnmatchcase(path, pattern)


def _material_scope_payload(binding: MaterialScopeBinding) -> dict[str, Any]:
    """Project one stable material Change-scope binding read model."""
    return {
        "ok": not binding.required_gaps,
        "state": binding.state,
        "changed_paths": list(binding.changed_paths),
        "material_patterns": list(binding.material_patterns),
        "material_paths": list(binding.material_paths),
        "changes": list(binding.changes),
        "covered_paths": list(binding.covered),
        "uncovered_paths": list(binding.uncovered),
        "required_gaps": list(binding.required_gaps),
        "advisory_gaps": list(binding.advisory_gaps),
        "bootstrap": binding.bootstrap or {},
        "profile_bootstrap": binding.profile_bootstrap or {},
    }
