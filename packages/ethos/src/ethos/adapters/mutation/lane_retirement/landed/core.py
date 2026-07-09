from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state import delete_lease
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE


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
    lanes = [
        _retirement_lane(repo, lane, leases=leases)
        for lane in worktrees
        if lane["role"] == ROLE_WORK_LANE
    ]
    selected = [lane for lane in lanes if branch is None or lane["branch"] == branch]
    gaps: list[str] = []
    if branch is not None and not selected:
        gaps.append("retire_branch_not_found")
    if apply and not branch:
        gaps.append("retire_branch_required")
    if branch:
        for lane in selected:
            gaps.extend(str(gap) for gap in cast("list[object]", lane["required_gaps"]))
        gaps.extend(_landed_actor_gaps(selected))
        gaps.extend(_landed_expect_head_gaps(selected, expect_head=expect_head, apply=apply))
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch or "",
            "lanes": lanes,
            "mutation": lane_retirement_shared.retire_mutation_binding(
                branch=branch,
                expect_head=expect_head,
                actor=_current_actor(),
                required_actor=_selected_lease_owner(selected),
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
            "mutation": lane_retirement_shared.retire_mutation_binding(
                branch=branch,
                expect_head=expect_head,
                actor=_current_actor(),
                required_actor=_selected_lease_owner(selected),
            ),
            "required_gaps": [],
        }
    lane = selected[0]
    removed = lane_retirement_shared.remove_linked_lane(repo, lane, expect_head=expect_head)
    if removed:
        return {
            "branch": branch or "",
            "lanes": lanes,
            "mutation": lane_retirement_shared.retire_mutation_binding(
                branch=branch,
                expect_head=expect_head,
                actor=_current_actor(),
                required_actor=_selected_lease_owner(selected),
            ),
            **removed,
        }
    # Release the lane's lease so it cannot outlive the lane: a recreated
    # same-named branch must re-acquire, not inherit a stale lease.
    delete_lease(repo / ".ethos" / "state" / "state.sqlite", subject=str(lane["branch"]))
    lane_retirement_shared.delete_json_projection_lease(repo, subject=str(lane["branch"]))
    return {
        "ok": True,
        "state": "retired",
        "branch": branch or "",
        "retired": lane,
        "lanes": lanes,
        "mutation": lane_retirement_shared.retire_mutation_binding(
            branch=branch,
            expect_head=expect_head,
            actor=_current_actor(),
            required_actor=_selected_lease_owner(selected),
        ),
        "required_gaps": [],
    }


def has_changed_paths(root: Path) -> bool:
    """Return whether a Work Lane path has tracked or untracked local changes."""
    completed = lane_retirement_shared.run_git(
        root,
        "status",
        "--porcelain",
        "--untracked-files=all",
        check=False,
    )
    if completed.returncode != 0:
        return True
    return bool(completed.stdout.strip())


def _landed_actor_gaps(selected: list[dict[str, object]]) -> list[str]:
    if not selected:
        return []
    lease_owner = _selected_lease_owner(selected)
    actor = _current_actor()
    if not lease_owner or actor != lease_owner:
        return ["foreign_work_lane_retire_authority_required"]
    return []


def _selected_lease_owner(selected: list[dict[str, object]]) -> str:
    if not selected:
        return ""
    return str(selected[0].get("lease_owner") or "")


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


def _current_actor() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip()


def _retirement_lane(
    repo: Path, lane: dict[str, object], *, leases: dict[str, dict[str, object]] | None = None
) -> dict[str, object]:
    gaps: list[str] = []
    branch = str(lane["branch"])
    path = Path(str(lane["path"]))
    lease = (leases or {}).get(branch, {})
    lease_owner = str(lease.get("owner") or "")
    if not is_ancestor(repo, branch, "HEAD"):
        gaps.append("work_lane_not_merged")
    if has_changed_paths(path):
        gaps.append("work_lane_dirty")
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": str(lane["head"]),
        "lease_owner": lease_owner,
        "lease_state": "leased" if lease_owner else "missing",
        "retire_ready": not gaps,
        "required_gaps": gaps,
    }
