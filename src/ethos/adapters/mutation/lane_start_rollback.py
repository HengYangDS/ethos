from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable

    from ethos.adapters.mutation.lane_start_carrier import LaneStartContext


class LaneStartRollback(NamedTuple):
    """Exact carrier ownership and effects available to lane-start compensation."""

    repo: Path
    target: Path
    branch: str
    ownership: tuple[str, str, str]
    completed: subprocess.CompletedProcess[str]
    run: Callable[..., subprocess.CompletedProcess[str]]
    lease: dict[str, object] | None
    failure_gap: str


def compensate(
    context: LaneStartContext,
    completed: subprocess.CompletedProcess[str],
    *,
    ownership: tuple[str, str, str],
    lease: dict[str, object] | None = None,
    gap: str | None = None,
) -> dict[str, object]:
    """Compensate one failed lane-start step from its shared context."""
    return rollback_lane_start(
        LaneStartRollback(
            repo=context.repo,
            target=context.target,
            branch=context.branch,
            ownership=ownership,
            completed=completed,
            run=context.run,
            lease=lease,
            failure_gap=gap or completed.stderr.strip() or "lane_start_initialization_failed",
        )
    )


def worktree_head(
    repo: Path,
    *,
    target: Path,
    branch: str,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> str | None:
    """Return the observed HEAD only for the exact target and branch binding."""
    listed = run(repo, "worktree", "list", "--porcelain", check=False)
    if listed.returncode != 0:
        return None
    for block in listed.stdout.split("\n\n"):
        record = {
            parts[0]: parts[1] if len(parts) > 1 else ""
            for line in block.splitlines()
            if line
            for parts in (line.split(" ", 1),)
        }
        path = record.get("worktree", "")
        observed_branch = (
            record.get("branch", "").removeprefix("refs/heads/")
            if "branch" in record
            else "detached"
            if "detached" in record
            else ""
        )
        if path and Path(path).resolve() == target and observed_branch == branch:
            return record.get("HEAD", "")
    return None


def exact_worktree(
    repo: Path,
    *,
    target: Path,
    branch: str,
    head: str,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    """Report whether the exact lane-start worktree binding still exists."""
    return worktree_head(repo, target=target, branch=branch, run=run) == head


def rollback_lane_start(context: LaneStartRollback) -> dict[str, object]:
    """Compensate only the exact carrier and lease created by lane start."""
    repo, target, branch = context.repo, context.target, context.branch
    worktree_branch, worktree_head_value, owned_ref_head = context.ownership
    observed_worktree = worktree_head(
        repo,
        target=target,
        branch=worktree_branch,
        run=context.run,
    )
    worktree = observed_worktree is not None and observed_worktree == worktree_head_value
    target_exists = os.path.lexists(target)
    worktree_removed = not worktree and not target_exists
    ref_removed = False
    current_head = ref_head(repo, branch)
    gap = (
        "lane_start_target_path_ownership_unknown"
        if target_exists and observed_worktree is None
        else "lane_start_target_ref_ownership_unknown"
        if observed_worktree is None and current_head
        else ""
    )
    if worktree and not gap:
        worktree_removed = remove_lane_start_worktree(
            repo,
            target=target,
            branch=worktree_branch,
            head=worktree_head_value,
            run=context.run,
        )
        if not worktree_removed:
            gap = "lane_start_worktree_cleanup_failed"
    current_head = ref_head(repo, branch) if not gap else current_head
    if not gap and current_head and current_head != owned_ref_head:
        gap = "lane_start_ref_changed"
    ref_removed = not current_head if not gap else False
    if not gap and current_head:
        try:
            delete_lane_start_ref(repo, branch, owned_ref_head, context.lease)
            ref_removed = not ref_head(repo, branch)
        except (OSError, TypeError, ValueError) as error:
            gap = str(error) or "lane_start_ref_cleanup_failed"
    if not ref_removed:
        gap = gap or "lane_start_ref_cleanup_failed"
    try:
        if not gap and context.lease:
            revoke_lease(
                state_database(repo),
                request=LeaseOperationRequest(
                    operation="lane_start_compensation",
                    branch=branch,
                    holder_ref=str(context.lease["holder_ref"]),
                    lease_id=str(context.lease["lease_id"]),
                    expected_epoch=integer_value(context.lease["epoch"]),
                    expect_head=str(context.lease["expected_head"]),
                    expected_expires_at=str(context.lease["expires_at"]),
                    expected_payload_sha256=str(context.lease["payload_sha256"]),
                    apply=True,
                ),
            )
    except (RuntimeError, ValueError) as exc:
        gap = str(exc)
    if gap:
        return retained_lane_start_report(
            branch=branch,
            target=target,
            completed=context.completed,
            worktree_removed=worktree_removed,
            ref_removed=ref_removed,
            lease=context.lease,
            gap=gap,
        )
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "path": target.as_posix(),
        "stderr": context.completed.stderr.strip() or "lane_start_postcondition_failed",
        "child_process": child_process_evidence(context.completed),
        "carrier_cleanup": {"worktree_removed": True, "ref_removed": True},
        "lease_state": "revoked" if context.lease else "not_acquired",
        "required_gaps": [context.failure_gap],
    }


def delete_lane_start_ref(
    repo: Path,
    branch: str,
    head: str,
    lease: dict[str, object] | None,
) -> None:
    """Delete only the exact ref owned by one failed leased lane start."""
    if not lease:
        message = "lane_start_ref_cleanup_lease_missing"
        raise ValueError(message)
    ref = f"refs/heads/{branch}"
    effect = GitEffect(updates={ref: GitRefUpdate(expected=head, desired="0" * len(head))})
    authority = load_lease_bound_commitment(repo, lease=lease)
    plan = compile_observed_git_effect(
        repo,
        authority,
        effect,
        head=head,
        prior_attestations={},
        policy={
            "operation": "lane.start.compensate",
            "branch": branch,
            "holder_ref": str(lease["holder_ref"]),
        },
        values={"lease_generation": lease_generation(lease)},
    )
    execute_git_effect(repo, plan, issuer=str(lease["holder_ref"]))


def remove_lane_start_worktree(
    repo: Path,
    *,
    target: Path,
    branch: str,
    head: str,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    """Remove only the exact detached or bound carrier created by lane start."""
    try:
        remove_worktree(
            repo,
            target,
            branch=branch,
            head=head,
            force=True,
            runner=run,
        )
    except ValueError:
        return False
    return True


def retained_lane_start_report(
    *,
    branch: str,
    target: Path,
    completed: subprocess.CompletedProcess[str],
    worktree_removed: bool,
    ref_removed: bool,
    lease: dict[str, object] | None,
    gap: str,
) -> dict[str, object]:
    """Report the evidence and retained authority after incomplete compensation."""
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "path": target.as_posix(),
        "stderr": completed.stderr.strip() or "lane_start_postcondition_failed",
        "child_process": child_process_evidence(completed),
        "carrier_cleanup": {
            "worktree_removed": worktree_removed,
            "ref_removed": ref_removed,
        },
        "lease_state": "retained" if lease else "not_acquired",
        "required_gaps": ["lane_creation_compensation_failed", gap],
    }


def child_process_evidence(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    """Project bounded child-process evidence for a blocked lane start."""
    args = completed.args if isinstance(completed.args, (list, tuple)) else (completed.args,)
    return {
        "argv": [str(item) for item in args],
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "parse_error": str(getattr(completed, "parse_error", "")),
    }
