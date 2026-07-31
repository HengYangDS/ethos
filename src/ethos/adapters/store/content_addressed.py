"""Atomic immutable content-addressed file storage."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from stat import S_ISREG


def write_content_addressed(path: Path, payload: bytes, *, collision: str) -> Path:
    """Publish complete immutable bytes or reject an identity collision."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = path.with_name(Path(temporary_name).name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except FileExistsError:
            try:
                if not S_ISREG(path.lstat().st_mode):
                    raise ValueError(collision)
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                existing_descriptor = os.open(path, flags)
                with os.fdopen(existing_descriptor, "rb") as stream:
                    if not S_ISREG(os.fstat(stream.fileno()).st_mode):
                        raise ValueError(collision)
                    existing = stream.read()
            except OSError as error:
                raise ValueError(collision) from error
            if existing != payload:
                raise ValueError(collision) from None
    finally:
        temporary.unlink(missing_ok=True)
    return path
