from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def layout_reference(root: Path) -> str | None:
    """Return the Git reference used for incremental layout comparisons."""
    status = run_git(root, "status", "--porcelain")
    if status:
        return "HEAD"
    for reference in ("candidate/dev", "dev", "HEAD"):
        if run_git(root, "rev-parse", "--verify", reference) is not None:
            return reference
    return None


def run_git_show(root: Path, spec: str) -> str | None:
    """Return `git show` stdout, or None when the spec is unavailable."""
    return run_git(root, "show", spec)


def run_git(root: Path, *args: str) -> str | None:
    """Run a read-only Git command and return stdout on success."""
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout
