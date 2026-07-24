"""Descriptor-relative, identity-bound current-record storage primitives."""

from __future__ import annotations

import fcntl
import hashlib
import os
import stat
import uuid
from contextlib import contextmanager
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.records.io.posix as posix
from ethos.adapters.mutation.resolution._shared import record_destination_safe

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_RECORD_PATH_UNSAFE = "lane_resolution_record_path_unsafe"
_CURRENT_RECORD_CHANGED = "lane_resolution_current_record_changed"
_CURRENT_RECORD_INVALID = "lane_resolution_current_record_invalid"
_MAX_CURRENT_RECORD_BYTES = 16 * 1024 * 1024
_RECORD_PATH_PART_COUNT = 2


@dataclass(frozen=True, slots=True)
class _RecordParent:
    record_root: Path
    destination: Path
    root_descriptor: int
    parent_descriptor: int
    category: str
    name: str
    root_identity: posix.DirectoryIdentity
    parent_identity: posix.DirectoryIdentity


def write_record_bytes(destination: Path, content: bytes, *, record_root: Path) -> None:
    """Link one immutable record through held no-follow directory descriptors."""
    with _open_record_parent(record_root, destination, create=True) as parent:
        _write_bound_bytes(parent, content)


def replace_record_bytes(
    destination: Path,
    replacement: bytes,
    *,
    expected: bytes,
    record_root: Path,
    locked_descriptor: int | None = None,
) -> None:
    """Replace only one exact canonical record while preserving competitors."""
    if locked_descriptor is None:
        with lock_record(destination, record_root=record_root) as descriptor:
            _replace_record_bytes(
                destination,
                replacement,
                expected=expected,
                record_root=record_root,
                locked_descriptor=descriptor,
            )
        return
    _replace_record_bytes(
        destination,
        replacement,
        expected=expected,
        record_root=record_root,
        locked_descriptor=locked_descriptor,
    )


def remove_record_bytes(
    destination: Path,
    *,
    expected: bytes,
    record_root: Path,
    locked_descriptor: int | None = None,
) -> None:
    """Remove only one exact canonical record while preserving competitors."""
    if locked_descriptor is None:
        with lock_record(destination, record_root=record_root) as descriptor:
            _remove_record_bytes(
                destination,
                expected=expected,
                record_root=record_root,
                locked_descriptor=descriptor,
            )
        return
    _remove_record_bytes(
        destination,
        expected=expected,
        record_root=record_root,
        locked_descriptor=locked_descriptor,
    )


def read_descriptor_bytes(descriptor: int) -> bytes:
    """Read bounded raw bytes from one stable regular-file descriptor."""
    before = posix.file_identity(os.fstat(descriptor))
    if not stat.S_ISREG(before[2]) or before[3] > _MAX_CURRENT_RECORD_BYTES:
        raise ValueError(_CURRENT_RECORD_INVALID)
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    remaining = _MAX_CURRENT_RECORD_BYTES + 1
    while remaining and (chunk := os.read(descriptor, min(64 * 1024, remaining))):
        chunks.append(chunk)
        remaining -= len(chunk)
    content = b"".join(chunks)
    if len(content) > _MAX_CURRENT_RECORD_BYTES or before != posix.file_identity(
        os.fstat(descriptor)
    ):
        raise ValueError(_CURRENT_RECORD_INVALID)
    return content


def read_record_bytes(destination: Path, *, record_root: Path) -> bytes:
    """Read one current record through no-follow identity-bound descriptors."""
    with _open_record_parent(record_root, destination, create=False) as parent:
        _require_parent_identity(parent)
        descriptor = _open_record_file(parent)
        try:
            content = read_descriptor_bytes(descriptor)
            if not _descriptor_matches_entry(parent, descriptor):
                raise OSError(_RECORD_PATH_UNSAFE)
            _require_parent_identity(parent)
            return content
        finally:
            os.close(descriptor)


