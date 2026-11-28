"""Filesystem boundary checks for content-addressed runtime generations."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path


def require_exclusive_inodes(root: Path, *, error: str) -> None:
    """Reject regular files whose inode is shared outside one generated tree."""
    for parent, _directories, files in os.walk(root, topdown=True, followlinks=False):
        base = Path(parent)
        for name in files:
            path = base / name
            if not path.is_symlink() and path.stat().st_nlink != 1:
                raise ValueError(error)


def make_owned_tree_writable(root: Path) -> None:
    """Make one owned generated tree writable without following links."""
    for parent, directories, files in os.walk(root, topdown=False, followlinks=False):
        base = Path(parent)
        for name in files:
            path = base / name
            if not path.is_symlink():
                path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR)
        for name in directories:
            path = base / name
            if not path.is_symlink():
                path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IRWXU)
    root.chmod(stat.S_IMODE(root.stat().st_mode) | stat.S_IRWXU)


def _prepare_removal_directory(path: Path) -> None:
    """Add only missing owner permissions to an ordinary owned directory."""
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        message = f"owned_cleanup_directory_unsafe:{path}"
        raise PermissionError(message)
    if metadata.st_mode & stat.S_IRWXU != stat.S_IRWXU:
        path.chmod(
            stat.S_IMODE(metadata.st_mode) | stat.S_IRWXU,
            follow_symlinks=os.chmod not in os.supports_follow_symlinks,
        )


def remove_owned_path(path: Path) -> None:
    """Remove owned output without changing external referents or hiding failure."""
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        _prepare_removal_directory(path)
        for parent, directories, _files in os.walk(path, followlinks=False):
            base = Path(parent)
            for name in directories[:]:
                child = base / name
                if child.is_symlink():
                    directories.remove(name)
                else:
                    _prepare_removal_directory(child)
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def runtime_python(interpreter_home: Path) -> Path:
    """Return the executable inside one owned interpreter home."""
    return runtime_scripts(interpreter_home) / "python"


def runtime_scripts(interpreter_home: Path) -> Path:
    """Return the console-script directory inside one owned interpreter home."""
    return interpreter_home / "bin"


def runtime_executable(interpreter_home: Path, name: str) -> Path:
    """Return one console executable inside one owned interpreter home."""
    return runtime_scripts(interpreter_home) / name
