from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.lane_lifecycle.refresh as lanes_refresh
import ethos.adapters.mutation.lane_retirement.core as lane_retirement_core
import ethos.adapters.mutation.lane_retirement.landed.core as landed_retirement
import ethos.adapters.mutation.lane_retirement.unbound.core as unbound_retirement
import ethos.adapters.repo.status.bindings as status_bindings
from ethos.adapters.mutation.lane_lifecycle.core import default_candidate_path
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_lifecycle.core import slug
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.core import acquire_lease
from ethos.adapters.store.state.lease.effects import delete_lease
from ethos.adapters.store.state.lease.effects import update_lease_payload
from ethos.adapters.store.state.lease.projection import active_leases
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.coordination import HolderRef

if TYPE_CHECKING:
    from ethos.adapters.mutation.lane_retirement.core import SupersededLaneRetirementRequest


def start_work_lane(
    *,
    root: Path,
    name: str,
    path: Path | None = None,
    holder_ref: str,
    claim_id: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = repo_root(root)
    policy = load_branch_role_policy(repo)
    lane_slug = slug(name)
    branch = policy.work_branch(lane_slug)
    # Default the lane home to the canonical sibling of the accepted root
    # (repo-<branch-slug>) so lanes stop scattering into /tmp; callers may
    # still pin an explicit path.
    target = (path or default_candidate_path(repo, branch)).resolve()
    try:
        normalized_holder_ref = HolderRef.parse(holder_ref).serialize()
    except ValueError:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "required_gaps": ["holder_ref_invalid"],
        }
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": branch,
            "path": target.as_posix(),
            "required_gaps": [],
        }
    status = workspace_status(repo)
    if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            "role": status["role"],
            "dirty": status["dirty"],
            "required_gaps": ["lane_start_requires_clean_accepted_root"],
        }
    candidate = cast("dict[str, object]", status["candidate"])
    if not candidate["exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            "required_gaps": ["candidate_branch_missing"],
        }
    if not candidate["worktree_exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            "required_gaps": ["candidate_worktree_missing"],
        }
    candidate_path = Path(str(candidate["worktree_path"]))
    if changed_paths(candidate_path):
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            "required_gaps": ["candidate_worktree_dirty"],
        }
    if _branch_exists(repo, branch):
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            "required_gaps": ["branch_already_exists"],
        }
    completed = run_git(
        repo,
        "worktree",
        "add",
        "-b",
        branch,
        target.as_posix(),
        policy.candidate_branch,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            "required_gaps": ["worktree_add_failed"],
            "stderr": completed.stderr.strip(),
        }
    lease = acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject=branch,
        holder_ref=normalized_holder_ref,
        payload={
            "path": target.as_posix(),
            "branch": branch,
            "claim_id": claim_id or "",
            "expected_head": str(candidate["head"]),
        },
    )
    return {
        "ok": True,
        "state": "started",
        "branch": branch,
        "base": policy.candidate_branch,
        "base_head": str(candidate["head"]),
        "path": target.as_posix(),
        "worktree": _started_worktree(branch=branch, path=target),
        "holder_ref": normalized_holder_ref,
        "claim_id": claim_id or "",
        "lease": lease,
        "required_gaps": [],
    }


def bind_work_lane_claim(
    *,
    root: Path,
    claim_id: str,
    branch: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = repo_root(root)
    status = workspace_status(repo)
    target_branch = branch or str(status["branch"])
    gaps: list[str] = []
    if not claim_id.strip():
        gaps.append("missing_claim_id")
    lane = _status_work_lane(status, target_branch)
    if lane is None:
        gaps.append(f"work_lane_not_found:{target_branch}")
    state_root = _state_root(status, repo)
    state_db = state_root / ".ethos" / "state" / "state.sqlite"
    lease = _active_lease(state_db, target_branch)
    if lease is None:
        gaps.append(f"work_lane_missing_lease:{target_branch}")
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": target_branch,
            "claim_id": claim_id,
            "holder_ref": str(lease.get("holder_ref") or "") if lease else "",
            "required_gaps": sorted(set(gaps)),
        }
    holder_ref = str(cast("dict[str, object]", lease)["holder_ref"])
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": target_branch,
            "claim_id": claim_id,
            "holder_ref": holder_ref,
            "required_gaps": [],
        }
    updated = update_lease_payload(
        state_db,
        subject=target_branch,
        payload={"claim_id": claim_id.strip()},
    )
    return {
        "ok": bool(updated),
        "state": "bound" if updated else "blocked",
        "branch": target_branch,
        "claim_id": claim_id.strip() if updated else "",
        "holder_ref": str(updated.get("holder_ref") or holder_ref),
        "lease": updated,
        "required_gaps": [] if updated else [f"work_lane_missing_lease:{target_branch}"],
    }


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    """Bootstrap candidate role through the lane refresh command contract."""
    return _call_refresh(
        "bootstrap_candidate",
        root=root,
        path=path,
        expect_head=expect_head,
        apply=apply,
    )


def refresh_candidate_from_accepted(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    """Refresh candidate from accepted through the lane refresh command contract."""
    return _call_refresh(
        "refresh_candidate_from_accepted",
        root=root,
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
    )


def refresh_work_lane_base(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    """Refresh a Work Lane base through the lane refresh command contract."""
    return _call_refresh(
        "refresh_work_lane_base",
        root=root,
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
    )


def _call_refresh(name: str, **kwargs: object) -> dict[str, object]:
    return cast(
        "dict[str, object]",
        getattr(lanes_refresh, name)(**kwargs, runtime=_lane_refresh_runtime()),
    )


def _lane_refresh_runtime() -> lanes_refresh.LaneRefreshRuntime:
    return lanes_refresh.LaneRefreshRuntime(
        repo_root=repo_root,
        default_candidate_path=default_candidate_path,
        load_branch_role_policy=load_branch_role_policy,
        workspace_status=workspace_status,
        changed_paths=changed_paths,
        is_ancestor=is_ancestor,
        run_git=run_git,
    )


def _status_work_lane(
    status: dict[str, object],
    branch: str,
) -> dict[str, object] | None:
    worktrees = status.get("worktrees")
    if not isinstance(worktrees, list):
        return None
    for worktree in worktrees:
        if not isinstance(worktree, dict):
            continue
        if worktree.get("branch") == branch and worktree.get("role") == ROLE_WORK_LANE:
            return cast("dict[str, object]", worktree)
    return None


def _state_root(status: dict[str, object], default_root: Path) -> Path:
    worktrees = status.get("worktrees")
    if isinstance(worktrees, list):
        for worktree in worktrees:
            if not isinstance(worktree, dict):
                continue
            if worktree.get("role") == ROLE_ACCEPTED_ROOT and worktree.get("path"):
                return Path(str(cast("dict[str, object]", worktree)["path"]))
    return default_root


def _active_lease(db_path: Path, subject: str) -> dict[str, object] | None:
    for lease in active_leases(db_path):
        if lease["subject"] == subject:
            return lease
    return None


def _branch_exists(root: Path, branch: str) -> bool:
    completed = run_git(
        root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False
    )
    return completed.returncode == 0


def _started_worktree(*, branch: str, path: Path) -> dict[str, str]:
    head = run_git(path, "rev-parse", "HEAD").stdout.strip()
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": head,
        "role": ROLE_WORK_LANE,
        "worktree_binding": "linked",
    }


def _retirement_leases_by_branch(
    worktrees: list[dict[str, str]], *, current_path: Path
) -> dict[str, dict[str, object]]:
    leases = status_bindings.leases_by_branch(worktrees, current_path=current_path)
    control_root = current_path
    for worktree in worktrees:
        if worktree.get("role") == ROLE_ACCEPTED_ROOT and worktree.get("path"):
            control_root = Path(str(worktree["path"]))
            break
    leases.update(
        {
            str(lease["subject"]): lease
            for lease in active_leases(control_root / ".ethos" / "state" / "state.sqlite")
        }
    )
    return leases


def _retirement_shared_runtime() -> lane_retirement_core.lane_retirement_shared.RetirementRuntime:
    return lane_retirement_core.lane_retirement_shared.RetirementRuntime(run_git=run_git)


def _landed_retirement_runtime() -> landed_retirement.LandedRetirementRuntime:
    return landed_retirement.LandedRetirementRuntime(
        repo_root=repo_root,
        workspace_status=workspace_status,
        leases_by_branch=_retirement_leases_by_branch,
        is_ancestor=is_ancestor,
        delete_lease=delete_lease,
        shared=_retirement_shared_runtime(),
    )


def _superseded_retirement_runtime() -> lane_retirement_core.SupersededRetirementRuntime:
    return lane_retirement_core.SupersededRetirementRuntime(
        repo_root=repo_root,
        workspace_status=workspace_status,
        leases_by_branch=_retirement_leases_by_branch,
        is_ancestor=is_ancestor,
        run_git=run_git,
        delete_lease=delete_lease,
        shared=_retirement_shared_runtime(),
    )


def _unbound_retirement_runtime() -> unbound_retirement.UnboundRetirementRuntime:
    return unbound_retirement.UnboundRetirementRuntime(
        repo_root=repo_root,
        workspace_status=workspace_status,
        delete_lease=delete_lease,
        shared=_retirement_shared_runtime(),
    )


def retire_landed_work_lanes(
    *,
    root: Path,
    branch: str | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    """Retire landed Work Lanes through explicit runtime bindings."""
    return landed_retirement.retire_landed_work_lanes(
        root=root,
        branch=branch,
        expect_head=expect_head,
        apply=apply,
        runtime=_landed_retirement_runtime(),
    )


def retire_superseded_work_lane(
    *,
    root: Path,
    request: SupersededLaneRetirementRequest,
) -> dict[str, object]:
    """Retire a superseded linked Work Lane through explicit runtime bindings."""
    return lane_retirement_core.retire_superseded_work_lane(
        root=root,
        request=request,
        runtime=_superseded_retirement_runtime(),
    )


def retire_unbound_work_lane_ref(
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    apply: bool = False,
    authorized: bool = False,
) -> dict[str, object]:
    """Retire an unbound Work Lane ref through explicit runtime bindings."""
    return unbound_retirement.retire_unbound_work_lane_ref(
        root=root,
        branch=branch,
        expect_head=expect_head,
        reason=reason,
        apply=apply,
        authorized=authorized,
        runtime=_unbound_retirement_runtime(),
    )
