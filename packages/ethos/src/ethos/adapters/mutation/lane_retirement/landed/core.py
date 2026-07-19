from __future__ import annotations

from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.repo.coordination import lease_summary
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import delete_lease
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.normalization.core import string_sequence


def retire_landed_work_lanes(
    *,
    root: Path,
    branch: str | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    """Retire clean linked Work Lanes already merged into accepted truth."""
    repo = repo_root(root)
    status = workspace_status(repo)
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    leases = leases_by_branch(cast("list[dict[str, str]]", worktrees), current_path=repo)
    candidate_lanes = [
        lane
        for lane in worktrees
        if lane["role"] == ROLE_WORK_LANE and (branch is None or lane["branch"] == branch)
    ]
    lanes = [_retirement_lane(repo, lane, leases=leases) for lane in candidate_lanes]
    selected = lanes
    gaps: list[str] = []
    if branch is not None and not selected:
        gaps.append("retire_branch_not_found")
    if apply and not branch:
        gaps.append("retire_branch_required")
    if branch:
        for lane in selected:
            gaps.extend(str(gap) for gap in cast("list[object]", lane["required_gaps"]))
        gaps.extend(lane_retirement_shared.holder_authority_gaps(selected))
        gaps.extend(_landed_expect_head_gaps(selected, expect_head=expect_head, apply=apply))
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch or "",
            "lanes": lanes,
            "mutation": lane_retirement_shared.retire_mutation_envelope(
                command="lane-retire-landed",
                action="lane.retire.landed",
                branch=branch,
                expect_head=expect_head,
                apply=apply,
                confirmed=False,
                required_gaps=gaps,
                holder_ref=lane_retirement_shared.current_holder_ref(),
                required_holder_ref=lane_retirement_shared.selected_holder_ref(selected),
            ),
            "required_gaps": sorted(set(gaps)),
            **lane_retirement_shared.retire_authority_guidance(gaps),
        }
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": branch or "",
            "lanes": lanes,
            "mutation": lane_retirement_shared.retire_mutation_envelope(
                command="lane-retire-landed",
                action="lane.retire.landed",
                branch=branch,
                expect_head=expect_head,
                apply=apply,
                confirmed=False,
                required_gaps=[],
                holder_ref=lane_retirement_shared.current_holder_ref(),
                required_holder_ref=lane_retirement_shared.selected_holder_ref(selected),
            ),
            "required_gaps": [],
        }
    lane = selected[0]
    control_root = _retirement_control_root(worktrees)
    if control_root is None:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch or "",
            "lanes": lanes,
            "mutation": lane_retirement_shared.retire_mutation_envelope(
                command="lane-retire-landed",
                action="lane.retire.landed",
                branch=branch,
                expect_head=expect_head,
                apply=apply,
                confirmed=False,
                required_gaps=["retirement_control_root_unavailable"],
                holder_ref=lane_retirement_shared.current_holder_ref(),
                required_holder_ref=lane_retirement_shared.selected_holder_ref(selected),
            ),
            "required_gaps": ["retirement_control_root_unavailable"],
        }
    removed = lane_retirement_shared.remove_linked_lane(control_root, lane, expect_head=expect_head)
    if removed:
        return {
            "branch": branch or "",
            "lanes": lanes,
            "mutation": lane_retirement_shared.retire_mutation_envelope(
                command="lane-retire-landed",
                action="lane.retire.landed",
                branch=branch,
                expect_head=expect_head,
                apply=apply,
                confirmed=False,
                required_gaps=string_sequence(removed.get("required_gaps")),
                holder_ref=lane_retirement_shared.current_holder_ref(),
                required_holder_ref=lane_retirement_shared.selected_holder_ref(selected),
            ),
            **removed,
        }
    delete_lease(control_root / ".ethos" / "state" / "state.sqlite", subject=str(lane["branch"]))
    lane_retirement_shared.delete_json_projection_lease(control_root, subject=str(lane["branch"]))
    return {
        "ok": True,
        "state": "retired",
        "branch": branch or "",
        "retired": lane,
        "lanes": lanes,
        "mutation": lane_retirement_shared.retire_mutation_envelope(
            command="lane-retire-landed",
            action="lane.retire.landed",
            branch=branch,
            expect_head=expect_head,
            apply=apply,
            confirmed=False,
            required_gaps=[],
            holder_ref=lane_retirement_shared.current_holder_ref(),
            required_holder_ref=lane_retirement_shared.selected_holder_ref(selected),
        ),
        "required_gaps": [],
    }


def _landed_expect_head_gaps(
    selected: list[dict[str, object]],
    *,
    expect_head: str | None,
    apply: bool,
) -> list[str]:
    if not apply:
        return []
    expected = (expect_head or "").strip()
    if not expected:
        return ["expect_head_required"]
    if selected and expected != str(selected[0]["head"]):
        return ["expect_head_mismatch"]
    return []


def _retirement_control_root(worktrees: list[dict[str, object]]) -> Path | None:
    """Return the accepted checkout that survives removal of any Work Lane."""
    for worktree in worktrees:
        if worktree["role"] != ROLE_ACCEPTED_ROOT:
            continue
        path = Path(str(worktree["path"]))
        if path.is_dir():
            return path
    return None


def _retirement_lane(
    repo: Path,
    lane: dict[str, object],
    *,
    leases: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    gaps: list[str] = []
    branch = str(lane["branch"])
    path = Path(str(lane["path"]))
    lease = (leases or {}).get(branch, {})
    holder_ref = str(lease.get("holder_ref") or "")
    if not is_ancestor(repo, branch, "HEAD"):
        gaps.append("work_lane_not_merged")
    if lane_retirement_shared.has_changed_paths(path):
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
