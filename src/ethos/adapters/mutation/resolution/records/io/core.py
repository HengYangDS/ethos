"""Descriptor-relative, identity-bound current-record storage primitives."""

from __future__ import annotations

import fcntl
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

_RECORD_PATH_UNSAFE = "lane_resolution_record_path_unsafe"
_CURRENT_RECORD_CHANGED = "lane_resolution_current_record_changed"
_CURRENT_RECORD_INVALID = "lane_resolution_current_record_invalid"
_MAX_CURRENT_RECORD_BYTES = 16 * 1024 * 1024


def write_record_bytes(destination: Path, content: bytes, *, record_root: Path) -> None:
    """Link one immutable record through held no-follow directory descriptors."""
    with roots.open_record_parent(record_root, destination, create=True) as parent:
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
    try:
        _remove_record_bytes(
            destination,
            expected=expected,
            record_root=record_root,
            locked_descriptor=locked_descriptor,
        )
    except FileNotFoundError as error:
        raise OSError(_RECORD_PATH_UNSAFE) from error


def read_descriptor_bytes(descriptor: int) -> bytes:
    """Read bounded raw bytes from one stable regular-file descriptor."""
    try:
        return posix.read_stable_descriptor(descriptor, max_bytes=_MAX_CURRENT_RECORD_BYTES)
    except ValueError:
        raise ValueError(_CURRENT_RECORD_INVALID) from None


def read_record_bytes(destination: Path, *, record_root: Path) -> bytes:
    """Read one current record through no-follow identity-bound descriptors."""
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        roots.require_parent_identity(parent)
        descriptor = posix.open_regular_file(parent.parent_descriptor, parent.name)
        try:
            content = read_descriptor_bytes(descriptor)
            if not posix.descriptor_matches_entry(
                parent.parent_descriptor, parent.name, descriptor
            ):
                raise OSError(_RECORD_PATH_UNSAFE)
            roots.require_parent_identity(parent)
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
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        roots.require_parent_identity(parent)
        if not posix.descriptor_matches_entry(parent.parent_descriptor, parent.name, descriptor):
            raise OSError(_RECORD_PATH_UNSAFE)
        roots.require_parent_identity(parent)


@contextmanager
def lock_record(destination: Path, *, record_root: Path) -> Iterator[int]:
    """Open and non-blockingly lock one exact visible record for a writer CAS."""
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        descriptor = posix.open_regular_file(parent.parent_descriptor, parent.name)
        locked = False
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
            if not posix.descriptor_matches_entry(
                parent.parent_descriptor, parent.name, descriptor
            ):
                raise OSError(_RECORD_PATH_UNSAFE)
            roots.require_parent_identity(parent)
            yield descriptor
            roots.require_parent_identity(parent)
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
    with roots.open_record_parent(record_root, reservation, create=True) as parent:
        roots.require_parent_identity(parent)
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
    """Hold exclusive ownership of one new or explicitly recovered sidecar."""
    with roots.open_record_parent(record_root, reservation, create=True) as parent:
        roots.require_parent_identity(parent)
        blocker_exists = (
            posix.entry_file_identity(parent.parent_descriptor, blocker.name) is not None
        )
        if blocker_exists and mode != "recover_completed":
            raise FileExistsError(blocker)
        if (
            blocker_exists
            and posix.entry_file_identity(parent.parent_descriptor, parent.name) is None
        ):
            yield None
            roots.require_parent_identity(parent)
            return
        created_identity: posix.FileIdentity | None = None
        try:
            descriptor = _create_locked_bound_bytes(parent, expected)
            created_identity = posix.file_identity(os.fstat(descriptor))
        except FileExistsError:
            if mode == "create":
                raise
            descriptor = _lock_existing_bound_record(parent, expected)
        try:
            roots.require_parent_identity(parent)
            if (
                posix.entry_file_identity(parent.parent_descriptor, blocker.name) is not None
                and mode != "recover_completed"
            ):
                if created_identity is not None:
                    posix.remove_owned_entry(
                        parent.parent_descriptor, parent.name, created_identity
                    )
                raise FileExistsError(blocker)
            yield descriptor
            roots.require_parent_identity(parent)
        finally:
            posix.unlock_close(descriptor)


