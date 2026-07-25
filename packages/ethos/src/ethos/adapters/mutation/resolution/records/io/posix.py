"""POSIX descriptor, identity, and no-replace filesystem primitives."""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import os
import stat
import uuid
from contextlib import suppress
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path

FileIdentity = tuple[int, int, int, int, int, int]
DirectoryIdentity = tuple[int, int, int]


def open_directory_path(path: Path, *, create: bool) -> int:
    """Open every absolute directory component without following symlinks."""
    if ".." in path.parts:
        raise OSError(errno.EINVAL, os.strerror(errno.EINVAL), path)
    absolute = path.absolute()
    descriptor = os.open(absolute.anchor, directory_flags())
    try:
        for component in absolute.parts[1:]:
            child = open_directory_child(descriptor, component, create=create)
            os.close(descriptor)
            descriptor = child
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def open_directory_child(parent_descriptor: int, name: str, *, create: bool) -> int:
    """Open one child after matching its lstat, descriptor, and final lstat identities."""
    before = entry_directory_identity(parent_descriptor, name)
    if before is None and create:
        with suppress(FileExistsError):
            os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
        before = entry_directory_identity(parent_descriptor, name)
    descriptor = os.open(name, directory_flags(), dir_fd=parent_descriptor)
    try:
        opened = directory_identity(os.fstat(descriptor))
        after = entry_directory_identity(parent_descriptor, name)
        _require_stable(condition=before is not None and before == opened == after, name=name)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def directory_binding(path: Path, child: str) -> tuple[DirectoryIdentity, DirectoryIdentity]:
    """Reopen one lexical root and child directory and return their identities."""
    root_descriptor = open_directory_path(path, create=False)
    child_descriptor: int | None = None
    try:
        child_descriptor = open_directory_child(root_descriptor, child, create=False)
        return (
            directory_identity(os.fstat(root_descriptor)),
            directory_identity(os.fstat(child_descriptor)),
        )
    finally:
        if child_descriptor is not None:
            os.close(child_descriptor)
        os.close(root_descriptor)


def directory_path_identity(path: Path) -> DirectoryIdentity:
    """Reopen one lexical directory path and return its no-follow identity."""
    descriptor = open_directory_path(path, create=False)
    try:
        return directory_identity(os.fstat(descriptor))
    finally:
        os.close(descriptor)


def directory_descriptor_is_live(
    path: Path,
    descriptor: int,
    expected_identity: DirectoryIdentity,
) -> bool:
    """Return whether a held directory is still the exact lexical path binding."""
    try:
        return (
            directory_identity(os.fstat(descriptor))
            == expected_identity
            == directory_path_identity(path)
        )
    except OSError:
        return False


def child_directory_is_live(  # noqa: PLR0913, RUF100 - exact root and child bindings
    path: Path,
    root_descriptor: int,
    root_identity: DirectoryIdentity,
    child_descriptor: int,
    child_name: str,
    child_identity: DirectoryIdentity,
) -> bool:
    """Return whether held root and child descriptors still match their lexical names."""
    try:
        visible_root, visible_child = directory_binding(path, child_name)
        return visible_root == root_identity == directory_identity(
            os.fstat(root_descriptor)
        ) and visible_child == child_identity == directory_identity(os.fstat(child_descriptor))
    except OSError:
        return False


def rename_no_replace(
    directory_descriptor: int,
    source_name: str,
    target_name: str,
) -> None:
    """Rename one descriptor-relative entry without replacing a competitor."""
    library = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source_name)
    target_bytes = os.fsencode(target_name)
    if hasattr(library, "renameatx_np"):
        result = library.renameatx_np(
            directory_descriptor,
            source_bytes,
            directory_descriptor,
            target_bytes,
            4,
        )
    elif hasattr(library, "renameat2"):
        result = library.renameat2(
            directory_descriptor,
            source_bytes,
            directory_descriptor,
            target_bytes,
            1,
        )
    else:
        raise OSError(errno.ENOTSUP, os.strerror(errno.ENOTSUP), target_name)
    if result == 0:
        return
    error = ctypes.get_errno()
    exception = FileExistsError if error == errno.EEXIST else OSError
    raise exception(error, os.strerror(error), target_name)


