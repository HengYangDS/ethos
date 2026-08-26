"""Filesystem boundary checks for content-addressed runtime generations."""

from __future__ import annotations

import os
from pathlib import Path


def is_junction(path: Path) -> bool:
    """Return whether ``path`` is a Windows junction without following it."""
    predicate = getattr(path, "is_junction", None)
    return bool(predicate is not None and predicate())


def require_no_junctions(root: Path, *, error: str) -> None:
    """Reject a tree containing a junction before any recursive read or mutation."""
    if is_junction(root):
        raise ValueError(error)
    for parent, directories, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(parent)
        if any(is_junction(base / name) for name in (*directories, *files)):
            raise ValueError(error)


def require_exclusive_inodes(root: Path, *, error: str) -> None:
    """Reject regular files whose inode is shared outside one generated tree."""
    for parent, _directories, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(parent)
        for name in files:
            path = base / name
            if not path.is_symlink() and path.stat().st_nlink != 1:
                raise ValueError(error)
