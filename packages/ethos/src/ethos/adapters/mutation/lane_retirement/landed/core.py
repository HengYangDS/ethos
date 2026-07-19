from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.repo.coordination import lease_summary
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import delete_lease
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class LandedRetirementRuntime:
    """Explicit dependencies used to retire landed Work Lanes."""

    repo_root: Callable[[Path], Path] = repo_root
    workspace_status: Callable[[Path], dict[str, object]] = workspace_status
    leases_by_branch: Callable[..., dict[str, dict[str, object]]] = leases_by_branch
    is_ancestor: Callable[[Path, str, str], bool] = is_ancestor
    delete_lease: Callable[..., int] = delete_lease
    shared: lane_retirement_shared.RetirementRuntime = field(
        default_factory=lane_retirement_shared.RetirementRuntime
    )


def retire_landed_work_lanes(
    *,
    root: Path,
    branch: str | None = None,
    expect_head: str | None = None,
    apply: bool = False,
    runtime: LandedRetirementRuntime | None = None,
) -> dict[str, object]:
    """Retire clean linked Work Lanes already merged into accepted truth."""
    active_runtime = runtime or LandedRetirementRuntime()
    repo = active_runtime.repo_root(root)
    status = active_runtime.workspace_status(repo)
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    leases = active_runtime.leases_by_branch(
        cast("list[dict[str, str]]", worktrees), current_path=repo
    )
    candidates = [
        lane
        for lane in worktrees
        if lane["role"] == ROLE_WORK_LANE and (branch is None or lane["branch"] == branch)
    ]
    lanes = [
        _retirement_lane(repo, lane, leases=leases, runtime=active_runtime) for lane in candidates
    ]
    gaps: list[str] = []
    if branch is not None and not lanes:
        gaps.append("retire_branch_not_found")
    if apply and not branch:
        gaps.append("retire_branch_required")
    if branch:
        for lane in lanes:
            gaps.extend(str(gap) for gap in cast("list[object]", lane["required_gaps"]))
        gaps.extend(lane_retirement_shared.holder_authority_gaps(lanes))
        if apply:
            gaps.extend(
                lane_retirement_shared.expected_head_gaps(
                    str(lanes[0]["head"]) if lanes else "", expect_head
                )
            )
    if gaps:
        return _report(branch, expect_head, apply, lanes, "blocked", gaps)
    if not apply:
        return _report(branch, expect_head, apply, lanes, "planned", [])
    lane = lanes[0]
    removed = lane_retirement_shared.remove_linked_lane(
        repo, lane, expect_head=expect_head, runtime=active_runtime.shared
    )
    if removed:
        failure_gaps = [str(gap) for gap in cast("list[object]", removed["required_gaps"])]
        return _report(
            branch,
            expect_head,
            apply,
            lanes,
            str(removed["state"]),
            failure_gaps,
            **{
                key: value
                for key, value in removed.items()
                if key not in {"ok", "state", "required_gaps"}
            },
        )
    active_runtime.delete_lease(
        repo / ".ethos" / "state" / "state.sqlite", subject=str(lane["branch"])
    )
    lane_retirement_shared.delete_json_projection_lease(repo, subject=str(lane["branch"]))
    return _report(branch, expect_head, apply, lanes, "retired", [], retired=lane)


def _report(  # noqa: PLR0913, RUF100 - exact retirement result dimensions
    branch: str | None,
    expect_head: str | None,
    apply: bool,  # noqa: FBT001 - internal positional compression helper
    lanes: list[dict[str, object]],
    state: str,
    gaps: list[str],
    **extra: object,
) -> dict[str, object]:
    return lane_retirement_shared.retirement_report(
        command="lane-retire-landed",
        action="lane.retire.landed",
        branch=branch,
        expect_head=expect_head,
        apply=apply,
        confirmed=False,
        state=state,
        gaps=gaps,
        holder_ref=lane_retirement_shared.current_holder_ref(),
        required_holder_ref=lane_retirement_shared.selected_holder_ref(lanes),
        fields={"lanes": lanes, **extra},
    )


def _retirement_lane(
    repo: Path,
    lane: dict[str, object],
    *,
    leases: dict[str, dict[str, object]] | None = None,
    runtime: LandedRetirementRuntime | None = None,
) -> dict[str, object]:
    active_runtime = runtime or LandedRetirementRuntime()
    gaps: list[str] = []
    branch = str(lane["branch"])
    path = Path(str(lane["path"]))
    lease = (leases or {}).get(branch, {})
    holder_ref = str(lease.get("holder_ref") or "")
    if not active_runtime.is_ancestor(repo, branch, "HEAD"):
        gaps.append("work_lane_not_merged")
    if lane_retirement_shared.has_changed_paths(path, runner=active_runtime.shared.run_git):
        gaps.append("work_lane_dirty")
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": str(lane["head"]),
        "lease": lease_summary(lease),
        "lease_state": "leased" if holder_ref else "missing",
        "retire_ready": not gaps,
        "required_gaps": gaps,
    }
