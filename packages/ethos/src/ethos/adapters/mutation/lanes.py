from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import cast

from ethos.adapters.repo.status import changed_paths
from ethos.adapters.repo.status import workspace_status
from ethos.adapters.store.state import acquire_lease
from ethos.adapters.store.state import active_leases
from ethos.adapters.store.state import delete_lease
from ethos.adapters.store.state import update_lease_payload
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE
from ethos_core.contracts.branch_roles import load_branch_role_policy

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
    candidate = cast("dict[str, object]", status["candidate"])
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


def refresh_candidate_from_accepted(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    repo = _repo_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    current_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")
    gaps: list[str] = []
    if status["role"] != ROLE_ACCEPTED_ROOT:
        gaps.append("accepted_root_required")
    elif status["dirty"]:
        gaps.append("accepted_root_dirty")
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    elif changed_paths(Path(candidate_path)):
        gaps.append("candidate_worktree_dirty")
    if apply:
        if not authorized:
            gaps.append("authorization_required")
        if expect_head is None:
            gaps.append("expect_head_required")
        elif expect_head != current_head:
            gaps.append("expect_head_mismatch")
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": candidate_head,
            "path": candidate_path,
            "required_gaps": gaps,
        }
    if candidate_head == current_head:
        return {
            "ok": True,
            "state": "base_current",
            "branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": candidate_head,
            "path": candidate_path,
            "required_gaps": [],
        }
    if not apply:
        return {
            "ok": True,
            "state": "ready_to_refresh_from_accepted",
            "branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": candidate_head,
            "path": candidate_path,
            "required_gaps": [],
        }
    completed = _git(Path(candidate_path), "reset", "--hard", current_head, check=False)
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": candidate_head,
            "path": candidate_path,
            "required_gaps": ["candidate_refresh_from_accepted_failed"],
            "stderr": completed.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "refreshed_from_accepted",
        "branch": policy.candidate_branch,
        "head": current_head,
        "previous_head": candidate_head,
        "path": candidate_path,
        "required_gaps": [],
    }


def refresh_work_lane_base(
    *,
    root: Path,
    apply: bool = False,
    authorized: bool = False,
    expect_head: str | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    status = workspace_status(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    branch = str(status.get("branch") or "")
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    candidate_path = str(candidate.get("worktree_path") or "")
    gaps: list[str] = []
    if status["role"] != ROLE_WORK_LANE:
        gaps.append("protected_root_mutation")
    elif status["dirty"]:
        gaps.append("work_lane_dirty")
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    elif changed_paths(Path(candidate_path)):
        gaps.append("candidate_worktree_dirty")
    if apply:
        if not authorized:
            gaps.append("authorization_required")
        if expect_head is None:
            gaps.append("expect_head_required")
        elif expect_head != current_head:
            gaps.append("expect_head_mismatch")
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "head": current_head,
            "candidate_branch": policy.candidate_branch,
            "candidate_head": candidate_head,
            "candidate_path": candidate_path,
            "required_gaps": gaps,
        }
    if _is_ancestor(root, candidate_head, current_head):
        return {
            "ok": True,
            "state": "base_current",
            "branch": branch,
            "head": current_head,
            "candidate_branch": policy.candidate_branch,
            "candidate_head": candidate_head,
            "candidate_path": candidate_path,
            "required_gaps": [],
        }
    if not apply:
        return {
            "ok": True,
            "state": "ready_to_refresh_base",
            "branch": branch,
            "head": current_head,
            "candidate_branch": policy.candidate_branch,
            "candidate_head": candidate_head,
            "candidate_path": candidate_path,
            "required_gaps": [],
        }
    completed = _git(root, "rebase", policy.candidate_branch, check=False)
    if completed.returncode != 0:
        _git(root, "rebase", "--abort", check=False)
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "head": current_head,
            "candidate_branch": policy.candidate_branch,
            "candidate_head": candidate_head,
            "candidate_path": candidate_path,
            "required_gaps": ["refresh_base_failed"],
            "stderr": completed.stderr.strip(),
        }
    refreshed_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    return {
        "ok": True,
        "state": "base_refreshed",
        "branch": branch,
        "previous_head": current_head,
        "head": refreshed_head,
        "candidate_branch": policy.candidate_branch,
        "candidate_head": candidate_head,
        "candidate_path": candidate_path,
        "required_gaps": [],
    }


