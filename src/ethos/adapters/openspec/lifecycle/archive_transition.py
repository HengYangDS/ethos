"""Recognize the sole Lease-bound transition from active Change to archive."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.openspec.lifecycle.archive_binding import ARCHIVE_COMMITMENT
from ethos.adapters.openspec.lifecycle.archive_binding import active_commitments
from ethos.adapters.openspec.lifecycle.archive_binding import archive_binding
from ethos.adapters.openspec.lifecycle.archive_binding import archive_context
from ethos.adapters.openspec.lifecycle.archive_binding import collision_preservation_path
from ethos.adapters.openspec.lifecycle.archive_binding import exact_carrier_relocation
from ethos.adapters.openspec.lifecycle.archive_binding import staged_archive_carrier
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.semantic import canonical_json_digest
from ethos.normalization.coercion import repository_path_matches
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment

_ARCHIVE_TRANSITION_ENV = "ETHOS_ARCHIVE_TRANSITION"
_ARCHIVE_TRANSITION_KEYS = frozenset(
    {
        "schema_version",
        "change",
        "head",
        "head_tree",
        "index_tree",
        "changed_paths",
        "completion_artifacts",
        "official_change_complete",
        "nonce",
    }
)


def archive_transition_environment(
    root: Path,
    *,
    change: str,
    head: str,
    changed_paths: tuple[str, ...],
    official_change_complete: bool,
    completion_artifacts: tuple[str, ...],
) -> dict[str, str]:
    """Bind one hook invocation to the exact admitted official archive delta."""
    payload: dict[str, object] = {
        "schema_version": 1,
        "change": change,
        "head": head,
        "head_tree": current_tree(root, head),
        "index_tree": run_git(root, "write-tree").stdout.strip(),
        "changed_paths": list(changed_paths),
        "completion_artifacts": list(completion_artifacts),
        "official_change_complete": official_change_complete,
    }
    payload["nonce"] = canonical_json_digest(payload)
    return {_ARCHIVE_TRANSITION_ENV: json.dumps(payload, sort_keys=True, separators=(",", ":"))}


def archive_transition_facts(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    requested_change: str | None,
) -> tuple[bool, tuple[str, ...]] | None:
    """Read exact, process-local archive facts only for their bound staged tree."""
    raw = os.environ.get(_ARCHIVE_TRANSITION_ENV, "")
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or set(payload) != _ARCHIVE_TRANSITION_KEYS:
        return None
    identity = {key: value for key, value in payload.items() if key != "nonce"}
    change = payload.get("change")
    artifacts = payload.get("completion_artifacts")
    paths = payload.get("changed_paths")
    head = current_tracked_head(root)
    valid = (
        payload.get("schema_version") == 1
        and isinstance(change, str)
        and bool(change)
        and requested_change in {None, change}
        and payload.get("head") == head
        and payload.get("head_tree") == current_tree(root, head)
        and payload.get("index_tree") == run_git(root, "write-tree").stdout.strip()
        and paths == list(changed_paths)
        and isinstance(artifacts, list)
        and all(isinstance(path, str) and path for path in artifacts)
        and payload.get("official_change_complete") is True
        and payload.get("nonce") == canonical_json_digest(identity)
    )
    return (True, tuple(artifacts)) if valid else None


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


def lease_bound_archive_transition_fields(
    root: Path,
    *,
    target_head: str,
) -> dict[str, str] | None:
    """Return the exact Lease-bound archive target from immutable Git facts."""
    branch = git_stdout(root, "branch", "--show-current")
    lease = leases_by_branch(root).get(branch, {})
    old_head = str(lease.get("expected_head") or "")
    if lease.get("lease_state") != "valid" or not old_head:
        return None
    try:
        source = load_lease_bound_commitment(root, lease=lease)
        change = source.id.removeprefix("change:")
        target_tree = current_tree(root, target_head)
        carrier = staged_archive_carrier(
            root,
            head=old_head,
            tree=target_tree,
            lease=lease,
            change=change,
        )
        target = exact_commitment_fields(
            root,
            head=target_head,
            carrier=carrier,
            change_id=change,
        )
        archived = load_commitment(
            root,
            carrier=carrier,
            change_id=change,
            tree_ref=target_tree,
        )
    except ValueError:
        return None
    preservation_valid, _binding = _preserved_archive_binding(
        root,
        head=old_head,
        tree=target_tree,
        carrier=carrier,
    )
    return (
        target
        if archived.digest() == source.digest()
        and active_commitments(root, target_tree) == ()
        and preservation_valid
        else None
    )


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
    return _preserved_archive_binding(root, head=head, tree=tree, carrier=carrier)


def _preserved_archive_binding(
    root: Path,
    *,
    head: str,
    tree: str,
    carrier: str,
) -> tuple[bool, tuple[str, str] | None]:
    archive = carrier.removesuffix("/commitment.toml")
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
    source = carrier.removesuffix("/commitment.toml")
    match = ARCHIVE_COMMITMENT.fullmatch(carrier)
    if match is None:
        return False, None
    active = f"openspec/changes/{match[2]}/commitment.toml"
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
                "path": carrier.removesuffix("/commitment.toml"),
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
    active_root = f"openspec/changes/{change}"
    archive_root = carrier.removesuffix("/commitment.toml")
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
