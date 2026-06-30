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
    paths = changed_paths(root)
    branch = current_branch(root)
    return {
        "root": str(root),
        "branch": branch,
        "dirty": bool(paths),
        "changed_paths": list(paths),
        "role": "work_lane" if branch.startswith("work/") else "accepted_root",
    }
