"""Recognize the sole Lease-bound transition from active Change to archive."""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.openspec.lifecycle.scope import path_matches_scope
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import relocated_commitment_fields
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import exact_rename_target
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.openspec.audit import tasks_complete
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


def lease_bound_archive_scope_report(
    root: Path,
    *,
    changed_paths: tuple[str, ...] = (),
    requested_change: str | None = None,
) -> dict[str, Any] | None:
    """Project the sole archive edge authorized by the current Work Lane Lease."""
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
        source = load_lease_bound_commitment(root, lease=lease)
    except ValueError:
        return None
    change = source.id.removeprefix("change:")
    if source.id == change or requested_change not in {None, change}:
        return None
    resolved = _archive_binding(root, head=head, change=change, lease=lease)
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
    tasks_path = carrier.removesuffix("commitment.toml") + "tasks.md"
    if (
        archived.digest() != source.digest()
        or not tasks_complete(committed_file_text(root, tree, tasks_path))
        or _active_commitments(root, tree)
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


def _archive_binding(
    root: Path, *, head: str, change: str, lease: dict[str, object]
) -> tuple[str, str, str] | None:
    carrier = str(lease.get("base_commitment_path") or "")
    if _valid_archive_carrier(carrier, change):
        source = f"openspec/changes/{change}/commitment.toml"
        revisions = git_stdout(root, "rev-list", head, "--", source, carrier).splitlines()
        for revision in revisions:
            parents = run_git(root, "rev-list", "--parents", "-n", "1", revision).stdout.split()
            if (
                len(parents) == 2
                and exact_rename_target(root, parents[1], revision, source) == carrier
            ):
                return "post_archive_closeout", current_tree(root, head), carrier
        return None
    try:
        index_tree = run_git(root, "write-tree").stdout.strip()
        target = relocated_commitment_fields(
            root,
            old_head=head,
            new_head=index_tree,
            lease=lease,
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
        path for path in paths if any(path_matches_scope(path, glob) for glob in patterns)
    )
    uncovered = [
        path
        for path in material
        if not any(path_matches_scope(path, pattern) for pattern in commitment.scope)
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
