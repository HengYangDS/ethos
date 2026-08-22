"""Recognize the sole Lease-bound transition from active Change to archive."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.openspec.lifecycle.archive_binding import active_commitments
from ethos.adapters.openspec.lifecycle.archive_binding import archive_binding
from ethos.adapters.openspec.lifecycle.archive_binding import archive_context
from ethos.adapters.openspec.lifecycle.archive_binding import collision_preservation_path
from ethos.adapters.openspec.lifecycle.archive_binding import exact_carrier_relocation
from ethos.adapters.openspec.lifecycle.archive_binding import staged_archive_carrier
from ethos.adapters.repo.commitment import commitment_binding_mismatch
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.normalization.coercion import repository_path_matches
from ethos.repository.openspec.identifiers import active_change_commitment
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import change_root_from_commitment
from ethos.repository.openspec.identifiers import parse_change_commitment
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


def lease_bound_archive_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    requested_change: str | None = None,
    official_change_complete: bool = False,
    completion_artifacts: tuple[str, ...] = (),
    preserved_archive: tuple[str, str] | None = None,
) -> dict[str, Any] | None:
    """Project the sole archive edge authorized by the current Work Lane Lease."""
    context = archive_context(root)
    if context is None:
        return None
    head, lease, source_commitment = context
    change = source_commitment.id.removeprefix("change:")
    if source_commitment.id == change or requested_change not in {None, change}:
        return None
    resolved = archive_binding(
        root,
        head=head,
        change=change,
        lease=lease,
        target_carrier=f"{preserved_archive[0]}/commitment.toml" if preserved_archive else "",
    )
    if resolved is None:
        return None
    state, tree, carrier = resolved
    try:
        archived = load_commitment(
            root,
            carrier=carrier,
            change_id=change,
            tree_ref=tree,
            expected_digest=str(lease.get("base_commitment_digest") or ""),
        )
    except ValueError:
        return None
    active = active_commitments(root, tree)
    expected_active = (carrier,) if state == "completion_transition" else ()
    changed = tuple(dict.fromkeys(filter(None, changed_paths)))
    preservation_valid, inferred_preservation = _archive_preservation_binding(
        root,
        state=state,
        head=head,
        tree=tree,
        carrier=carrier,
    )
    preserved_archive_invalid = not preservation_valid or (
        preserved_archive is not None and preserved_archive != inferred_preservation
    )
    completion_invalid = state == "completion_transition" and (
        not official_change_complete or len(changed) != 1 or changed[0] not in completion_artifacts
    )
    archive_invalid = state == "archive_transition" and (
        not official_change_complete or not completion_artifacts
    )
    if (
        archived.digest() != source_commitment.digest()
        or active != expected_active
        or completion_invalid
        or archive_invalid
        or preserved_archive_invalid
    ):
        return None
    return _scope_report(
        root,
        commitment=archived,
        change=change,
        carrier=carrier,
        state=state,
        changed_paths=changed_paths,
        completion_artifacts=completion_artifacts,
    )


def archive_postimage_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    requested_change: str,
    tree: str,
    source_head: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Select one exact official archive post-image without mutating the real index."""
    context = (
        archive_context(root, source_head=source_head)
        if source_head is not None
        else archive_context(root)
    )
    if context is None or not _requested_archive_context(context, requested_change):
        return None
    head, lease, source = context
    change = source.id.removeprefix("change:")
    try:
        carrier = staged_archive_carrier(
            root,
            head=head,
            tree=tree,
            lease=lease,
            change=change,
            environment=environment,
        )
        target = exact_commitment_fields(
            root,
            head=tree,
            carrier=carrier,
            change_id=change,
            environment=dict(environment or {}),
        )
        archived = load_commitment(
            root,
            carrier=carrier,
            change_id=change,
            tree_ref=tree,
            expected_digest=str(lease.get("base_commitment_digest") or ""),
            environment=dict(environment or {}),
        )
    except ValueError:
        return None

    def object_id(specification: str) -> str:
        observed = run_git(
            root,
            "rev-parse",
            specification,
            check=False,
            env=environment,
        )
        return observed.stdout.strip() if observed.returncode == 0 else ""

    active_root = active_change_root(change)
    archive_root = change_root_from_commitment(carrier)
    source_tree = git_stdout(root, "rev-parse", f"{head}:{active_root}")
    archive_tree = object_id(f"{tree}:{archive_root}")
    previous_archive_tree = git_stdout(root, "rev-parse", f"{head}:{archive_root}")
    preservation = ""
    if previous_archive_tree:
        preservation = collision_preservation_path(archive_root, previous_archive_tree, head)
        if object_id(f"{tree}:{preservation}") != previous_archive_tree:
            return None
    allowed = (f"{active_root}/", f"{archive_root}/", "openspec/specs/") + (
        (f"{preservation}/",) if preservation else ()
    )
    if (
        archived.digest() != source.digest()
        or archive_tree != source_tree
        or active_commitments(root, tree, environment=environment) != ()
        or commitment_binding_mismatch(target, lease)
        or not changed_paths
        or any(not path.startswith(allowed) for path in changed_paths)
    ):
        return None
    listed = run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        head,
        "--",
        active_root,
        check=False,
    )
    if listed.returncode:
        return None
    completion_artifacts = tuple(listed.stdout.splitlines())
    return _scope_report(
        root,
        commitment=archived,
        change=change,
        carrier=carrier,
        state="archive_transition",
        changed_paths=changed_paths,
        completion_artifacts=completion_artifacts,
    ) | {
        "tree": tree,
        "archive_path": archive_root,
        "completion_artifacts": list(completion_artifacts),
        **({"preserved_archive_path": preservation} if preservation else {}),
    }