def directory_flags() -> int:
    """Return no-follow flags for opening one descriptor-bound directory."""
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )


def file_flags() -> int:
    """Return no-follow flags for opening one descriptor-bound regular file."""
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )


def create_bound_file(directory_descriptor: int, name: str) -> int:
    """Create one exclusive no-follow file relative to a held directory."""
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    return os.open(name, flags, 0o600, dir_fd=directory_descriptor)


def prepare_bound_file(
    directory_descriptor: int,
    target_name: str,
    content: bytes,
) -> tuple[str, FileIdentity]:
    """Create and sync one temporary file with cleanup armed before its first write."""
    temporary = f".{target_name}.{uuid.uuid4().hex}.tmp"
    descriptor = create_bound_file(directory_descriptor, temporary)
    identity = file_identity(os.fstat(descriptor))
    try:
        write_all(descriptor, content)
        os.fsync(descriptor)
        identity = file_identity(os.fstat(descriptor))
    except BaseException:
        with suppress(OSError):
            identity = file_identity(os.fstat(descriptor))
        os.close(descriptor)
        with suppress(OSError):
            remove_owned_entry(directory_descriptor, temporary, identity)
        raise
    try:
        os.close(descriptor)
    except BaseException:
        with suppress(OSError):
            remove_owned_entry(directory_descriptor, temporary, identity)
        raise
    return temporary, identity


def staging_name(target_name: str, expected: bytes) -> str:
    """Return one unique CAS staging name bound to the expected bytes."""
    digest = hashlib.sha256(expected).hexdigest()
    return f".{target_name}.{digest}.{uuid.uuid4().hex}.cas"


