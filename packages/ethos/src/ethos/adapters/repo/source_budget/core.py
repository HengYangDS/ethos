"""Present-worktree inventory adapter for the source-budget gate."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def present_worktree_paths(root: Path) -> tuple[str, ...]:
    """Return present tracked and non-ignored untracked paths in stable order."""
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        return ()
    if completed.returncode != 0:
        return ()
    resolved_root = root.resolve()
    paths = {
        relative
        for raw in completed.stdout.split(b"\0")
        if (relative := raw.decode("utf-8", errors="surrogateescape"))
        and _present_file(resolved_root, relative)
    }
    return tuple(sorted(paths))


def _present_file(root: Path, relative: str) -> bool:
    """Keep only a regular in-worktree path that can be measured now."""
    path = (root / relative).resolve()
    return path.is_relative_to(root) and path.is_file()