def require_locked_record_identity(
    destination: Path,
    descriptor: int,
    *,
    record_root: Path,
) -> None:
    """Require one locked descriptor to remain the exact visible record path."""
    with _open_record_parent(record_root, destination, create=False) as parent:
        _require_parent_identity(parent)
        if not _descriptor_matches_entry(parent, descriptor):
            raise OSError(_RECORD_PATH_UNSAFE)


@contextmanager
def lock_record(destination: Path, *, record_root: Path) -> Iterator[int]:
    """Open and non-blockingly lock one exact visible record for a writer CAS."""
    with _open_record_parent(record_root, destination, create=False) as parent:
        descriptor = _open_record_file(parent)
        locked = False
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
            if not _descriptor_matches_entry(parent, descriptor):
                raise OSError(_RECORD_PATH_UNSAFE)
            _require_parent_identity(parent)
            yield descriptor
        finally:
            if locked:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def reserve_record_sidecar(
    reservation: Path,
    blocker: Path,
    *,
    expected: bytes,
    record_root: Path,
) -> None:
    """Create one exclusive exact sidecar while the completion name is absent."""
    with _open_record_parent(record_root, reservation, create=True) as parent:
        if posix.entry_file_identity(parent.parent_descriptor, blocker.name) is not None:
            raise FileExistsError(blocker)
        try:
            _write_bound_bytes(parent, expected)
        except FileExistsError as error:
            try:
                content = _read_bound_bytes(parent)
            except OSError:
                if posix.entry_file_identity(parent.parent_descriptor, parent.name) is None:
                    raise FileExistsError(parent.destination) from error
                raise
            if content != expected:
                raise ValueError(_CURRENT_RECORD_CHANGED) from None
            raise FileExistsError(parent.destination) from error
        _require_parent_identity(parent)
        if posix.entry_file_identity(parent.parent_descriptor, blocker.name) is not None:
            remove_record_bytes(reservation, expected=expected, record_root=record_root)
            raise FileExistsError(blocker)


def record_entry_exists(destination: Path, *, record_root: Path) -> bool:
    """Return whether one descriptor-bound record entry currently exists."""
    with _open_record_parent(record_root, destination, create=False) as parent:
        _require_parent_identity(parent)
        return posix.entry_file_identity(parent.parent_descriptor, parent.name) is not None


def _write_bound_bytes(parent: _RecordParent, content: bytes) -> None:
    _require_parent_identity(parent)
    if posix.entry_file_identity(parent.parent_descriptor, parent.name) is not None:
        raise FileExistsError(parent.destination)
    temporary = _temporary_name(parent.name)
    descriptor = posix.create_bound_file(parent.parent_descriptor, temporary)
    try:
        posix.write_all(descriptor, content)
        os.fsync(descriptor)
        temporary_identity = posix.file_identity(os.fstat(descriptor))
    finally:
        os.close(descriptor)
    linked = False
    try:
        os.link(
            temporary,
            parent.name,
            src_dir_fd=parent.parent_descriptor,
            dst_dir_fd=parent.parent_descriptor,
            follow_symlinks=False,
        )
        linked = True
        _require_parent_identity(parent)
        _require_written_record(parent, temporary_identity, content)
        os.fsync(parent.parent_descriptor)
    except BaseException:
        if linked and posix.same_content_identity(
            posix.entry_file_identity(parent.parent_descriptor, parent.name), temporary_identity
        ):
            os.unlink(parent.name, dir_fd=parent.parent_descriptor)
        raise
    finally:
        posix.unlink_if_present(parent.parent_descriptor, temporary)


