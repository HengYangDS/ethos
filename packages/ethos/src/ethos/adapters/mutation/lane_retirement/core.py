from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_retirement.shared.core import remove_linked_lane
from ethos.adapters.mutation.lane_retirement.shared.core import retire_authority_guidance
from ethos.adapters.mutation.lane_retirement.shared.core import retire_mutation_binding
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state import delete_lease
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import load_branch_role_policy


@dataclass(frozen=True)
class SupersededLaneRetirementRequest:
    """Inputs for retiring a linked Work Lane superseded by accepted truth."""

    branch: str
    expect_head: str | None = None
    reason: str = ""
    absorbed_by: str = ""
    apply: bool = False
    authorized: bool = False


def retire_superseded_work_lane(
    *,
    root: Path,
    request: SupersededLaneRetirementRequest,
) -> dict[str, object]:
    """Retire a clean linked Work Lane already absorbed by accepted truth."""
    repo = repo_root(root)
    status = workspace_status(repo)
    branch = request.branch.strip()
    reason = request.reason.strip()
    absorbed_by = request.absorbed_by.strip()
    selected = _linked_work_lane(status, branch)
    lane = (
        _superseded_retirement_lane(
            repo,
            selected,
            leases=leases_by_branch(
                cast("list[dict[str, str]]", status["worktrees"]),
                current_path=repo,
            ),
        )
        if selected
        else {}
    )
    accepted_head = _accepted_head(repo)
    head = str(lane.get("head") or _branch_head(repo, branch))
    gaps = _superseded_retire_gaps(
        {
            "repo": repo,
            "branch": branch,
            "selected": selected,
            "lane": lane,
            "head": head,
            "expect_head": request.expect_head,
            "reason": reason,
            "absorbed_by": absorbed_by,
            "accepted_head": accepted_head,
            "apply": request.apply,
            "authorized": request.authorized,
        }
    )
    report = {
        "ok": not gaps,
        "state": "ready_to_retire_superseded" if not gaps else "blocked",
        "branch": branch,
        "head": head,
        "absorbed_by": absorbed_by,
        "accepted_head": accepted_head,
        "reason": reason,
        "retire_ready": bool(lane.get("retire_ready")) and not gaps,
        "lane": lane,
        "mutation": {
            "apply": request.apply,
            "authorized": request.authorized,
            **retire_mutation_binding(
                branch=branch,
                expect_head=request.expect_head,
                actor=_current_actor(),
                required_actor=str(lane.get("lease_owner") or ""),
            ),
        },
        "required_gaps": sorted(set(gaps)),
    }
    if gaps:
        return {**report, **retire_authority_guidance(gaps)}
    if not request.apply:
        return report
    removed = remove_linked_lane(repo, lane, expect_head=request.expect_head)
    if removed:
        report.update(removed)
        return report
    delete_lease(repo / ".ethos" / "state" / "state.sqlite", subject=str(lane["branch"]))
    lane_retirement_shared.delete_json_projection_lease(repo, subject=str(lane["branch"]))
    report["state"] = "retired_superseded"
    report["retired"] = lane
    report["retire_ready"] = True
    return report


def _superseded_retire_gaps(context: dict[str, object]) -> list[str]:
    repo = cast("Path", context["repo"])
    branch = str(context["branch"])
    lane = cast("dict[str, object]", context["lane"])
    gaps = _superseded_branch_gaps(
        repo,
        branch=branch,
        selected=cast("dict[str, object] | None", context["selected"]),
    )
    if lane:
        gaps.extend(str(gap) for gap in cast("list[object]", lane["required_gaps"]))
        gaps.extend(_landed_actor_gaps([lane]))
    gaps.extend(
        _superseded_absorption_gaps(
            reason=str(context["reason"]),
            absorbed_by=str(context["absorbed_by"]),
            accepted_head=str(context["accepted_head"]),
        )
    )
    gaps.extend(
        _superseded_expected_head_gaps(
            head=str(context["head"]),
            expect_head=cast("str | None", context["expect_head"]),
        )
    )
    if bool(context["apply"]) and not bool(context["authorized"]):
        gaps.append("authorization_required")
    return gaps


def _superseded_branch_gaps(
    repo: Path,
    *,
    branch: str,
    selected: dict[str, object] | None,
) -> list[str]:
    policy = load_branch_role_policy(repo)
    if not branch:
        return ["superseded_retire_branch_required"]
    if not _branch_exists(repo, branch):
        return ["superseded_retire_branch_not_found"]
    if policy.role_for_branch(branch) != ROLE_WORK_LANE:
        return ["superseded_retire_not_work_lane"]
    if selected is None:
        return ["superseded_retire_worktree_not_linked"]
    return []


def _superseded_absorption_gaps(
    *,
    reason: str,
    absorbed_by: str,
    accepted_head: str,
) -> list[str]:
    gaps: list[str] = []
    if not reason:
        gaps.append("retire_reason_required")
    if not accepted_head:
        gaps.append("accepted_head_unavailable")
    if not absorbed_by:
        gaps.append("absorbed_by_required")
    elif accepted_head and absorbed_by != accepted_head:
        gaps.append("absorbed_by_not_current_accepted_head")
    return gaps


def _superseded_expected_head_gaps(
    *,
    head: str,
    expect_head: str | None,
) -> list[str]:
    expected = (expect_head or "").strip()
    if not expected:
        return ["expect_head_required"]
    if head and expected != head:
        return ["expect_head_mismatch"]
    return []


def _current_actor() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip()


def _landed_actor_gaps(selected: list[dict[str, object]]) -> list[str]:
    if not selected:
        return []
    lease_owner = str(selected[0].get("lease_owner") or "")
    actor = _current_actor()
    if not lease_owner or actor != lease_owner:
        return ["foreign_work_lane_retire_authority_required"]
    return []


def _branch_exists(root: Path, branch: str) -> bool:
    completed = run_git(root, "rev-parse", "--verify", branch, check=False)
    return completed.returncode == 0


def _accepted_head(root: Path) -> str:
    policy = load_branch_role_policy(root)
    completed = run_git(root, "rev-parse", policy.accepted_branch, check=False)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _branch_head(root: Path, branch: str) -> str:
    if not branch:
        return ""
    completed = run_git(root, "rev-parse", branch, check=False)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _linked_work_lane(
    status: dict[str, object],
    branch: str,
) -> dict[str, object] | None:
    worktrees = status.get("worktrees")
    if not isinstance(worktrees, list):
        return None
    for lane in worktrees:
        if (
            isinstance(lane, dict)
            and lane.get("role") == ROLE_WORK_LANE
            and lane.get("branch") == branch
        ):
            return cast("dict[str, object]", lane)
    return None


def _superseded_retirement_lane(
    repo: Path,
    lane: dict[str, object],
    *,
    leases: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    gaps: list[str] = []
    branch = str(lane["branch"])
    path = Path(str(lane["path"]))
    lease = (leases or {}).get(branch, {})
    lease_owner = str(lease.get("owner") or "")
    if is_ancestor(repo, branch, "HEAD"):
        gaps.append("work_lane_already_merged_use_retire_landed")
    if _has_changed_paths(path):
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


def _has_changed_paths(root: Path) -> bool:
    completed = run_git(root, "status", "--porcelain", "--untracked-files=all", check=False)
    if completed.returncode != 0:
        return True
    return bool(completed.stdout.strip())
