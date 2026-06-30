from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.rstrip("\n")


def current_branch(root: Path) -> str:
    return _run_git(root, "branch", "--show-current") or "detached"


def changed_paths(root: Path) -> tuple[str, ...]:
    output = _run_git(root, "status", "--porcelain")
    paths: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        paths.append(line[3:] if len(line) > 3 and line[2] == " " else line[2:].strip())
    return tuple(paths)


def workspace_status(root: Path) -> dict[str, object]:
    repo = Path(_run_git(root, "rev-parse", "--show-toplevel")).resolve()
    current_path = repo
    paths = changed_paths(root)
    branch = current_branch(root)
    role = _role_for_branch(branch)
    worktrees = _worktrees(root)
    foreign = [
        {
            "path": worktree["path"],
            "head": worktree["head"],
            "branch": worktree["branch"],
            "role": worktree["role"],
        }
        for worktree in worktrees
        if worktree["role"] == "work_lane" and Path(str(worktree["path"])).resolve() != current_path
    ]
    required_gaps = ["foreign_work_lane_present"] if foreign else []
    return {
        "root": str(root),
        "branch": branch,
        "dirty": bool(paths),
        "changed_paths": list(paths),
        "role": role,
        "worktrees": worktrees,
        "foreign_work_lanes": foreign,
        "required_gaps": required_gaps,
    }


def _worktrees(root: Path) -> list[dict[str, str]]:
    output = _run_git(root, "worktree", "list", "--porcelain")
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                entries.append(_normalize_worktree(current))
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        entries.append(_normalize_worktree(current))
    return entries


def _normalize_worktree(entry: dict[str, str]) -> dict[str, str]:
    branch = entry.get("branch", "")
    if branch.startswith("refs/heads/"):
        branch = branch.removeprefix("refs/heads/")
    return {
        "path": entry.get("worktree", ""),
        "head": entry.get("HEAD", ""),
        "branch": branch or "detached",
        "role": _role_for_branch(branch),
    }


def _role_for_branch(branch: str) -> str:
    if branch.startswith("work/"):
        return "work_lane"
    if branch == "candidate/dev":
        return "candidate"
    if branch.startswith("submit/"):
        return "submit"
    if branch == "detached":
        return "detached"
    if branch in {"dev", "main"}:
        return "accepted_root"
    return "other"
