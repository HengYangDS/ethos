from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ethos_workspace.state import acquire_lease
from ethos_workspace.status import CANDIDATE_BRANCH, changed_paths, workspace_status

_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def start_work_lane(
    *,
    root: Path,
    name: str,
    path: Path,
    owner: str,
    apply: bool = False,
) -> dict[str, object]:
    repo = _repo_root(root)
    slug = _slug(name)
    branch = f"work/{slug}"
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
    if status["role"] != "accepted_root" or status["dirty"]:
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
        CANDIDATE_BRANCH,
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
        payload={"path": target.as_posix(), "branch": branch},
    )
    return {
        "ok": True,
        "state": "started",
        "branch": branch,
        "base": CANDIDATE_BRANCH,
        "base_head": str(candidate["head"]),
        "path": target.as_posix(),
        "worktree": _started_worktree(branch=branch, path=target),
        "owner": owner,
        "lease": lease,
        "required_gaps": [],
    }


def bootstrap_candidate(
    *,
    root: Path,
    path: Path | None = None,
    expect_head: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = _repo_root(root)
    status = workspace_status(repo)
    current_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    target = (path or _default_candidate_path(repo)).resolve()
    gaps: list[str] = []
    if status["role"] != "accepted_root" or status["dirty"]:
        gaps.append("candidate_bootstrap_requires_clean_accepted_root")
    if expect_head is not None and expect_head != current_head:
        gaps.append("expect_head_mismatch")
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": gaps,
        }
    candidate = status["candidate"]
    if candidate["exists"] and candidate["worktree_exists"]:
        return {
            "ok": True,
            "state": "present",
            "branch": CANDIDATE_BRANCH,
            "head": candidate["head"],
            "path": candidate["worktree_path"],
            "required_gaps": [],
        }
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": [],
        }
    if target.exists():
        return {
            "ok": False,
            "state": "blocked",
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": ["candidate_worktree_path_exists"],
        }
    if not candidate["exists"]:
        completed = _git(repo, "branch", CANDIDATE_BRANCH, current_head, check=False)
        if completed.returncode != 0:
            return {
                "ok": False,
                "state": "blocked",
                "branch": CANDIDATE_BRANCH,
                "head": current_head,
                "path": target.as_posix(),
                "required_gaps": ["candidate_bootstrap_failed"],
                "stderr": completed.stderr.strip(),
            }
    completed = _git(repo, "worktree", "add", target.as_posix(), CANDIDATE_BRANCH, check=False)
    if completed.returncode != 0:
        return {
            "ok": False,
            "state": "blocked",
            "branch": CANDIDATE_BRANCH,
            "head": current_head,
            "path": target.as_posix(),
            "required_gaps": ["candidate_worktree_add_failed"],
            "stderr": completed.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "bootstrapped",
        "branch": CANDIDATE_BRANCH,
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
        if lane["role"] == "work_lane"
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


def _repo_root(root: Path) -> Path:
    completed = _git(root, "rev-parse", "--show-toplevel")
    return Path(completed.stdout.strip()).resolve()


def _default_candidate_path(repo: Path) -> Path:
    return repo.with_name(f"{repo.name}-candidate-dev")


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
        "role": "work_lane",
        "open_action": "open_worktree",
        "open_label": "Open Worktree",
    }


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )
