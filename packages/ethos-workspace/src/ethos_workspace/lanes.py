from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ethos_workspace.state import acquire_lease
from ethos_workspace.status import workspace_status

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
        "HEAD",
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
        "path": target.as_posix(),
        "owner": owner,
        "lease": lease,
        "required_gaps": [],
    }


def _slug(name: str) -> str:
    slug = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    return slug or "work"


def _repo_root(root: Path) -> Path:
    completed = _git(root, "rev-parse", "--show-toplevel")
    return Path(completed.stdout.strip()).resolve()


def _branch_exists(root: Path, branch: str) -> bool:
    completed = _git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    return completed.returncode == 0


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
    )
