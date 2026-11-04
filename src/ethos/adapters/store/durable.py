"""Replace one small file durably: its bytes and its directory entry reach the disk first."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Windows cannot open a directory to synchronize it; its replacement is durable by itself.
_DIRECTORY_FSYNC_SUPPORTED = os.name == "posix"


def sync_directory(directory: Path) -> None:
    """Make a directory's entries durable where the platform allows it."""
    if not _DIRECTORY_FSYNC_SUPPORTED:
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def replace_durably(path: Path, payload: bytes) -> None:
    """Replace a file with complete bytes, synced before and after the rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)