def _replace_record_bytes(
    destination: Path,
    replacement: bytes,
    *,
    expected: bytes,
    record_root: Path,
    locked_descriptor: int,
) -> None:
    with _open_record_parent(record_root, destination, create=False) as parent:
        temporary = _temporary_name(parent.name)
        descriptor = posix.create_bound_file(parent.parent_descriptor, temporary)
        try:
            posix.write_all(descriptor, replacement)
            os.fsync(descriptor)
            temporary_identity = posix.file_identity(os.fstat(descriptor))
        finally:
            os.close(descriptor)
        staging = _staging_name(parent.name, expected)
        staged = linked = False
        try:
            _stage_expected_record(parent, locked_descriptor, expected, staging)
            staged = True
            try:
                os.link(
                    temporary,
                    parent.name,
                    src_dir_fd=parent.parent_descriptor,
                    dst_dir_fd=parent.parent_descriptor,
                    follow_symlinks=False,
                )
            except FileExistsError as error:
                raise ValueError(_CURRENT_RECORD_CHANGED) from error
            linked = True
            _require_parent_identity(parent)
            _require_replaced_record(parent, temporary_identity, replacement)
            os.unlink(staging, dir_fd=parent.parent_descriptor)
            staged = False
            os.fsync(parent.parent_descriptor)
        except BaseException:
            if linked and posix.same_content_identity(
                posix.entry_file_identity(parent.parent_descriptor, parent.name), temporary_identity
            ):
                os.unlink(parent.name, dir_fd=parent.parent_descriptor)
            if staged:
                _restore_staged_record(parent, staging)
            raise
        finally:
            posix.unlink_if_present(parent.parent_descriptor, temporary)


def _remove_record_bytes(
    destination: Path,
    *,
    expected: bytes,
    record_root: Path,
    locked_descriptor: int,
) -> None:
    with _open_record_parent(record_root, destination, create=False) as parent:
        staging = _staging_name(parent.name, expected)
        _stage_expected_record(parent, locked_descriptor, expected, staging)
        try:
            _require_parent_identity(parent)
            os.unlink(staging, dir_fd=parent.parent_descriptor)
            os.fsync(parent.parent_descriptor)
        except BaseException:
            _restore_staged_record(parent, staging)
            raise
        if posix.entry_file_identity(parent.parent_descriptor, parent.name) is not None:
            raise ValueError(_CURRENT_RECORD_CHANGED)


def _stage_expected_record(
    parent: _RecordParent,
    locked_descriptor: int,
    expected: bytes,
    staging: str,
) -> None:
    _require_parent_identity(parent)
    if read_descriptor_bytes(locked_descriptor) != expected or not _descriptor_matches_entry(
        parent, locked_descriptor
    ):
        raise ValueError(_CURRENT_RECORD_CHANGED)
    if posix.entry_file_identity(parent.parent_descriptor, staging) is not None:
        raise ValueError(_CURRENT_RECORD_CHANGED)
    posix.rename_no_replace(parent.parent_descriptor, parent.name, staging)
    descriptor = os.open(staging, posix.file_flags(), dir_fd=parent.parent_descriptor)
    try:
        valid = (
            posix.file_identity(os.fstat(descriptor))
            == posix.file_identity(os.fstat(locked_descriptor))
            and read_descriptor_bytes(descriptor) == expected
        )
    finally:
        os.close(descriptor)
    if valid:
        return
    _restore_staged_record(parent, staging)
    raise ValueError(_CURRENT_RECORD_CHANGED)


def _restore_staged_record(parent: _RecordParent, staging: str) -> None:
    if posix.entry_file_identity(parent.parent_descriptor, staging) is None:
        return
    if posix.entry_file_identity(parent.parent_descriptor, parent.name) is not None:
        return
    try:
        posix.rename_no_replace(parent.parent_descriptor, staging, parent.name)
        os.fsync(parent.parent_descriptor)
    except OSError:
        pass


def _read_bound_bytes(parent: _RecordParent) -> bytes:
    descriptor = _open_record_file(parent)
    try:
        content = read_descriptor_bytes(descriptor)
        if not _descriptor_matches_entry(parent, descriptor):
            raise OSError(_RECORD_PATH_UNSAFE)
        return content
    finally:
        os.close(descriptor)


