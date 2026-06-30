from __future__ import annotations

import subprocess
from pathlib import Path

CANDIDATE_BRANCH = "candidate/dev"


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
    worktrees = _worktrees(root, current_path=current_path)
    candidate = _candidate_status(root, worktrees)
    branch_actions = _branch_actions(worktrees, candidate)
    foreign = [
        {
            "path": worktree["path"],
            "head": worktree["head"],
            "branch": worktree["branch"],
            "role": worktree["role"],
            "open_action": worktree["open_action"],
            "open_label": worktree["open_label"],
        }
        for worktree in worktrees
        if worktree["role"] == "work_lane" and Path(str(worktree["path"])).resolve() != current_path
    ]
    required_gaps = []
    if foreign:
        required_gaps.append("foreign_work_lane_present")
    if not candidate["exists"]:
        required_gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        required_gaps.append("candidate_worktree_missing")
    return {
        "root": str(root),
        "branch": branch,
        "dirty": bool(paths),
        "changed_paths": list(paths),
        "role": role,
        "candidate": candidate,
        "worktrees": worktrees,
        "branch_actions": branch_actions,
        "foreign_work_lanes": foreign,
        "required_gaps": required_gaps,
    }


def _worktrees(root: Path, *, current_path: Path) -> list[dict[str, str]]:
    output = _run_git(root, "worktree", "list", "--porcelain")
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                entries.append(_normalize_worktree(current, current_path=current_path))
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    if current:
        entries.append(_normalize_worktree(current, current_path=current_path))
    return entries


def _normalize_worktree(entry: dict[str, str], *, current_path: Path) -> dict[str, str]:
    branch = entry.get("branch", "")
    if branch.startswith("refs/heads/"):
        branch = branch.removeprefix("refs/heads/")
    path = entry.get("worktree", "")
    action, label = _worktree_action(path, current_path=current_path)
    return {
        "path": path,
        "head": entry.get("HEAD", ""),
        "branch": branch or "detached",
        "role": _role_for_branch(branch),
        "open_action": action,
        "open_label": label,
    }


def _candidate_status(
    root: Path,
    worktrees: list[dict[str, str]],
) -> dict[str, object]:
    head = _ref_head(root, CANDIDATE_BRANCH)
    worktree_path = ""
    open_action = "bootstrap_worktree"
    open_label = "Bootstrap Worktree"
    for worktree in worktrees:
        if worktree["branch"] == CANDIDATE_BRANCH:
            worktree_path = worktree["path"]
            open_action = worktree["open_action"]
            open_label = worktree["open_label"]
            break
    if head and not worktree_path:
        open_action = "create_worktree"
        open_label = "Create Worktree"
    return {
        "branch": CANDIDATE_BRANCH,
        "exists": bool(head),
        "head": head,
        "worktree_exists": bool(worktree_path),
        "worktree_path": worktree_path,
        "open_action": open_action,
        "open_label": open_label,
    }


def _branch_actions(
    worktrees: list[dict[str, str]],
    candidate: dict[str, object],
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    seen: set[str] = set()
    for worktree in worktrees:
        branch = str(worktree["branch"])
        if branch == "detached":
            continue
        actions.append(
            {
                "branch": branch,
                "role": str(worktree["role"]),
                "head": str(worktree["head"]),
                "path": str(worktree["path"]),
                "action": str(worktree["open_action"]),
                "label": str(worktree["open_label"]),
            }
        )
        seen.add(branch)
    if CANDIDATE_BRANCH not in seen:
        actions.append(
            {
                "branch": CANDIDATE_BRANCH,
                "role": "candidate",
                "head": str(candidate["head"]),
                "path": str(candidate["worktree_path"]),
                "action": str(candidate["open_action"]),
                "label": str(candidate["open_label"]),
            }
        )
    return actions


def _worktree_action(path: str, *, current_path: Path) -> tuple[str, str]:
    if path and Path(path).resolve() == current_path:
        return "current_worktree", "Current Worktree"
    return "open_worktree", "Open Worktree"


def _ref_head(root: Path, ref: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _role_for_branch(branch: str) -> str:
    if branch.startswith("work/"):
        return "work_lane"
    if branch == CANDIDATE_BRANCH:
        return "candidate"
    if branch.startswith("submit/"):
        return "submit"
    if branch == "detached":
        return "detached"
    if branch in {"dev", "main"}:
        return "accepted_root"
    return "other"
