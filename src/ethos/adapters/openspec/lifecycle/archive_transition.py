"""Recognize the sole Lease-bound transition from active Change to archive."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.normalization.coercion import repository_path_matches
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment

_ARCHIVE_COMMITMENT = re.compile(
    r"^openspec/changes/archive/(20\d{2}-\d{2}-\d{2})-"
    r"([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)
_ACTIVE_COMMITMENT = re.compile(
    r"^openspec/changes/([a-z][a-z0-9]*(?:-[a-z0-9]+)*)/commitment\.toml$"
)


def _archive_context(root: Path) -> tuple[str, dict[str, object], Commitment] | None:
    branch = git_stdout(root, "branch", "--show-current")
    if load_branch_role_policy(root).role_for_branch(branch) != ROLE_WORK_LANE:
        return None
    head = current_tracked_head(root)
    lease = leases_by_branch(root).get(branch, {})
    if (
        lease.get("lease_state") != "valid"
        or lease.get("commitment_binding") != "bound"
        or lease.get("expected_head") != head
    ):
        return None
    try:
        return head, lease, load_lease_bound_commitment(root, lease=lease)
    except ValueError:
        return None


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
    context = _archive_context(root)
    if context is None:
        return None
    head, lease, source_commitment = context
    change = source_commitment.id.removeprefix("change:")
    if source_commitment.id == change or requested_change not in {None, change}:
        return None
    resolved = _archive_binding(
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
    active = _active_commitments(root, tree)
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
    if (
        archived.digest() != source_commitment.digest()
        or active != expected_active
        or completion_invalid
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
        carrier = _staged_archive_carrier(
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
        and _active_commitments(root, target_tree) == ()
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


def collision_preservation_path(path: str, tree: str, head: str) -> str:
    """Return the sole immutable preservation path for one archive collision."""
    suffix = hashlib.sha256(f"{tree}\0{head}".encode()).hexdigest()[:12]
    return f"{path}-{suffix}"


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
    match = _ARCHIVE_COMMITMENT.fullmatch(carrier)
    if match is None:
        return False, None
    active = f"openspec/changes/{match[2]}/commitment.toml"
    revisions = git_stdout(root, "rev-list", head, "--", active, carrier).splitlines()
    for revision in revisions:
        parents = run_git(root, "rev-list", "--parents", "-n", "1", revision).stdout.split()
        if len(parents) != 2:
            continue
        parent = parents[1]
        if not _exact_carrier_relocation(root, parent, revision, active, carrier):
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


def _archive_binding(
    root: Path,
    *,
    head: str,
    change: str,
    lease: dict[str, object],
    target_carrier: str = "",
) -> tuple[str, str, str] | None:
    carrier = str(lease.get("base_commitment_path") or "")
    if _valid_archive_carrier(carrier, change):
        return _bound_archive_binding(root, head=head, change=change, carrier=carrier)
    try:
        index_tree = run_git(root, "write-tree").stdout.strip()
        active_carrier = f"openspec/changes/{change}/commitment.toml"
        if carrier == active_carrier and carrier in _active_commitments(root, index_tree):
            target = exact_commitment_fields(
                root,
                head=index_tree,
                carrier=carrier,
                change_id=change,
            )
            expected = {
                name: str(lease.get(name) or "")
                for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
            }
            if all(target[name] == value for name, value in expected.items()):
                return "completion_transition", target["expected_tree"], carrier
        inferred_carrier = target_carrier or _staged_archive_carrier(
            root,
            head=head,
            tree=index_tree,
            lease=lease,
            change=change,
        )
        target = exact_commitment_fields(
            root,
            head=index_tree,
            carrier=inferred_carrier,
            change_id=change,
        )
    except ValueError:
        return None
    target_carrier = target["base_commitment_path"]
    expected = {
        name: str(lease.get(name) or "")
        for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
    }
    if not _valid_archive_carrier(target_carrier, change) or any(
        target[name] != value for name, value in expected.items()
    ):
        return None
    return "archive_transition", target["expected_tree"], target_carrier


def _staged_archive_carrier(
    root: Path,
    *,
    head: str,
    tree: str,
    lease: dict[str, object],
    change: str,
) -> str:
    active = f"openspec/changes/{change}/commitment.toml"
    if git_stdout(root, "rev-parse", f"{tree}:{active}"):
        message = "openspec_active_commitment_not_relocated"
        raise ValueError(message)
    listed = run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        tree,
        "--",
        "openspec/changes/archive",
        check=False,
    )
    if listed.returncode:
        message = "openspec_archive_tree_unreadable"
        raise ValueError(message)
    expected = {
        name: str(lease.get(name) or "")
        for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
    }
    candidates: list[str] = []
    for carrier in listed.stdout.splitlines():
        if not _valid_archive_carrier(carrier, change):
            continue
        before = git_stdout(root, "rev-parse", f"{head}:{carrier}")
        after = git_stdout(root, "rev-parse", f"{tree}:{carrier}")
        if before == after:
            continue
        try:
            target = exact_commitment_fields(
                root,
                head=tree,
                carrier=carrier,
                change_id=change,
            )
        except ValueError:
            continue
        if all(target[name] == value for name, value in expected.items()):
            candidates.append(carrier)
    if len(candidates) != 1:
        message = "lease_base_commitment_path_mismatch"
        raise ValueError(message)
    return candidates[0]


def _bound_archive_binding(
    root: Path,
    *,
    head: str,
    change: str,
    carrier: str,
) -> tuple[str, str, str] | None:
    source = f"openspec/changes/{change}/commitment.toml"
    if not git_stdout(root, "rev-parse", f"{head}:{source}"):
        return "post_archive_closeout", current_tree(root, head), carrier
    revisions = git_stdout(root, "rev-list", head, "--", source, carrier).splitlines()
    for revision in revisions:
        parents = run_git(root, "rev-list", "--parents", "-n", "1", revision).stdout.split()
        try:
            _commit, parent = parents
        except ValueError:
            continue
        if _exact_carrier_relocation(root, parent, revision, source, carrier):
            return "post_archive_closeout", current_tree(root, head), carrier
    return None


def _exact_carrier_relocation(
    root: Path,
    parent: str,
    revision: str,
    source: str,
    carrier: str,
) -> bool:
    """Recognize semantic carrier relocation without relying on Git rename heuristics."""
    source_blob = git_stdout(root, "rev-parse", f"{parent}:{source}")
    target_blob = git_stdout(root, "rev-parse", f"{revision}:{carrier}")
    source_after = git_stdout(root, "rev-parse", f"{revision}:{source}")
    return bool(source_blob and source_blob == target_blob and not source_after)


def _valid_archive_carrier(carrier: str, change: str) -> bool:
    match = _ARCHIVE_COMMITMENT.fullmatch(carrier)
    if match is None or match[2] != change:
        return False
    try:
        date.fromisoformat(match[1])
    except ValueError:
        return False
    return True


def _active_commitments(root: Path, tree: str) -> tuple[str, ...]:
    listed = run_git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        tree,
        "--",
        "openspec/changes",
        check=False,
    )
    if listed.returncode != 0:
        return ("unreadable",)
    return tuple(path for path in listed.stdout.splitlines() if _ACTIVE_COMMITMENT.fullmatch(path))


def _scope_report(
    root: Path,
    *,
    commitment: Commitment,
    change: str,
    carrier: str,
    state: str,
    changed_paths: tuple[str, ...],
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
    uncovered = [
        path
        for path in material
        if not any(repository_path_matches(path, pattern) for pattern in commitment.scope)
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
