"""Observe and establish trust-anchor protection through the host's permission bits."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def protected_from_untrusted_write(path: Path) -> bool:
    """Return whether the path and its parent exclude group and other write authority."""
    try:
        target = path.resolve(strict=True)
    except OSError:
        return False
    return all(_posix_protected(candidate) for candidate in (target, target.parent))


def protect_for_current_identity(path: Path) -> None:
    """Restrict one trust-anchor file or directory to the current identity."""
    try:
        path.chmod(0o700 if path.is_dir() else 0o600)
    except OSError as error:
        message = f"git_object_trust_anchor_protection_failed:{error.strerror or error}"
        raise OSError(message) from error


def _posix_protected(path: Path) -> bool:
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError:
        return False
    return mode & 0o022 == 0