def _write_bound_bytes(parent: roots.RecordParent, content: bytes) -> None:
    roots.require_parent_identity(parent)
    if posix.entry_file_identity(parent.parent_descriptor, parent.name) is not None:
        raise FileExistsError(parent.destination)
    temporary, temporary_identity = posix.prepare_bound_file(
        parent.parent_descriptor, parent.name, content
    )
    record_identity = temporary_identity
    linked = verified = temporary_removed = False
    try:
        os.link(
            temporary,
            parent.name,
            src_dir_fd=parent.parent_descriptor,
            dst_dir_fd=parent.parent_descriptor,
            follow_symlinks=False,
        )
        linked = True
        linked_identity = roots.require_entry_identity(
            parent,
            temporary,
            match_name=parent.name,
            changed=False,
        )
        record_identity = linked_identity
        temporary_identity = linked_identity
        posix.remove_owned_entry(
            parent.parent_descriptor,
            temporary,
            temporary_identity,
            sync=False,
        )
        temporary_removed = True
        record_identity = roots.require_entry_identity(parent, parent.name, changed=False)
        roots.require_parent_identity(parent)
        _require_record(parent, record_identity, content, changed=False)
        verified = True
        os.fsync(parent.parent_descriptor)
        roots.require_parent_identity(parent)
    except BaseException:
        if linked and (
            not verified
            or not roots.directory_binding_matches(
                parent.record_root,
                parent.category,
                parent.root_identity,
                parent.parent_identity,
            )
        ):
            with suppress(OSError):
                posix.remove_owned_entry(parent.parent_descriptor, parent.name, record_identity)
        raise
    finally:
        if not temporary_removed:
            with suppress(OSError):
                posix.remove_owned_entry(parent.parent_descriptor, temporary, temporary_identity)


def _create_locked_bound_bytes(parent: roots.RecordParent, content: bytes) -> int:
    roots.require_parent_identity(parent)
    if posix.entry_file_identity(parent.parent_descriptor, parent.name) is not None:
        raise FileExistsError(parent.destination)
    descriptor, identity = posix.create_locked_file_link(
        parent.parent_descriptor,
        parent.name,
        content,
    )
    try:
        roots.require_parent_identity(parent)
        _require_record(parent, identity, content, changed=False)
    except BaseException:
        with suppress(OSError):
            posix.remove_owned_entry(parent.parent_descriptor, parent.name, identity)
        posix.unlock_close(descriptor)
        raise
    return descriptor


def _lock_existing_bound_record(parent: roots.RecordParent, expected: bytes) -> int:
    try:
        descriptor = posix.lock_regular_file(parent.parent_descriptor, parent.name)
    except BlockingIOError as error:
        raise FileExistsError(parent.destination) from error
    try:
        _require_locked_record_content(parent, descriptor, expected)
    except BaseException:
        posix.unlock_close(descriptor)
        raise
    return descriptor


def _require_locked_record_content(
    parent: roots.RecordParent,
    descriptor: int,
    expected: bytes,
) -> None:
    if read_descriptor_bytes(descriptor) != expected or not posix.descriptor_matches_entry(
        parent.parent_descriptor, parent.name, descriptor
    ):
        raise ValueError(_CURRENT_RECORD_CHANGED)
    roots.require_parent_identity(parent)


def _replace_record_bytes(
    destination: Path,
    replacement: bytes,
    *,
    expected: bytes,
    record_root: Path,
    locked_descriptor: int,
) -> None:
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        temporary, temporary_identity = posix.prepare_bound_file(
            parent.parent_descriptor, parent.name, replacement
        )
        staging = posix.staging_name(parent.name, expected)
        record_identity = temporary_identity
        staged = linked = temporary_removed = False
        try:
            staging_identity = _stage_expected_record(parent, locked_descriptor, expected, staging)
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
            linked_identity = roots.require_entry_identity(
                parent,
                temporary,
                match_name=parent.name,
                changed=True,
            )
            record_identity = linked_identity
            temporary_identity = linked_identity
            posix.remove_owned_entry(
                parent.parent_descriptor,
                temporary,
                temporary_identity,
                sync=False,
            )
            temporary_removed = True
            record_identity = roots.require_entry_identity(parent, parent.name, changed=True)
            roots.require_parent_identity(parent)
            _require_record(parent, record_identity, replacement, changed=True)
            os.fsync(parent.parent_descriptor)
            roots.require_parent_identity(parent)
            posix.remove_owned_entry(
                parent.parent_descriptor,
                staging,
                staging_identity,
            )
            staged = False
            roots.require_parent_identity(parent)
        except BaseException as error:
            if staged:
                rollback_identity = posix.file_identity(os.fstat(locked_descriptor))
                canonical_identity = posix.entry_file_identity(
                    parent.parent_descriptor, parent.name
                )
                if (
                    posix.entry_file_identity(parent.parent_descriptor, staging)
                    == rollback_identity
                ):
                    if canonical_identity == record_identity:
                        posix.remove_owned_entry(
                            parent.parent_descriptor,
                            parent.name,
                            record_identity,
                        )
                    if canonical_identity in (None, record_identity):
                        posix.restore_staged_file(
                            parent.parent_descriptor,
                            staging,
                            parent.name,
                            rollback_identity,
                        )
                    else:
                        raise OSError(posix.errno.ESTALE, parent.name) from error
            elif linked and not roots.directory_binding_matches(
                parent.record_root,
                parent.category,
                parent.root_identity,
                parent.parent_identity,
            ):
                with suppress(OSError):
                    posix.remove_owned_entry(
                        parent.parent_descriptor,
                        parent.name,
                        record_identity,
                    )
            raise
        finally:
            if not temporary_removed:
                with suppress(OSError):
                    posix.remove_owned_entry(
                        parent.parent_descriptor, temporary, temporary_identity
                    )


