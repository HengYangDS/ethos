"""Handle-bound immutable publication for source-budget replay artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from contextlib import suppress
from pathlib import Path
from pathlib import PurePosixPath
from typing import Never

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
_WRITE_FAILED_MESSAGE = "replay artifact write failed"
_TEMPORARY_EXHAUSTED_MESSAGE = "replay artifact temporary name exhausted"
_DIRECTORY_CHANGED_MESSAGE = "replay artifact directory changed"


def _invalid(message: str) -> Never:
    raise ValueError(message)


def _artifact_data(payload: dict[str, object]) -> tuple[bytes, str]:
    if type(payload) is not dict or any(type(key) is not str for key in payload):
        _invalid("replay artifact payload invalid")
    declared = payload.get("digest")
    unsigned = {key: value for key, value in payload.items() if key != "digest"}
    digest = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if type(declared) is not str or declared != digest:
        _invalid("replay artifact digest invalid")
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(), digest


def _artifact_target(
    root: Path,
    artifact_root: str,
    requested: Path | None,
    digest: str,
) -> tuple[Path, tuple[str, ...], str, Path]:
    resolved = root.resolve(strict=True)
    configured = PurePosixPath(artifact_root)
    if (
        not artifact_root
        or "\\" in artifact_root
        or configured.is_absolute()
        or str(configured) != artifact_root
        or any(part in {"", ".", ".."} for part in configured.parts)
    ):
        _invalid("replay artifact root invalid")
    if requested is None:
        relative = configured / f"{digest}.json"
    else:
        target = requested if requested.is_absolute() else resolved / requested
        target = Path(os.path.normpath(target))
        try:
            relative = PurePosixPath(target.relative_to(resolved).as_posix())
        except ValueError:
            _invalid("replay output must remain under configured artifact root")
    prefix = relative.parts[: len(configured.parts)]
    if prefix != configured.parts or len(relative.parts) == len(configured.parts):
        _invalid("replay output must remain under configured artifact root")
    return resolved, relative.parts[:-1], relative.name, resolved.joinpath(*relative.parts)


def _open_parent(root: Path, parts: tuple[str, ...], *, create: bool = True) -> int:
    descriptor = os.open(root, _DIR_FLAGS)
    try:
        for part in parts:
            try:
                child = os.open(part, _DIR_FLAGS, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                with suppress(FileExistsError):
                    os.mkdir(part, 0o755, dir_fd=descriptor)
                child = os.open(part, _DIR_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
    except BaseException:
        os.close(descriptor)
        raise
    else:
        return descriptor


def _parent_is_current(root: Path, parts: tuple[str, ...], parent: int) -> bool:
    try:
        current = _open_parent(root, parts, create=False)
    except OSError:
        return False
    try:
        expected = os.fstat(parent)
        actual = os.fstat(current)
    except OSError:
        return False
    else:
        return (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino)
    finally:
        os.close(current)


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError(_WRITE_FAILED_MESSAGE)
        view = view[written:]


def _same_existing(parent: int, name: str, data: bytes) -> bool:
    descriptor = os.open(name, _READ_FLAGS, dir_fd=parent)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size != len(data):
            return False
        chunks = bytearray()
        while chunk := os.read(descriptor, max(1, len(data) - len(chunks))):
            chunks.extend(chunk)
        after = os.fstat(descriptor)
        before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        return before_identity == after_identity and bytes(chunks) == data
    finally:
        os.close(descriptor)


def _temporary(parent: int, final_name: str) -> tuple[int, str]:
    for _ in range(16):
        name = f".{final_name}.{secrets.token_hex(8)}"
        try:
            return os.open(name, _WRITE_FLAGS, 0o600, dir_fd=parent), name
        except FileExistsError:
            pass
    raise FileExistsError(_TEMPORARY_EXHAUSTED_MESSAGE)


def write_replay_artifact(
    root: Path,
    artifact_root: str,
    requested: Path | None,
    payload: dict[str, object],
) -> Path:
    """Publish one immutable artifact relative to a verified directory handle."""
    data, digest = _artifact_data(payload)
    root, parents, name, output = _artifact_target(root, artifact_root, requested, digest)
    parent = _open_parent(root, parents)
    temporary = ""
    published = False
    try:
        descriptor, temporary = _temporary(parent, name)
        try:
            _write_all(descriptor, data)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        try:
            os.link(
                temporary,
                name,
                src_dir_fd=parent,
                dst_dir_fd=parent,
                follow_symlinks=False,
            )
            published = True
        except FileExistsError:
            if not _same_existing(parent, name, data):
                _invalid("conflicting replay artifact already exists")
        finally:
            os.unlink(temporary, dir_fd=parent)
            temporary = ""
        if not _parent_is_current(root, parents, parent):
            if published:
                with suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=parent)
                os.fsync(parent)
            raise OSError(_DIRECTORY_CHANGED_MESSAGE)
        os.fsync(parent)
        return output
    finally:
        if temporary:
            with suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=parent)
        os.close(parent)
