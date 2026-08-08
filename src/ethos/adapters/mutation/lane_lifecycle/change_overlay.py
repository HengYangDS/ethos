"""Admit an exact staged overlay into the next Change generation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypedDict

from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.normalization.coercion import repository_path_matches

if TYPE_CHECKING:
    from pathlib import Path


class ChangeOverlay(TypedDict):
    """Exact pre-transition overlay observation."""

    paths: tuple[str, ...]
    digest: str
    required_gaps: list[str]


def lifecycle_report(
    branch: str,
    head: str,
    state: str,
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    """Project the common lifecycle mutation result contract."""
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "branch": branch,
        "head": head,
        "required_gaps": list(dict.fromkeys(gaps)),
        **details,
    }


def work_lane_transition_gaps(
    root: Path,
    *,
    branch: str,
    head: str,
    expect_head: str,
    lease: dict[str, object],
    actor: str,
    role_gap: str,
    require_clean: bool = False,
) -> list[str]:
    """Validate the coordinates shared by OpenSpec lifecycle transitions."""
    checks = (
        (load_branch_role_policy(root).role_for_branch(branch) == ROLE_WORK_LANE, role_gap),
        (head == expect_head, "expect_head_mismatch"),
        (not require_clean or not git_stdout(root, "status", "--short"), "work_lane_dirty"),
        (lease.get("lease_state") == "valid", f"work_lane_lease_invalid:{branch}"),
        (lease.get("holder_ref") == actor, "lease_actor_mismatch"),
        (lease.get("expected_head") == head, "lease_head_stale"),
        (lease.get("expected_tree") == current_tree(root, head), "lease_tree_stale"),
    )
    return [gap for valid, gap in checks if not valid]


def advance_committed_lease(
    root: Path,
    *,
    branch: str,
    previous_head: str,
    head: str,
    failure_gap: str,
) -> dict[str, object]:
    """Apply or recognize the shared committed-ref Lease transition."""
    lease = leases_by_branch(root).get(branch, {})
    if lease.get("expected_head") == head:
        return lease
    transition = work_lane_ref_transition_report(
        root=root,
        phase="committed",
        ref_name=f"refs/heads/{branch}",
        old_value=previous_head,
        new_value=head,
    )
    if transition.get("verdict") != "pass":
        raise ValueError(failure_gap)
    return leases_by_branch(root).get(branch, {})


def change_overlay_report(
    root: Path,
    *,
    scope: tuple[str, ...],
    expected_digest: str,
    apply: bool,
) -> ChangeOverlay:
    """Bind a clean tree or one fully staged, scope-covered overlay."""
    paths = changed_paths(root)
    if not paths:
        return {"paths": (), "digest": "", "required_gaps": []}
    unstaged = tuple(git_stdout(root, "diff", "--name-only", "--").splitlines())
    staged = tuple(git_stdout(root, "diff", "--cached", "--name-only", "--").splitlines())
    digest = dirty_content_sha256(root)
    gaps: list[str] = []
    if unstaged or set(staged) != set(paths):
        gaps.append("openspec_change_overlay_not_fully_staged")
    uncovered = [
        path
        for path in paths
        if not any(repository_path_matches(path, pattern) for pattern in scope)
    ]
    gaps.extend(f"openspec_change_overlay_uncovered:{path}" for path in uncovered)
    if expected_digest and expected_digest != digest:
        gaps.append("openspec_change_overlay_digest_mismatch")
    if apply and not expected_digest:
        gaps.append("openspec_change_overlay_digest_required")
    return {"paths": paths, "digest": digest, "required_gaps": gaps}