def _requested_archive_context(
    context: tuple[str, dict[str, object], Commitment], requested_change: str
) -> bool:
    _head, _lease, source = context
    change = source.id.removeprefix("change:")
    return source.id != change and requested_change == change


def _archive_preservation_binding(
    root: Path,
    *,
    state: str,
    head: str,
    tree: str,
    carrier: str,
) -> tuple[bool, tuple[str, str] | None]:
    if state == "completion_transition":
        return True, None
    if state == "post_archive_closeout":
        return _post_archive_preservation_binding(root, head=head, carrier=carrier)
    return preserved_archive_binding(root, head=head, tree=tree, carrier=carrier)


def preserved_archive_binding(
    root: Path,
    *,
    head: str,
    tree: str,
    carrier: str,
) -> tuple[bool, tuple[str, str] | None]:
    archive = change_root_from_commitment(carrier)
    archive_tree = git_stdout(root, "rev-parse", f"{head}:{archive}")
    if not archive_tree:
        return True, None
    preserved = collision_preservation_path(archive, archive_tree, head)
    binding = (archive, preserved)
    return (
        _exact_preserved_archive(
            root,
            head=head,
            tree=tree,
            source=archive,
            target=preserved,
        ),
        binding,
    )


def _post_archive_preservation_binding(
    root: Path,
    *,
    head: str,
    carrier: str,
) -> tuple[bool, tuple[str, str] | None]:
    """Validate collision preservation at the exact archive commit in history."""
    parsed = parse_change_commitment(carrier)
    if parsed is None or parsed[1] is None:
        return False, None
    source = change_root_from_commitment(carrier)
    active = active_change_commitment(parsed[0])
    revisions = git_stdout(root, "rev-list", head, "--", active, carrier).splitlines()
    for revision in revisions:
        parents = run_git(root, "rev-list", "--parents", "-n", "1", revision).stdout.split()
        if len(parents) != 2:
            continue
        parent = parents[1]
        if not exact_carrier_relocation(root, parent, revision, active, carrier):
            continue
        source_tree = git_stdout(root, "rev-parse", f"{parent}:{source}")
        if not source_tree:
            return True, None
        preserved = collision_preservation_path(source, source_tree, parent)
        return (
            _exact_preserved_archive(
                root,
                head=parent,
                tree=current_tree(root, revision),
                source=source,
                target=preserved,
            ),
            (source, preserved),
        )
    return False, None


def _exact_preserved_archive(
    root: Path,
    *,
    head: str,
    tree: str,
    source: str,
    target: str,
) -> bool:
    source_tree = git_stdout(root, "rev-parse", f"{head}:{source}")
    replacement_tree = git_stdout(root, "rev-parse", f"{tree}:{source}")
    target_tree = git_stdout(root, "rev-parse", f"{tree}:{target}")
    return bool(source_tree and replacement_tree and source_tree == target_tree)


def _scope_report(
    root: Path,
    *,
    commitment: Commitment,
    change: str,
    carrier: str,
    state: str,
    changed_paths: tuple[str, ...],
    completion_artifacts: tuple[str, ...] = (),
) -> dict[str, Any]:
    profile = load_repository_profile(root)
    if (
        profile.state == "invalid"
        or profile.declaration is None
        or profile.declaration.openspec is None
    ):
        raise ValueError(INVALID_PROFILE_ERROR)
    patterns = profile.declaration.openspec.material_paths
    paths = tuple(dict.fromkeys(filter(None, changed_paths)))
    material = tuple(
        path for path in paths if any(repository_path_matches(path, glob) for glob in patterns)
    )
    authority_paths = {
        path: _archive_authority_path(
            root,
            path,
            change=change,
            carrier=carrier,
            state=state,
            completion_artifacts=completion_artifacts,
        )
        for path in material
    }
    uncovered = [
        path
        for path, authority_path in authority_paths.items()
        if not any(repository_path_matches(authority_path, pattern) for pattern in commitment.scope)
    ]
    covered = [{"path": path, "changes": [change]} for path in material if path not in uncovered]
    gaps = [f"openspec_material_path_uncovered:{path}" for path in uncovered]
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "changed_paths": list(paths),
        "material_patterns": list(patterns),
        "material_paths": list(material),
        "changes": [
            {
                "name": change,
                "path": change_root_from_commitment(carrier),
                "scope": list(commitment.scope),
            }
        ],
        "covered_paths": covered,
        "uncovered_paths": uncovered,
        "required_gaps": gaps,
        "advisory_gaps": [],
    }


def _archive_authority_path(
    root: Path,
    path: str,
    *,
    change: str,
    carrier: str,
    state: str,
    completion_artifacts: tuple[str, ...],
) -> str:
    """Map an official archive output to the active artifact that authorized it."""
    if state not in {"archive_transition", "post_archive_closeout"}:
        return path
    active_root = active_change_root(change)
    archive_root = change_root_from_commitment(carrier)
    if path == archive_root or path.startswith(f"{archive_root}/"):
        return active_root + path.removeprefix(archive_root)
    canonical_prefix = "openspec/specs/"
    if path.startswith(canonical_prefix):
        active_spec = f"{active_root}/specs/{path.removeprefix(canonical_prefix)}"
        if active_spec in completion_artifacts or (
            state == "post_archive_closeout"
            and git_stdout(
                root,
                "rev-parse",
                f"HEAD:{archive_root}/specs/{path.removeprefix(canonical_prefix)}",
            )
        ):
            return active_spec
    return path