def retire_unbound_work_lane_ref(
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    apply: bool = False,
    authorized: bool = False,
) -> dict[str, object]:
    repo = _repo_root(root)
    status = workspace_status(repo)
    policy = load_branch_role_policy(repo)
    branch = branch.strip()
    reason = reason.strip()
    current = _unbound_work_lane_ref(status, branch)
    binding = _branch_binding(status, branch)
    head = str((current or binding or {}).get("head") or "")
    gaps: list[str] = []
    if not branch:
        gaps.append("unbound_retire_branch_required")
    elif not _branch_exists(repo, branch):
        gaps.append("unbound_retire_branch_not_found")
    elif policy.role_for_branch(branch) != ROLE_WORK_LANE:
        gaps.append("unbound_retire_not_work_lane")
    elif current is None:
        gaps.append("unbound_retire_ref_not_unbound")
    if not reason:
        gaps.append("retire_reason_required")
    if expect_head is None or not str(expect_head).strip():
        gaps.append("expect_head_required")
    elif head and expect_head != head:
        gaps.append("expect_head_mismatch")
    if apply and not authorized:
        gaps.append("authorization_required")
    report = {
        "ok": not gaps,
        "state": "ready_to_retire_unbound" if not gaps else "blocked",
        "branch": branch,
        "head": head,
        "relation_to_accepted": str((current or {}).get("relation_to_accepted") or ""),
        "claim_id": str((current or {}).get("claim_id") or ""),
        "claim_binding": str((current or {}).get("claim_binding") or ""),
        "reason": reason,
        "mutation": {
            "apply": apply,
            "authorized": authorized,
            "expect_head": expect_head or "",
            "ref": f"refs/heads/{branch}" if branch else "",
        },
        "required_gaps": sorted(set(gaps)),
    }
    if gaps:
        return report
    if not apply:
        return report
    deleted = _git(
        repo,
        "update-ref",
        "-d",
        f"refs/heads/{branch}",
        str(expect_head),
        check=False,
    )
    if deleted.returncode != 0:
        report["ok"] = False
        report["state"] = "blocked"
        report["required_gaps"] = ["unbound_ref_delete_failed"]
        report["stderr"] = deleted.stderr.strip()
        return report
    delete_lease(repo / ".ethos" / "state" / "state.sqlite", subject=branch)
    report["state"] = "retired_unbound"
    report["retired_ref"] = f"refs/heads/{branch}"
    return report


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
        for lane in cast("list[dict[str, object]]", status["worktrees"])
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
    # Release the lane's lease so it cannot outlive the lane — a recreated
    # same-named branch must re-acquire, not inherit a stale lease.
    delete_lease(repo / ".ethos" / "state" / "state.sqlite", subject=str(lane["branch"]))
    return {
        "ok": True,
        "state": "retired",
        "branch": branch or "",
        "retired": lane,
        "lanes": lanes,
        "required_gaps": [],
    }


def _unbound_work_lane_ref(
    status: dict[str, object],
    branch: str,
) -> dict[str, object] | None:
    coordination = status.get("coordination")
    if not isinstance(coordination, dict):
        return None
    refs = coordination.get("unbound_work_lane_refs")
    if not isinstance(refs, list):
        return None
    for ref in refs:
        if isinstance(ref, dict) and ref.get("branch") == branch:
            return cast("dict[str, object]", ref)
    return None


def _branch_binding(
    status: dict[str, object],
    branch: str,
) -> dict[str, object] | None:
    bindings = status.get("branch_bindings")
    if not isinstance(bindings, list):
        return None
    for binding in bindings:
        if isinstance(binding, dict) and binding.get("branch") == branch:
            return cast("dict[str, object]", binding)
    return None


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
