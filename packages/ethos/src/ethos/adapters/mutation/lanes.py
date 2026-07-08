from __future__ import annotations

from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lanes_refresh as lanes_refresh
import ethos.adapters.mutation.lanes_retire as lanes_retire
from ethos.adapters.mutation.lanes_retire import _git
from ethos.adapters.mutation.lanes_retire import _is_ancestor
from ethos.adapters.mutation.lanes_retire import _repo_root
from ethos.adapters.mutation.lanes_retire import _slug
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status import workspace_status
from ethos.adapters.store.state import acquire_lease
from ethos.adapters.store.state import active_leases
from ethos.adapters.store.state import delete_lease
from ethos.adapters.store.state import update_lease_payload
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import load_branch_role_policy


# Keep the historical private helper surface on this module for internal tests
# and patchable adapters. lanes_refresh uses the shared implementation in
# lanes_retire; this compatibility helper preserves the old private surface.
def _default_candidate_path(repo: Path, candidate_branch: str) -> Path:
    return repo.with_name(f"{repo.name}-{_slug(candidate_branch)}")


__all__ = (
    "retire_landed_work_lanes",
    "retire_unbound_work_lane_ref",
)


def start_work_lane(
    *,
    root: Path,
    name: str,
    path: Path | None = None,
    owner: str,
    claim_id: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = _repo_root(root)
    policy = load_branch_role_policy(repo)
    slug = _slug(name)
    branch = policy.work_branch(slug)
    # Default the lane home to the canonical sibling of the accepted root
    # (repo-<branch-slug>) so lanes stop scattering into /tmp; callers may
    # still pin an explicit path.
    target = (path or _default_candidate_path(repo, branch)).resolve()
    if not owner.strip():
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "required_gaps": ["missing_owner"],
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
    completed = _git(
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
        owner=owner,
        payload={
            "path": target.as_posix(),
            "branch": branch,
            "claim_id": claim_id or "",
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
        "owner": owner,
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
    repo = _repo_root(root)
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
            "owner": str(lease.get("owner") or "") if lease else "",
            "required_gaps": sorted(set(gaps)),
        }
    owner = str(cast("dict[str, object]", lease)["owner"])
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": target_branch,
            "claim_id": claim_id,
            "owner": owner,
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
        "owner": str(updated.get("owner") or owner),
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
    """Bootstrap candidate role while preserving this module's patchable adapters."""
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
    """Refresh candidate from accepted while preserving patchable adapters."""
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
    """Refresh a work lane base while preserving patchable adapters."""
    return _call_refresh(
        "refresh_work_lane_base",
        root=root,
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
    )


def _call_refresh(name: str, **kwargs: object) -> dict[str, object]:
    previous = _refresh_previous(lanes_refresh)
    try:
        _patch_refresh_adapters(lanes_refresh)
        return cast("dict[str, object]", getattr(lanes_refresh, name)(**kwargs))
    finally:
        _restore_refresh_adapters(lanes_refresh, previous)


def _refresh_previous(refresh: object) -> dict[str, object]:
    namespace = cast("dict[str, object]", refresh.__dict__)
    return {
        key: namespace[key] for key in ("workspace_status", "changed_paths", "_is_ancestor", "_git")
    }


def _patch_refresh_adapters(refresh: object) -> None:
    namespace = cast("dict[str, object]", refresh.__dict__)
    namespace.update(
        workspace_status=workspace_status,
        changed_paths=changed_paths,
        _is_ancestor=_is_ancestor,
        _git=_git,
    )


def _restore_refresh_adapters(refresh: object, previous: dict[str, object]) -> None:
    cast("dict[str, object]", refresh.__dict__).update(previous)


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


def _state_root(status: dict[str, object], fallback: Path) -> Path:
    worktrees = status.get("worktrees")
    if isinstance(worktrees, list):
        for worktree in worktrees:
            if not isinstance(worktree, dict):
                continue
            if worktree.get("role") == ROLE_ACCEPTED_ROOT and worktree.get("path"):
                return Path(str(cast("dict[str, object]", worktree)["path"]))
    return fallback


def _active_lease(db_path: Path, subject: str) -> dict[str, object] | None:
    for lease in active_leases(db_path):
        if lease["subject"] == subject:
            return lease
    return None


def _branch_exists(root: Path, branch: str) -> bool:
    completed = _git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    return completed.returncode == 0


def _started_worktree(*, branch: str, path: Path) -> dict[str, str]:
    head = _git(path, "rev-parse", "HEAD").stdout.strip()
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": head,
        "role": ROLE_WORK_LANE,
        "worktree_binding": "linked",
    }


def retire_landed_work_lanes(
    *,
    root: Path,
    branch: str | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    """Retire landed lanes while preserving this module's patchable adapters."""
    previous = {
        "_repo_root": lanes_retire.__dict__["_repo_root"],
        "workspace_status": lanes_retire.workspace_status,
        "active_leases": lanes_retire.active_leases,
        "delete_lease": lanes_retire.delete_lease,
        "_is_ancestor": lanes_retire.__dict__["_is_ancestor"],
        "_git": lanes_retire.__dict__["_git"],
    }
    try:
        lanes_retire.__dict__["_repo_root"] = _repo_root
        lanes_retire.workspace_status = workspace_status
        lanes_retire.active_leases = active_leases
        lanes_retire.delete_lease = delete_lease
        lanes_retire.__dict__["_is_ancestor"] = _is_ancestor
        lanes_retire.__dict__["_git"] = _git
        return lanes_retire.retire_landed_work_lanes(
            root=root,
            branch=branch,
            expect_head=expect_head,
            apply=apply,
        )
    finally:
        lanes_retire.__dict__["_repo_root"] = previous["_repo_root"]
        lanes_retire.workspace_status = previous["workspace_status"]
        lanes_retire.active_leases = previous["active_leases"]
        lanes_retire.delete_lease = previous["delete_lease"]
        lanes_retire.__dict__["_is_ancestor"] = previous["_is_ancestor"]
        lanes_retire.__dict__["_git"] = previous["_git"]


def retire_unbound_work_lane_ref(
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    apply: bool = False,
    authorized: bool = False,
) -> dict[str, object]:
    """Retire an unbound lane ref while preserving this module's patchable adapters."""
    previous = {
        "workspace_status": lanes_retire.workspace_status,
        "delete_lease": lanes_retire.delete_lease,
        "_git": lanes_retire.__dict__["_git"],
    }
    try:
        lanes_retire.workspace_status = workspace_status
        lanes_retire.delete_lease = delete_lease
        lanes_retire.__dict__["_git"] = _git
        return lanes_retire.retire_unbound_work_lane_ref(
            root=root,
            branch=branch,
            expect_head=expect_head,
            reason=reason,
            apply=apply,
            authorized=authorized,
        )
    finally:
        lanes_retire.workspace_status = previous["workspace_status"]
        lanes_retire.delete_lease = previous["delete_lease"]
        lanes_retire.__dict__["_git"] = previous["_git"]
