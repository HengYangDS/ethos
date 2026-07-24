"""POSIX descriptor, identity, and no-replace filesystem primitives."""

from __future__ import annotations

import ctypes
import errno
import os
import stat
from contextlib import suppress

FileIdentity = tuple[int, int, int, int, int, int]
DirectoryIdentity = tuple[int, int, int]


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
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    return os.open(name, flags, 0o600, dir_fd=directory_descriptor)


def open_regular_file(directory_descriptor: int, name: str) -> int:
    """Open one no-follow regular file relative to a held directory."""
    descriptor = os.open(name, file_flags(), dir_fd=directory_descriptor)
    if stat.S_ISREG(os.fstat(descriptor).st_mode):
        return descriptor
    os.close(descriptor)
    raise OSError(errno.EINVAL, os.strerror(errno.EINVAL), name)


def write_all(descriptor: int, content: bytes) -> None:
    """Write every byte to one already-open descriptor."""
    view = memoryview(content)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError(errno.EIO, os.strerror(errno.EIO))
        view = view[written:]


def unlink_if_present(directory_descriptor: int, name: str) -> None:
    """Unlink one descriptor-relative entry when it still exists."""
    with suppress(FileNotFoundError):
        os.unlink(name, dir_fd=directory_descriptor)


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


def same_content_identity(left: FileIdentity | None, right: FileIdentity) -> bool:
    """Return whether two identities describe the same inode content version."""
    return left is not None and left[:5] == right[:5]