def create_locked_file_link(
    directory_descriptor: int,
    name: str,
    content: bytes,
) -> tuple[int, FileIdentity]:
    """Create, lock, and link one immutable file relative to a held directory."""
    temporary = f".{name}.{uuid.uuid4().hex}.tmp"
    descriptor = create_bound_file(directory_descriptor, temporary)
    identity = file_identity(os.fstat(descriptor))
    linked = locked = False
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        write_all(descriptor, content)
        os.fsync(descriptor)
        identity = file_identity(os.fstat(descriptor))
        os.link(
            temporary,
            name,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        linked = True
        identity = file_identity(os.fstat(descriptor))
        _require_stable(
            condition=entry_file_identity(directory_descriptor, name) == identity,
            name=name,
        )
        remove_owned_entry(directory_descriptor, temporary, identity, sync=False)
        identity = file_identity(os.fstat(descriptor))
        _require_stable(
            condition=entry_file_identity(directory_descriptor, name) == identity,
            name=name,
        )
        os.fsync(directory_descriptor)
    except BaseException:
        if linked:
            with suppress(OSError):
                remove_owned_entry(directory_descriptor, name, identity)
                identity = file_identity(os.fstat(descriptor))
        with suppress(OSError):
            remove_owned_entry(directory_descriptor, temporary, identity)
        if locked:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
        raise
    return descriptor, identity


def lock_regular_file(directory_descriptor: int, name: str) -> int:
    """Open and non-blockingly lock one descriptor-relative regular file."""
    descriptor = open_regular_file(directory_descriptor, name)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def unlock_close(descriptor: int) -> None:
    """Release one advisory lock and close its descriptor."""
    fcntl.flock(descriptor, fcntl.LOCK_UN)
    os.close(descriptor)


def open_regular_file(directory_descriptor: int, name: str) -> int:
    """Open one no-follow regular file relative to a held directory."""
    descriptor = os.open(name, file_flags(), dir_fd=directory_descriptor)
    if stat.S_ISREG(os.fstat(descriptor).st_mode):
        return descriptor
    os.close(descriptor)
    raise OSError(errno.EINVAL, os.strerror(errno.EINVAL), name)


def read_bound_file(
    directory_descriptor: int,
    name: str,
    expected_identity: FileIdentity,
    *,
    max_bytes: int,
) -> bytes | None:
    """Read one identity-bound file while enforcing a fixed byte ceiling."""
    descriptor = open_identity_bound_file(directory_descriptor, name, expected_identity)
    try:
        if expected_identity[3] > max_bytes:
            return None
        remaining = max_bytes + 1
        chunks: list[bytes] = []
        while remaining and (chunk := os.read(descriptor, min(1024 * 1024, remaining))):
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        return (
            content
            if len(content) <= max_bytes
            and _file_binding_matches(directory_descriptor, name, descriptor, expected_identity)
            else None
        )
    finally:
        os.close(descriptor)


def read_stable_descriptor(descriptor: int, *, max_bytes: int) -> bytes:
    """Read bounded bytes only while one descriptor identity stays unchanged."""
    before = file_identity(os.fstat(descriptor))
    if not stat.S_ISREG(before[2]) or before[3] > max_bytes:
        raise ValueError
    os.lseek(descriptor, 0, os.SEEK_SET)
    remaining = max_bytes + 1
    chunks: list[bytes] = []
    while remaining and (chunk := os.read(descriptor, min(64 * 1024, remaining))):
        chunks.append(chunk)
        remaining -= len(chunk)
    content = b"".join(chunks)
    if len(content) > max_bytes or before != file_identity(os.fstat(descriptor)):
        raise ValueError
    return content


def digest_bound_file(
    directory_descriptor: int,
    name: str,
    expected_identity: FileIdentity,
) -> str | None:
    """Hash one identity-bound file and reject any path or descriptor drift."""
    descriptor = open_identity_bound_file(directory_descriptor, name, expected_identity)
    try:
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        return (
            digest.hexdigest()
            if _file_binding_matches(directory_descriptor, name, descriptor, expected_identity)
            else None
        )
    finally:
        os.close(descriptor)


def digest_matches_identity(
    directory_descriptor: int,
    name: str,
    expected_identity: FileIdentity,
    expected_sha256: str,
) -> bool:
    """Match a digest only while the exact current-file identity remains bound."""
    identity = entry_file_identity(directory_descriptor, name)
    return (
        identity == expected_identity
        and digest_bound_file(directory_descriptor, name, identity) == expected_sha256
    )


def open_identity_bound_file(
    directory_descriptor: int,
    name: str,
    expected_identity: FileIdentity,
) -> int:
    if entry_file_identity(directory_descriptor, name) != expected_identity:
        raise OSError(errno.ESTALE, os.strerror(errno.ESTALE), name)
    descriptor = open_regular_file(directory_descriptor, name)
    try:
        _require_stable(
            condition=_file_binding_matches(
                directory_descriptor, name, descriptor, expected_identity
            ),
            name=name,
        )
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _file_binding_matches(
    directory_descriptor: int,
    name: str,
    descriptor: int,
    expected_identity: FileIdentity,
) -> bool:
    return (
        file_identity(os.fstat(descriptor))
        == expected_identity
        == entry_file_identity(directory_descriptor, name)
    )


def descriptor_matches_entry(
    directory_descriptor: int,
    name: str,
    descriptor: int,
) -> bool:
    """Return whether an open descriptor remains the exact visible entry."""
    try:
        return entry_file_identity(directory_descriptor, name) == file_identity(
            os.fstat(descriptor)
        )
    except OSError:
        return False


def stage_locked_file(
    directory_descriptor: int,
    source_name: str,
    staging_name: str,
    locked_descriptor: int,
) -> tuple[int, FileIdentity]:
    """Rename one visible file to staging with restoration armed before reopening it."""
    staging_identity = file_identity(os.fstat(locked_descriptor))
    renamed = False
    try:
        rename_no_replace(directory_descriptor, source_name, staging_name)
        renamed = True
        locked_identity = file_identity(os.fstat(locked_descriptor))
        staging_identity = locked_identity
        visible_identity = entry_file_identity(directory_descriptor, staging_name)
        _require_stable(
            condition=visible_identity is not None,
            name=staging_name,
        )
        staging_identity = cast("FileIdentity", visible_identity)
        _require_stable(condition=staging_identity == locked_identity, name=staging_name)
        descriptor = open_identity_bound_file(
            directory_descriptor,
            staging_name,
            staging_identity,
        )
    except BaseException:
        if renamed:
            restore_staged_file(
                directory_descriptor,
                staging_name,
                source_name,
                staging_identity,
            )
        raise
    return descriptor, staging_identity


def restore_staged_file(
    directory_descriptor: int,
    staging_name: str,
    target_name: str,
    expected_identity: FileIdentity,
) -> None:
    """Restore only the exact staged inode when its canonical name is vacant."""
    staged_identity = entry_file_identity(directory_descriptor, staging_name)
    if staged_identity is None:
        return
    _require_stable(
        condition=staged_identity == expected_identity
        and entry_file_identity(directory_descriptor, target_name) is None,
        name=staging_name,
    )
    rename_no_replace(directory_descriptor, staging_name, target_name)
    os.fsync(directory_descriptor)


def _require_stable(*, condition: bool, name: str) -> None:
    if not condition:
        raise OSError(errno.ESTALE, os.strerror(errno.ESTALE), name)


def write_all(descriptor: int, content: bytes) -> None:
    """Write every byte to one already-open descriptor."""
    view = memoryview(content)
    while view:
        written = os.write(descriptor, view)
        view = view[written:]


def remove_owned_entry(
    directory_descriptor: int,
    name: str,
    expected: FileIdentity,
    *,
    sync: bool = True,
) -> None:
    """Quarantine, verify, and remove one exact entry without deleting a competitor."""
    fcntl.flock(directory_descriptor, fcntl.LOCK_EX)
    try:
        descriptor = open_identity_bound_file(directory_descriptor, name, expected)
        tombstone = f".{name}.{uuid.uuid4().hex}.delete"
        moved = False
        moved_identity = expected
        try:
            rename_no_replace(directory_descriptor, name, tombstone)
            moved = True
            moved_identity = file_identity(os.fstat(descriptor))
            visible_identity = entry_file_identity(directory_descriptor, tombstone)
            if visible_identity != moved_identity:
                if visible_identity is not None:
                    moved = False
                    restore_staged_file(
                        directory_descriptor,
                        tombstone,
                        name,
                        visible_identity,
                    )
                _require_stable(condition=False, name=tombstone)
            os.unlink(tombstone, dir_fd=directory_descriptor)
            moved = False
            if sync:
                os.fsync(directory_descriptor)
        except BaseException:
            if moved:
                restore_staged_file(directory_descriptor, tombstone, name, moved_identity)
            raise
        finally:
            os.close(descriptor)
    finally:
        fcntl.flock(directory_descriptor, fcntl.LOCK_UN)


def file_identity(metadata: os.stat_result) -> FileIdentity:
    """Return the exact regular-file identity and content-version fields."""
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def directory_identity(metadata: os.stat_result) -> DirectoryIdentity:
    """Return the stable binding identity for one directory descriptor."""
    return metadata.st_dev, metadata.st_ino, metadata.st_mode


def entry_file_identity(directory_descriptor: int, name: str) -> FileIdentity | None:
    """Return one no-follow entry identity relative to a held directory."""
    try:
        metadata = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return file_identity(metadata)


def entry_directory_identity(
    directory_descriptor: int,
    name: str,
) -> DirectoryIdentity | None:
    """Return one no-follow directory-entry identity relative to a held parent."""
    try:
        metadata = os.stat(name, dir_fd=directory_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return directory_identity(metadata)
