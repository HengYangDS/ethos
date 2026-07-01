from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ethos_contracts.branch_roles import (
    ROLE_ACCEPTED_ROOT,
    ROLE_WORK_LANE,
    load_branch_role_policy,
)

from ethos_adapters.state import (
    acquire_lease,
    active_leases,
    update_lease_payload,
)
from ethos_adapters.status import changed_paths, workspace_status

_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def start_work_lane(
    *,
    root: Path,
    name: str,
    path: Path,
    owner: str,
    claim_id: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = _repo_root(root)
    policy = load_branch_role_policy(repo)
    slug = _slug(name)
    branch = policy.work_branch(slug)
    target = path.resolve()
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
    candidate = status["candidate"]
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
    owner = str(lease["owner"])
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
    repo = _repo_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    current_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    target = (path or _default_candidate_path(repo, policy.candidate_branch)).resolve()
    gaps: list[str] = []
    if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]:
        gaps.append("candidate_bootstrap_requires_clean_accepted_root")
    if expect_head is not None and expect_head != current_head:
        gaps.append("expect_head_mismatch")
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": gaps,
        }
    candidate = status["candidate"]
    if candidate["exists"] and candidate["worktree_exists"]:
        return {
            "ok": True,
            "state": "present",
            "branch": policy.candidate_branch,
            "head": candidate["head"],
            "path": candidate["worktree_path"],
            "required_gaps": [],
        }
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": [],
        }
    if target.exists():
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": ["candidate_worktree_path_exists"],
        }
    if not candidate["exists"]:
        completed = _git(repo, "branch", policy.candidate_branch, current_head, check=False)
        if completed.returncode != 0:
            return {
                "ok": False,
                "state": "blocked",
                "branch": policy.candidate_branch,
                "head": current_head,
                "path": target.as_posix(),
                "required_gaps": ["candidate_bootstrap_failed"],
                "stderr": completed.stderr.strip(),
            }
    completed = _git(
        repo,
        "worktree",
        "add",
        target.as_posix(),
        policy.candidate_branch,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": ["candidate_worktree_add_failed"],
            "stderr": completed.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "bootstrapped",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": target.as_posix(),
        "required_gaps": [],
    }


def retire_landed_work_lanes(
    *,
    root: Path,
    branch: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = _repo_root(root)
    status = workspace_status(repo)
    lanes = [
        _retirement_lane(repo, lane)
        for lane in status["worktrees"]
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
            gaps.extend(str(gap) for gap in lane["required_gaps"])
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch or "",
            "lanes": lanes,
            "required_gaps": sorted(set(gaps)),
        }
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": branch or "",
            "lanes": lanes,
            "required_gaps": [],
        }
    lane = selected[0]
    remove = _git(repo, "worktree", "remove", str(lane["path"]), check=False)
    if remove.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch or "",
            "lanes": lanes,
            "required_gaps": ["worktree_remove_failed"],
            "stderr": remove.stderr.strip(),
        }
    delete = _git(repo, "branch", "-d", str(lane["branch"]), check=False)
    if delete.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch or "",
            "lanes": lanes,
            "required_gaps": ["branch_delete_failed"],
            "stderr": delete.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "retired",
        "branch": branch or "",
        "retired": lane,
        "lanes": lanes,
        "required_gaps": [],
    }


def _retirement_lane(repo: Path, lane: dict[str, object]) -> dict[str, object]:
    gaps: list[str] = []
    branch = str(lane["branch"])
    path = Path(str(lane["path"]))
    if not _is_ancestor(repo, branch, "HEAD"):
        gaps.append("work_lane_not_merged")
    if changed_paths(path):
        gaps.append("work_lane_dirty")
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": str(lane["head"]),
        "retire_ready": not gaps,
        "required_gaps": gaps,
    }


def _slug(name: str) -> str:
    slug = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    return slug or "work"


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
            return worktree
    return None


def _state_root(status: dict[str, object], fallback: Path) -> Path:
    worktrees = status.get("worktrees")
    if isinstance(worktrees, list):
        for worktree in worktrees:
            if not isinstance(worktree, dict):
                continue
            if worktree.get("role") == ROLE_ACCEPTED_ROOT and worktree.get("path"):
                return Path(str(worktree["path"]))
    return fallback


def _active_lease(db_path: Path, subject: str) -> dict[str, object] | None:
    for lease in active_leases(db_path):
        if lease["subject"] == subject:
            return lease
    return None


def _repo_root(root: Path) -> Path:
    completed = _git(root, "rev-parse", "--show-toplevel")
    return Path(completed.stdout.strip()).resolve()


def _default_candidate_path(repo: Path, candidate_branch: str) -> Path:
    return repo.with_name(f"{repo.name}-{_slug(candidate_branch)}")


def _branch_exists(root: Path, branch: str) -> bool:
    completed = _git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    return completed.returncode == 0


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = _git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False)
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


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )
