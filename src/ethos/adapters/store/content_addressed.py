"""Atomic immutable content-addressed file storage."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from stat import S_ISREG

from ethos.adapters.store.durable import sync_directory

# A record retirement can unlink a name between a writer's link and its read; link it again.
_ATTEMPTS = 3


def write_content_addressed(path: Path, payload: bytes, *, collision: str) -> Path:
    """Publish complete immutable bytes or reject an identity collision.

    An identical record is adopted again, its retention floor restarting; a name that vanishes
    while it is adopted is linked again, at most three times, before the write refuses.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = path.with_name(Path(temporary_name).name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        for _attempt in range(_ATTEMPTS):
            try:
                os.link(temporary, path)
            except FileExistsError:
                try:
                    _adopt(path, payload, collision)
                except FileNotFoundError:
                    continue
                return path
            sync_directory(path.parent)
            return path
    finally:
        temporary.unlink(missing_ok=True)
    raise ValueError(collision)


def _adopt(path: Path, payload: bytes, collision: str) -> None:
    """Accept an existing identical record and restart its floor; a vanished name propagates."""
    try:
        if not S_ISREG(path.lstat().st_mode):
            raise ValueError(collision)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        existing_descriptor = os.open(path, flags)
        with os.fdopen(existing_descriptor, "rb") as stream:
            if not S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError(collision)
            existing = stream.read()
    except FileNotFoundError:
        raise
    except OSError as error:
        raise ValueError(collision) from error
    if existing != payload:
        raise ValueError(collision)
    os.utime(path)
