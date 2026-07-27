"""Descriptor-bound, compare-and-swap current-record storage."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextlib import suppress
from typing import TYPE_CHECKING
from typing import Literal

import ethos.adapters.mutation.resolution.records.io.posix as posix
import ethos.adapters.mutation.resolution.records.roots as roots

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_PATH_UNSAFE = "lane_resolution_record_path_unsafe"
_CHANGED = "lane_resolution_current_record_changed"
_INVALID = "lane_resolution_current_record_invalid"
_MAX_BYTES = 16 * 1024 * 1024


def write_record_bytes(destination: Path, content: bytes, *, record_root: Path) -> None:
    """Create one immutable current record without replacing a competitor."""
    with roots.open_record_parent(record_root, destination, create=True) as parent:
        roots.require_parent_identity(parent)
        descriptor, identity = posix.create_locked_file_link(
            parent.parent_descriptor, parent.name, content
        )
        try:
            _require_descriptor(parent, descriptor, content)
        except BaseException:
            with suppress(OSError):
                posix.remove_owned_entry(parent.parent_descriptor, parent.name, identity)
            raise
        finally:
            posix.unlock_close(descriptor)


def replace_record_bytes(
    destination: Path,
    replacement: bytes,
    *,
    expected: bytes,
    record_root: Path,
    locked_descriptor: int | None = None,
) -> None:
    """Replace one exact current record while preserving every competitor."""
    if locked_descriptor is None:
        with lock_record(destination, record_root=record_root) as descriptor:
            _mutate_record(destination, expected, replacement, record_root, descriptor)
        return
    _mutate_record(destination, expected, replacement, record_root, locked_descriptor)


def remove_record_bytes(
    destination: Path,
    *,
    expected: bytes,
    record_root: Path,
    locked_descriptor: int | None = None,
) -> None:
    """Remove one exact current record while preserving every competitor."""
    try:
        if locked_descriptor is None:
            with lock_record(destination, record_root=record_root) as descriptor:
                _mutate_record(destination, expected, None, record_root, descriptor)
        else:
            _mutate_record(destination, expected, None, record_root, locked_descriptor)
    except FileNotFoundError as error:
        raise OSError(_PATH_UNSAFE) from error


def read_descriptor_bytes(descriptor: int) -> bytes:
    """Read bounded bytes from one stable regular-file descriptor."""
    try:
        return posix.read_stable_descriptor(descriptor, max_bytes=_MAX_BYTES)
    except ValueError:
        raise ValueError(_INVALID) from None


def read_record_bytes(destination: Path, *, record_root: Path) -> bytes:
    """Read one current record through its held lexical parent."""
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        descriptor = posix.open_regular_file(parent.parent_descriptor, parent.name)
        try:
            content = read_descriptor_bytes(descriptor)
            _require_descriptor(parent, descriptor, content)
            return content
        finally:
            os.close(descriptor)


def require_locked_record_identity(
    destination: Path, descriptor: int, *, record_root: Path
) -> None:
    """Require one locked descriptor to remain the exact visible record."""
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        _require_visible(parent, descriptor)


@contextmanager
def lock_record(destination: Path, *, record_root: Path) -> Iterator[int]:
    """Hold one exact visible current record under a nonblocking writer lock."""
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        descriptor = posix.lock_regular_file(parent.parent_descriptor, parent.name)
        try:
            _require_visible(parent, descriptor)
            yield descriptor
            roots.require_parent_identity(parent)
        finally:
            posix.unlock_close(descriptor)


def reserve_record_sidecar(
    reservation: Path, blocker: Path, *, expected: bytes, record_root: Path
) -> None:
    """Create one exact sidecar only while its completion name is absent."""
    with roots.open_record_parent(record_root, reservation, create=True) as parent:
        _require_absent(parent, blocker.name, blocker)
        try:
            write_record_bytes(reservation, expected, record_root=record_root)
        except FileExistsError as error:
            try:
                current = read_record_bytes(reservation, record_root=record_root)
            except OSError:
                if posix.entry_file_identity(parent.parent_descriptor, parent.name) is None:
                    raise FileExistsError(parent.destination) from error
                raise
            if current != expected:
                raise ValueError(_CHANGED) from None
            raise FileExistsError(parent.destination) from error
        roots.require_parent_identity(parent)
        if posix.entry_file_identity(parent.parent_descriptor, blocker.name) is not None:
            remove_record_bytes(reservation, expected=expected, record_root=record_root)
            raise FileExistsError(blocker)


@contextmanager
def claim_record_sidecar(
    reservation: Path,
    blocker: Path,
    *,
    expected: bytes,
    record_root: Path,
    mode: Literal["create", "recover", "recover_completed"],
) -> Iterator[int | None]:
    """Hold exclusive ownership of a new or explicitly recovered sidecar."""
    with roots.open_record_parent(record_root, reservation, create=True) as parent:
        blocker_present = (
            posix.entry_file_identity(parent.parent_descriptor, blocker.name) is not None
        )
        if blocker_present and mode != "recover_completed":
            raise FileExistsError(blocker)
        if (
            blocker_present
            and posix.entry_file_identity(parent.parent_descriptor, parent.name) is None
        ):
            yield None
            roots.require_parent_identity(parent)
            return
        created: posix.FileIdentity | None = None
        try:
            descriptor, created = posix.create_locked_file_link(
                parent.parent_descriptor, parent.name, expected
            )
            try:
                _require_descriptor(parent, descriptor, expected)
            except BaseException:
                with suppress(OSError):
                    posix.remove_owned_entry(parent.parent_descriptor, parent.name, created)
                posix.unlock_close(descriptor)
                raise
        except FileExistsError:
            if mode == "create":
                raise
            descriptor = _lock_expected(parent, expected)
        try:
            if (
                posix.entry_file_identity(parent.parent_descriptor, blocker.name) is not None
                and mode != "recover_completed"
            ):
                if created is not None:
                    posix.remove_owned_entry(parent.parent_descriptor, parent.name, created)
                raise FileExistsError(blocker)
            yield descriptor
            roots.require_parent_identity(parent)
        finally:
            posix.unlock_close(descriptor)


def _mutate_record(
    destination: Path,
    expected: bytes,
    replacement: bytes | None,
    record_root: Path,
    locked: int,
) -> None:
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        _require_descriptor(parent, locked, expected)
        staging = posix.staging_name(parent.name, expected)
        if posix.entry_file_identity(parent.parent_descriptor, staging) is not None:
            raise ValueError(_CHANGED)
        staged_descriptor, predecessor = posix.stage_locked_file(
            parent.parent_descriptor, parent.name, staging, locked
        )
        os.close(staged_descriptor)
        installed: posix.FileIdentity | None = None
        temporary: tuple[str, posix.FileIdentity] | None = None
        try:
            roots.require_parent_identity(parent)
            if replacement is not None:
                temporary = posix.prepare_bound_file(
                    parent.parent_descriptor, parent.name, replacement
                )
                name, _identity = temporary
                try:
                    os.link(
                        name,
                        parent.name,
                        src_dir_fd=parent.parent_descriptor,
                        dst_dir_fd=parent.parent_descriptor,
                        follow_symlinks=False,
                    )
                except FileExistsError as error:
                    raise ValueError(_CHANGED) from error
                installed = roots.require_entry_identity(
                    parent, name, match_name=parent.name, changed=True
                )
                posix.remove_owned_entry(parent.parent_descriptor, name, installed, sync=False)
                temporary = None
                installed = roots.require_entry_identity(parent, parent.name, changed=True)
                _require_record(parent, installed, replacement)
                os.fsync(parent.parent_descriptor)
            posix.remove_owned_entry(parent.parent_descriptor, staging, predecessor)
            roots.require_parent_identity(parent)
        except BaseException as error:
            _restore_predecessor(parent, staging, predecessor, installed, error)
            raise
        finally:
            if temporary is not None:
                with suppress(OSError):
                    posix.remove_owned_entry(parent.parent_descriptor, *temporary)
        visible = posix.entry_file_identity(parent.parent_descriptor, parent.name)
        if (replacement is None and visible is not None) or (
            replacement is not None and visible != installed
        ):
            raise ValueError(_CHANGED)


def _restore_predecessor(
    parent: roots.RecordParent,
    staging: str,
    predecessor: posix.FileIdentity,
    installed: posix.FileIdentity | None,
    cause: BaseException,
) -> None:
    if posix.entry_file_identity(parent.parent_descriptor, staging) != predecessor:
        return
    visible = posix.entry_file_identity(parent.parent_descriptor, parent.name)
    if installed is not None and visible == installed:
        posix.remove_owned_entry(parent.parent_descriptor, parent.name, installed)
        visible = None
    if visible is None:
        posix.restore_staged_file(parent.parent_descriptor, staging, parent.name, predecessor)
    elif visible != installed:
        raise OSError(posix.errno.ESTALE, parent.name) from cause


def _lock_expected(parent: roots.RecordParent, expected: bytes) -> int:
    try:
        descriptor = posix.lock_regular_file(parent.parent_descriptor, parent.name)
    except BlockingIOError as error:
        raise FileExistsError(parent.destination) from error
    try:
        _require_descriptor(parent, descriptor, expected)
    except BaseException:
        posix.unlock_close(descriptor)
        raise
    else:
        return descriptor


def _require_visible(parent: roots.RecordParent, descriptor: int) -> None:
    roots.require_parent_identity(parent)
    if not posix.descriptor_matches_entry(parent.parent_descriptor, parent.name, descriptor):
        raise OSError(_PATH_UNSAFE)
    roots.require_parent_identity(parent)


def _require_descriptor(parent: roots.RecordParent, descriptor: int, expected: bytes) -> None:
    if read_descriptor_bytes(descriptor) != expected:
        raise ValueError(_CHANGED)
    _require_visible(parent, descriptor)


def _require_record(
    parent: roots.RecordParent, identity: posix.FileIdentity, expected: bytes
) -> None:
    descriptor = posix.open_identity_bound_file(parent.parent_descriptor, parent.name, identity)
    try:
        _require_descriptor(parent, descriptor, expected)
    finally:
        os.close(descriptor)


def _require_absent(parent: roots.RecordParent, name: str, path: Path) -> None:
    roots.require_parent_identity(parent)
    if posix.entry_file_identity(parent.parent_descriptor, name) is not None:
        raise FileExistsError(path)
