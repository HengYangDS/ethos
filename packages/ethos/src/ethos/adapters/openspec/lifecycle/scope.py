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


def material_change_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    active_change_names: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Bind each declared material path to an official active Change companion.

    Scope completeness is a path-coverage invariant, not a global Change
    hygiene gate.  Missing or malformed companions remain diagnostic facts on
    their respective Change, but a changed material path is admitted whenever
    at least one official active or archiving Change supplies a valid matching
    companion.  The caller supplies names selected from the official OpenSpec
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
    )
    if not profile.exists:
        return _material_scope_payload(binding._replace(state="not_applicable"))
    if not profile.valid:
        return _material_scope_payload(
            binding._replace(required_gaps=("openspec_material_paths_profile_invalid",))
        )
    policy_payload = profile.tables.get("openspec")
    if _material_paths_missing(policy_payload):
        return _material_scope_payload(
            binding._replace(
                state="material_paths_missing",
                required_gaps=("openspec_material_paths_missing",),
            )
        )
    try:
        policy = AdopterOpenSpecPolicy.model_validate(policy_payload)
    except ValidationError:
        return _material_scope_payload(
            binding._replace(required_gaps=("openspec_material_paths_invalid",))
        )
    material_patterns = policy.material_paths
    material_paths = tuple(
        path
        for path in normalized_paths
        if any(_path_matches(path, pattern) for pattern in material_patterns)
    )
    if not material_paths:
        return _material_scope_payload(
            binding._replace(
                state="no_material_paths",
                material_patterns=material_patterns,
                material_paths=material_paths,
            )
        )
    changes = _change_scope_declarations(root, active_change_names=active_change_names)
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
    binding = binding._replace(
        material_patterns=material_patterns,
        material_paths=material_paths,
        changes=changes,
        advisory_gaps=diagnostics,
    )
    if bootstrap is not None:
        return _material_scope_payload(
            binding._replace(
                state="bootstrap_scope_creation",
                advisory_gaps=(),
                bootstrap=bootstrap,
            )
        )
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
    required_gaps = tuple(f"openspec_material_path_uncovered:{path}" for path in uncovered)
    return _material_scope_payload(
        binding._replace(
            state="covered" if not required_gaps else "uncovered",
            covered=tuple(covered),
            uncovered=tuple(uncovered),
            required_gaps=required_gaps,
        )
    )


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


def _material_paths_missing(policy_payload: object) -> bool:
    """Return whether an adopter has not made the required material declaration."""
    if not isinstance(policy_payload, dict) or "material_paths" not in policy_payload:
        return True
    paths = policy_payload.get("material_paths")
    return isinstance(paths, list) and not paths


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
        scope_path = change_root / "scope.toml"
        relative = scope_path.relative_to(root).as_posix()
        if not scope_path.exists():
            declarations.append(
                {
                    "name": change_root.name,
                    "state": "missing",
                    "scope_path": relative,
                    "paths": [],
                    "ok": False,
                    "required_gaps": [f"openspec_scope_missing:{change_root.name}"],
                }
            )
            continue
        try:
            declaration = ChangeScopeDeclaration.model_validate(
                tomllib.loads(scope_path.read_text(encoding="utf-8"))
            )
        except (OSError, tomllib.TOMLDecodeError, ValidationError):
            declarations.append(
                {
                    "name": change_root.name,
                    "state": "invalid",
                    "scope_path": relative,
                    "paths": [],
                    "ok": False,
                    "required_gaps": [f"openspec_scope_invalid:{change_root.name}"],
                }
            )
            continue
        declarations.append(
            {
                "name": change_root.name,
                "state": "active_or_archiving",
                "scope_path": relative,
                "paths": list(declaration.paths),
                "ok": True,
                "required_gaps": [],
            }
        )
    return tuple(declarations)


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
    }