def _remove_record_bytes(
    destination: Path,
    *,
    expected: bytes,
    record_root: Path,
    locked_descriptor: int,
) -> None:
    with roots.open_record_parent(record_root, destination, create=False) as parent:
        staging = posix.staging_name(parent.name, expected)
        staging_identity = _stage_expected_record(parent, locked_descriptor, expected, staging)
        deleted = False
        try:
            roots.require_parent_identity(parent)
            posix.remove_owned_entry(
                parent.parent_descriptor,
                staging,
                staging_identity,
            )
            deleted = True
            roots.require_parent_identity(parent)
        except BaseException:
            if not deleted:
                restored_identity = posix.file_identity(os.fstat(locked_descriptor))
                posix.restore_staged_file(
                    parent.parent_descriptor,
                    staging,
                    parent.name,
                    restored_identity,
                )
            raise
        if posix.entry_file_identity(parent.parent_descriptor, parent.name) is not None:
            raise ValueError(_CURRENT_RECORD_CHANGED)


def _stage_expected_record(
    parent: roots.RecordParent,
    locked_descriptor: int,
    expected: bytes,
    staging: str,
) -> posix.FileIdentity:
    roots.require_parent_identity(parent)
    if read_descriptor_bytes(locked_descriptor) != expected or not posix.descriptor_matches_entry(
        parent.parent_descriptor, parent.name, locked_descriptor
    ):
        raise ValueError(_CURRENT_RECORD_CHANGED)
    if posix.entry_file_identity(parent.parent_descriptor, staging) is not None:
        raise ValueError(_CURRENT_RECORD_CHANGED)
    try:
        descriptor, staging_identity = posix.stage_locked_file(
            parent.parent_descriptor,
            parent.name,
            staging,
            locked_descriptor,
        )
    except OSError as error:
        if (
            error.errno == posix.errno.ESTALE
            and posix.entry_file_identity(parent.parent_descriptor, parent.name) is not None
        ):
            raise ValueError(_CURRENT_RECORD_CHANGED) from None
        raise
    try:
        valid = (
            posix.file_identity(os.fstat(locked_descriptor)) == staging_identity
            and posix.file_identity(os.fstat(descriptor)) == staging_identity
            and read_descriptor_bytes(descriptor) == expected
            and posix.descriptor_matches_entry(
                parent.parent_descriptor,
                staging,
                descriptor,
            )
        )
        roots.require_parent_identity(parent)
    except BaseException:
        posix.restore_staged_file(parent.parent_descriptor, staging, parent.name, staging_identity)
        raise
    finally:
        os.close(descriptor)
    if valid:
        return staging_identity
    posix.restore_staged_file(parent.parent_descriptor, staging, parent.name, staging_identity)
    raise ValueError(_CURRENT_RECORD_CHANGED)


def _read_bound_bytes(parent: roots.RecordParent) -> bytes:
    roots.require_parent_identity(parent)
    descriptor = posix.open_regular_file(parent.parent_descriptor, parent.name)
    try:
        content = read_descriptor_bytes(descriptor)
        if not posix.descriptor_matches_entry(parent.parent_descriptor, parent.name, descriptor):
            raise OSError(_RECORD_PATH_UNSAFE)
        roots.require_parent_identity(parent)
        return content
    finally:
        os.close(descriptor)


def _require_record(
    parent: roots.RecordParent,
    identity: posix.FileIdentity,
    content: bytes,
    *,
    changed: bool,
) -> None:
    matches = (
        posix.entry_file_identity(parent.parent_descriptor, parent.name) == identity
        and _read_bound_bytes(parent) == content
    )
    if matches:
        return
    if changed:
        raise ValueError(_CURRENT_RECORD_CHANGED)
    raise OSError(_RECORD_PATH_UNSAFE)
