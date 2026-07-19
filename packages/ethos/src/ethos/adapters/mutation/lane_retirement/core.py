from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.coordination import lease_summary
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import delete_lease
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class SupersededLaneRetirementRequest:
    """Inputs for retiring a linked Work Lane superseded by accepted truth."""

    branch: str
    expect_head: str | None = None
    reason: str = ""
    absorbed_by: str = ""
    apply: bool = False
    authorized: bool = False


def _run_git_adapter(
    root: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return run_git(root, *args, check=check)


@dataclass(frozen=True, slots=True)
class SupersededRetirementRuntime:
    """Explicit dependencies used to retire superseded Work Lanes."""

    repo_root: Callable[[Path], Path] = repo_root
    workspace_status: Callable[[Path], dict[str, object]] = workspace_status
    leases_by_branch: Callable[..., dict[str, dict[str, object]]] = leases_by_branch
    is_ancestor: Callable[[Path, str, str], bool] = is_ancestor
    run_git: Callable[..., subprocess.CompletedProcess[str]] = _run_git_adapter
    delete_lease: Callable[..., int] = delete_lease
    shared: lane_retirement_shared.RetirementRuntime = field(
        default_factory=lane_retirement_shared.RetirementRuntime
    )


def retire_superseded_work_lane(
    *,
    root: Path,
    request: SupersededLaneRetirementRequest,
    runtime: SupersededRetirementRuntime | None = None,
) -> dict[str, object]:
    """Retire a clean linked Work Lane already absorbed by accepted truth."""
    active_runtime = runtime or SupersededRetirementRuntime()
    repo = active_runtime.repo_root(root)
    status = active_runtime.workspace_status(repo)
    branch = request.branch.strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    worktrees = status.get("worktrees")
    selected = (
        next(
            (
                cast("dict[str, object]", item)
                for item in worktrees
                if isinstance(item, dict)
                and item.get("role") == ROLE_WORK_LANE
                and item.get("branch") == branch
            ),
            None,
        )
        if isinstance(worktrees, list)
        else None
    )
    lane: dict[str, object] = {}
    if selected:
        path = Path(str(selected["path"]))
        lease = active_runtime.leases_by_branch(
            cast("list[dict[str, str]]", worktrees), current_path=repo
        ).get(branch, {})
        lane_gaps = [
            *(
                ["work_lane_already_merged_use_retire_landed"]
                if active_runtime.is_ancestor(repo, branch, "HEAD")
                else []
            ),
            *(
                ["work_lane_dirty"]
                if lane_retirement_shared.has_changed_paths(path, runner=active_runtime.run_git)
                else []
            ),
        ]
        lane = {
            "branch": branch,
            "path": path.as_posix(),
            "head": str(selected["head"]),
            "lease": lease_summary(lease),
            "lease_state": "leased" if lease.get("holder_ref") else "missing",
            "retire_ready": not lane_gaps,
            "required_gaps": lane_gaps,
        }
    accepted_head = (
        _output(
            repo,
            "rev-parse",
            load_branch_role_policy(repo).accepted_branch,
            runtime=active_runtime,
        )
        or ""
    )
    head = str(
        lane.get("head")
        or (_output(repo, "rev-parse", branch, runtime=active_runtime) if branch else "")
        or ""
    )
    gaps = _gaps(
        repo=repo,
        branch=branch,
        selected=selected,
        lane=lane,
        head=head,
        expected=request.expect_head,
        reason=reason,
        absorbed_by=absorbed_by,
        accepted_head=accepted_head,
        apply=request.apply,
        authorized=request.authorized,
        runtime=active_runtime,
    )
    report = lane_retirement_shared.retirement_report(
        command="lane-retire-superseded",
        action="lane.retire.superseded",
        branch=branch,
        expect_head=request.expect_head,
        apply=request.apply,
        confirmed=request.authorized,
        state="ready_to_retire_superseded" if not gaps else "blocked",
        gaps=gaps,
        holder_ref=lane_retirement_shared.current_holder_ref(),
        required_holder_ref=lane_retirement_shared.lane_holder_ref(lane),
        extra_state={"absorbed_by": absorbed_by, "accepted_head": accepted_head},
        fields={
            "head": head,
            "absorbed_by": absorbed_by,
            "accepted_head": accepted_head,
            "reason": reason,
            "retire_ready": bool(lane.get("retire_ready")) and not gaps,
            "lane": lane,
        },
    )
    if gaps:
        return report
    if not request.apply:
        return report
    removed = lane_retirement_shared.remove_linked_lane(
        repo, lane, expect_head=request.expect_head, runtime=active_runtime.shared
    )
    if removed:
        report.update(removed)
        return report
    active_runtime.delete_lease(
        repo / ".ethos" / "state" / "state.sqlite", subject=str(lane["branch"])
    )
    lane_retirement_shared.delete_json_projection_lease(repo, subject=str(lane["branch"]))
    report["state"] = "retired_superseded"
    report["retired"] = lane
    report["retire_ready"] = True
    return report


def _gaps(  # noqa: C901, PLR0913, RUF100 - exact retirement state dimensions
    *,
    repo: Path,
    branch: str,
    selected: dict[str, object] | None,
    lane: dict[str, object],
    head: str,
    expected: str | None,
    reason: str,
    absorbed_by: str,
    accepted_head: str,
    apply: bool,
    authorized: bool,
    runtime: SupersededRetirementRuntime,
) -> list[str]:
    gaps: list[str] = []
    policy = load_branch_role_policy(repo)
    if not branch:
        gaps.append("superseded_retire_branch_required")
    elif _output(repo, "rev-parse", "--verify", branch, runtime=runtime) is None:
        gaps.append("superseded_retire_branch_not_found")
    elif policy.role_for_branch(branch) != ROLE_WORK_LANE:
        gaps.append("superseded_retire_not_work_lane")
    elif selected is None:
        gaps.append("superseded_retire_worktree_not_linked")
    if lane:
        gaps.extend(str(gap) for gap in cast("list[object]", lane["required_gaps"]))
        gaps.extend(lane_retirement_shared.holder_authority_gaps([lane]))
    if not reason:
        gaps.append("retire_reason_required")
    if not accepted_head:
        gaps.append("accepted_head_unavailable")
    if not absorbed_by:
        gaps.append("absorbed_by_required")
    elif accepted_head and absorbed_by != accepted_head:
        gaps.append("absorbed_by_not_current_accepted_head")
    if (
        selected
        and branch
        and head
        and accepted_head
        and absorbed_by == accepted_head
        and not _lane_delta_absorbed_by_accepted(
            repo,
            branch=branch,
            head=head,
            accepted_head=accepted_head,
            runtime=runtime,
        )
    ):
        gaps.append("superseded_lane_not_absorbed_by_accepted")
    gaps.extend(lane_retirement_shared.expected_head_gaps(head, expected))
    if apply and not authorized:
        gaps.append("authorization_required")
    return gaps


def _lane_delta_absorbed_by_accepted(
    repo: Path,
    *,
    branch: str,
    head: str,
    accepted_head: str,
    runtime: SupersededRetirementRuntime,
) -> bool:
    base = _output(repo, "merge-base", accepted_head, branch, runtime=runtime)
    if not base:
        return False
    changed = _output(
        repo, "diff", "--name-only", "--no-renames", "-z", base, head, runtime=runtime
    )
    if changed is None:
        return False
    return all(
        (_output(repo, "rev-parse", f"{head}:{path}", runtime=runtime) or "")
        == (_output(repo, "rev-parse", f"{accepted_head}:{path}", runtime=runtime) or "")
        for path in changed.split("\0")
        if path
    )


def _output(
    root: Path,
    *args: str,
    runtime: SupersededRetirementRuntime | None = None,
) -> str | None:
    completed = (runtime or SupersededRetirementRuntime()).run_git(root, *args, check=False)
    return completed.stdout.strip() if not completed.returncode else None


def _branch_exists(
    root: Path,
    branch: str,
    *,
    runtime: SupersededRetirementRuntime | None = None,
) -> bool:
    return _output(root, "rev-parse", "--verify", branch, runtime=runtime) is not None


def _branch_head(
    root: Path,
    branch: str,
    *,
    runtime: SupersededRetirementRuntime | None = None,
) -> str:
    return (_output(root, "rev-parse", branch, runtime=runtime) or "") if branch else ""


def _linked_work_lane(status: dict[str, object], branch: str) -> dict[str, object] | None:
    rows = status.get("worktrees")
    if not isinstance(rows, list):
        return None
    return next(
        (
            cast("dict[str, object]", row)
            for row in rows
            if isinstance(row, dict)
            and row.get("role") == ROLE_WORK_LANE
            and row.get("branch") == branch
        ),
        None,
    )


def _superseded_expected_head_gaps(*, head: str, expect_head: str | None) -> list[str]:
    return lane_retirement_shared.expected_head_gaps(head, expect_head)
