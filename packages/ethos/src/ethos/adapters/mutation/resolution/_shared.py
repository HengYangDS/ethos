"""Private shared helpers for lane-resolution adapters."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def sha256_digest(path: Path) -> str:
    """Return the hex sha256 digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