@contextmanager
def _open_record_parent(
    record_root: Path,
    destination: Path,
    *,
    create: bool,
) -> Iterator[_RecordParent]:
    category, name = _record_parts(record_root, destination)
    if not record_destination_safe(record_root, destination):
        raise OSError(_RECORD_PATH_UNSAFE)
    if create:
        record_root.mkdir(parents=True, exist_ok=True)
    root_descriptor: int | None = None
    parent_descriptor: int | None = None
    try:
        root_descriptor = os.open(record_root, posix.directory_flags())
        root_identity = posix.directory_identity(os.fstat(root_descriptor))
        if create:
            with suppress(FileExistsError):
                os.mkdir(category, mode=0o700, dir_fd=root_descriptor)
        parent_descriptor = os.open(category, posix.directory_flags(), dir_fd=root_descriptor)
        parent_identity = posix.directory_identity(os.fstat(parent_descriptor))
        parent = _RecordParent(
            record_root,
            destination,
            root_descriptor,
            parent_descriptor,
            category,
            name,
            root_identity,
            parent_identity,
        )
        _require_parent_identity(parent)
    except (FileNotFoundError, FileExistsError):
        _close_record_parent(parent_descriptor, root_descriptor)
        raise
    except OSError as error:
        _close_record_parent(parent_descriptor, root_descriptor)
        raise OSError(_RECORD_PATH_UNSAFE) from error
    try:
        yield parent
    finally:
        os.close(parent_descriptor)
        os.close(root_descriptor)


def _close_record_parent(parent_descriptor: int | None, root_descriptor: int | None) -> None:
    for descriptor in (parent_descriptor, root_descriptor):
        if descriptor is not None:
            os.close(descriptor)


def _record_parts(record_root: Path, destination: Path) -> tuple[str, str]:
    try:
        relative = destination.absolute().relative_to(record_root.absolute())
    except ValueError as error:
        raise OSError(_RECORD_PATH_UNSAFE) from error
    if len(relative.parts) != _RECORD_PATH_PART_COUNT or ".." in relative.parts:
        raise OSError(_RECORD_PATH_UNSAFE)
    return relative.parts[0], relative.parts[1]


def _require_parent_identity(parent: _RecordParent) -> None:
    try:
        root_visible = posix.directory_identity(parent.record_root.stat(follow_symlinks=False))
        category_visible = posix.entry_directory_identity(parent.root_descriptor, parent.category)
    except OSError as error:
        raise OSError(_RECORD_PATH_UNSAFE) from error
    if root_visible != parent.root_identity or category_visible != parent.parent_identity:
        raise OSError(_RECORD_PATH_UNSAFE)


def _open_record_file(parent: _RecordParent) -> int:
    try:
        return posix.open_regular_file(parent.parent_descriptor, parent.name)
    except FileNotFoundError:
        raise
    except OSError as error:
        raise OSError(_RECORD_PATH_UNSAFE) from error


def _descriptor_matches_entry(parent: _RecordParent, descriptor: int) -> bool:
    try:
        return posix.entry_file_identity(
            parent.parent_descriptor, parent.name
        ) == posix.file_identity(os.fstat(descriptor))
    except OSError:
        return False


def _require_written_record(
    parent: _RecordParent,
    identity: posix.FileIdentity,
    content: bytes,
) -> None:
    if (
        not posix.same_content_identity(
            posix.entry_file_identity(parent.parent_descriptor, parent.name), identity
        )
        or _read_bound_bytes(parent) != content
    ):
        raise OSError(_RECORD_PATH_UNSAFE)


def _require_replaced_record(
    parent: _RecordParent,
    identity: posix.FileIdentity,
    content: bytes,
) -> None:
    if (
        not posix.same_content_identity(
            posix.entry_file_identity(parent.parent_descriptor, parent.name), identity
        )
        or _read_bound_bytes(parent) != content
    ):
        raise ValueError(_CURRENT_RECORD_CHANGED)


def _temporary_name(name: str) -> str:
    return f".{name}.{uuid.uuid4().hex}.tmp"


def _staging_name(name: str, expected: bytes) -> str:
    digest = hashlib.sha256(expected).hexdigest()
    return f".{name}.{digest}.{uuid.uuid4().hex}.cas"
