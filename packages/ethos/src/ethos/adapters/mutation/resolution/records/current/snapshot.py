"""Descriptor-bound snapshots for current lane-resolution records."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import os
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

_MAX_CURRENT_RECORD_BYTES = 16 * 1024 * 1024
_MAX_CURRENT_DIRECTORY_ENTRIES = 100_000
_PRESERVATION_PACKAGE_NAMES = {
    "manifest.json",
    "repository.bundle",
    "tracked.patch",
    "index.patch",
    "untracked.tar",
}
CurrentFileIdentity = tuple[int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class _EntryIdentity:
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True, slots=True)
class QuarantinedPackageBinding:
    """Exact child names, digests, and identities approved for deletion."""

    identity: tuple[int, int, int]
    names: set[str]
    sha256: dict[str, str]
    file_identities: dict[str, CurrentFileIdentity]


class CurrentRecordSnapshot:
    """Hold the current root and opened child directories by verified descriptors."""

    def __init__(
        self,
        *,
        root: Path,
        descriptor: int,
        entries: dict[str, _EntryIdentity],
    ) -> None:
        self.root = root
        self._descriptor = descriptor
        self._entries = entries
        self._directories: dict[str, tuple[int, dict[str, _EntryIdentity]]] = {}

    @property
    def names(self) -> tuple[str, ...]:
        """Return the bounded root entry names captured by this snapshot."""
        return tuple(sorted(self._entries))

    def root_entry_identity(self, name: str) -> tuple[int, int, int] | None:
        """Return the device, inode, and mode captured for one root child."""
        identity = self._entries.get(name)
        if identity is None:
            return None
        return identity.device, identity.inode, identity.mode

    def file_identity(self, directory: str, name: str) -> CurrentFileIdentity | None:
        """Return the exact regular-file identity captured for one child."""
        opened = self._directories.get(directory)
        if opened is None:
            return None
        identity = opened[1].get(name)
        if identity is None or not stat.S_ISREG(identity.mode):
            return None
        return _identity_value(identity)

    def open_directory(self, name: str) -> tuple[tuple[str, ...], str]:
        """Open one direct child directory without following or rebinding its path."""
        if name in self._directories:
            return tuple(sorted(self._directories[name][1])), "valid"
        identity = self._entries.get(name)
        if identity is None:
            return (), "missing"
        if not stat.S_ISDIR(identity.mode):
            return (), "invalid"
        try:
            descriptor = os.open(name, _directory_flags(), dir_fd=self._descriptor)
        except OSError:
            return (), "invalid"
        entries: dict[str, _EntryIdentity] | None = None
        try:
            if _identity(os.fstat(descriptor)) == identity:
                entries = _entries(descriptor)
                if entries is not None:
                    self._directories[name] = (descriptor, entries)
        except OSError:
            entries = None
        finally:
            if name not in self._directories:
                os.close(descriptor)
        return (tuple(sorted(entries)), "valid") if entries is not None else ((), "invalid")

    def read_file(self, directory: str, name: str) -> bytes | None:
        """Read one file relative to its held directory and original identity."""
        opened = self._directories.get(directory)
        if opened is None:
            return None
        descriptor, entries = opened
        identity = entries.get(name)
        if identity is None or not stat.S_ISREG(identity.mode):
            return None
        try:
            file_descriptor = os.open(name, _file_flags(), dir_fd=descriptor)
        except OSError:
            return None
        content: bytes | None = None
        try:
            if _identity(os.fstat(file_descriptor)) == identity:
                candidate = _read_bounded(file_descriptor)
                if candidate is not None and _identity(os.fstat(file_descriptor)) == identity:
                    content = candidate
        except OSError:
            content = None
        finally:
            os.close(file_descriptor)
        return content

    def digest_file(self, directory: str, name: str) -> str | None:
        """Hash one regular file through its held directory without a size cap."""
        opened = self._directories.get(directory)
        if opened is None:
            return None
        descriptor, entries = opened
        identity = entries.get(name)
        if identity is None or not stat.S_ISREG(identity.mode):
            return None
        try:
            file_descriptor = os.open(name, _file_flags(), dir_fd=descriptor)
        except OSError:
            return None
        result: str | None = None
        try:
            if _identity(os.fstat(file_descriptor)) == identity:
                digest = hashlib.sha256()
                while chunk := os.read(file_descriptor, 1024 * 1024):
                    digest.update(chunk)
                if _identity(os.fstat(file_descriptor)) == identity:
                    result = digest.hexdigest()
        except OSError:
            pass
        finally:
            os.close(file_descriptor)
        return result

    def close(self) -> None:
        """Close every descriptor retained by the snapshot."""
        for descriptor, _entries_by_name in self._directories.values():
            os.close(descriptor)
        self._directories.clear()
        os.close(self._descriptor)

    def __enter__(self) -> CurrentRecordSnapshot:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def open_current_record_snapshot(
    root: Path,
) -> tuple[CurrentRecordSnapshot | None, str]:
    """Open one bounded no-follow snapshot of the current record root."""
    try:
        descriptor = os.open(root, _directory_flags())
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "invalid"
    try:
        entries = _entries(descriptor)
        if entries is None:
            return None, "invalid"
    except OSError:
        return None, "invalid"
    finally:
        if "entries" not in locals() or entries is None:
            os.close(descriptor)
    return CurrentRecordSnapshot(root=root, descriptor=descriptor, entries=entries), "valid"


def read_current_record_path(root: Path, path: Path) -> tuple[bytes | None, str]:
    """Read one direct decision path through a descriptor-bound current snapshot."""
    if path.absolute().parent != (root / "decisions").absolute() or path.suffix != ".json":
        return None, "invalid"
    snapshot, state = open_current_record_snapshot(root)
    if snapshot is None:
        return None, state
    with snapshot:
        names, category_state = snapshot.open_directory("decisions")
        if category_state != "valid" or path.name not in names:
            return None, "missing" if category_state == "missing" else "invalid"
        content = snapshot.read_file("decisions", path.name)
        return (content, "valid") if content is not None else (None, "invalid")


def move_current_package_to_quarantine(
    *,
    root: Path,
    source_name: str,
    quarantine_name: str,
    expected_identity: tuple[int, int, int],
) -> str:
    """Atomically move the exact reviewed package without replacing a quarantine."""
    try:
        descriptor = os.open(root, _directory_flags())
    except OSError:
        return "root_invalid"
    state = "rename_failed"
    try:
        if _entry_token_at(descriptor, source_name) != expected_identity:
            state = "identity_mismatch"
        elif _entry_token_at(descriptor, quarantine_name) is not None:
            state = "collision"
        else:
            try:
                _rename_no_replace_at(descriptor, source_name, quarantine_name)
            except FileExistsError:
                state = "collision"
            except OSError:
                pass
            else:
                if _entry_token_at(descriptor, quarantine_name) != expected_identity:
                    state = "identity_mismatch"
                else:
                    os.fsync(descriptor)
                    state = "moved"
    finally:
        os.close(descriptor)
    return state


def remove_quarantined_package(
    *,
    root: Path,
    quarantine_name: str,
    binding: QuarantinedPackageBinding,
) -> bool:
    """Delete only the exact quarantined package captured by the current snapshot."""
    try:
        root_descriptor = os.open(root, _directory_flags())
    except OSError:
        return False
    package_descriptor: int | None = None
    removed = False
    try:
        package_descriptor = _open_quarantined_package(
            root_descriptor, quarantine_name, binding.identity
        )
        if package_descriptor is not None:
            names = _quarantined_package_names(package_descriptor, binding)
            if names is not None and _remove_bound_children(package_descriptor, binding, names):
                removed = _remove_quarantine_directory(
                    root_descriptor,
                    package_descriptor,
                    quarantine_name,
                    binding.identity,
                )
    except OSError:
        removed = False
    finally:
        if package_descriptor is not None:
            os.close(package_descriptor)
        os.close(root_descriptor)
    return removed


def _open_quarantined_package(
    root_descriptor: int,
    quarantine_name: str,
    expected_identity: tuple[int, int, int],
) -> int | None:
    if _entry_token_at(root_descriptor, quarantine_name) != expected_identity:
        return None
    descriptor = os.open(quarantine_name, _directory_flags(), dir_fd=root_descriptor)
    try:
        if _identity_token(os.fstat(descriptor)) == expected_identity:
            return descriptor
    except BaseException:
        os.close(descriptor)
        raise
    os.close(descriptor)
    return None


def _quarantined_package_names(
    descriptor: int, binding: QuarantinedPackageBinding
) -> tuple[str, ...] | None:
    names = tuple(os.listdir(descriptor))
    valid = (
        len(names) <= _MAX_CURRENT_DIRECTORY_ENTRIES
        and set(names) == binding.names
        and binding.names <= _PRESERVATION_PACKAGE_NAMES
        and all(
            _file_matches(
                descriptor,
                name,
                binding.file_identities.get(name),
                binding.sha256.get(name),
            )
            for name in names
        )
    )
    return names if valid else None


def _remove_bound_children(
    descriptor: int,
    binding: QuarantinedPackageBinding,
    names: tuple[str, ...],
) -> bool:
    deletion_order = sorted(names, key=lambda name: name == "manifest.json")
    return all(
        _remove_bound_child(
            descriptor,
            name,
            binding.file_identities[name],
            binding.sha256[name],
        )
        for name in deletion_order
    )


def _remove_bound_child(
    descriptor: int,
    name: str,
    identity: CurrentFileIdentity,
    expected_sha256: str,
) -> bool:
    staging_name = _staging_name(name, identity)
    if _entry_identity_at(descriptor, staging_name) is not None:
        return False
    try:
        _rename_no_replace_at(descriptor, name, staging_name)
    except OSError:
        return False
    os.fsync(descriptor)
    if not _file_matches(descriptor, staging_name, identity, expected_sha256):
        _restore_staged_entry(descriptor, staging_name, name)
        return False
    try:
        os.unlink(staging_name, dir_fd=descriptor)
    except BaseException:
        _restore_staged_entry(descriptor, staging_name, name)
        raise
    os.fsync(descriptor)
    return True


def _remove_quarantine_directory(
    root_descriptor: int,
    package_descriptor: int,
    quarantine_name: str,
    expected_identity: tuple[int, int, int],
) -> bool:
    os.fsync(package_descriptor)
    if _entry_token_at(root_descriptor, quarantine_name) != expected_identity:
        return False
    os.rmdir(quarantine_name, dir_fd=root_descriptor)
    os.fsync(root_descriptor)
    return _entry_token_at(root_descriptor, quarantine_name) is None


def _entries(descriptor: int) -> dict[str, _EntryIdentity] | None:
    entries: dict[str, _EntryIdentity] = {}
    with os.scandir(descriptor) as iterator:
        for index, entry in enumerate(iterator):
            if index >= _MAX_CURRENT_DIRECTORY_ENTRIES:
                return None
            entries[entry.name] = _identity(entry.stat(follow_symlinks=False))
    return entries


def _identity(metadata: os.stat_result) -> _EntryIdentity:
    return _EntryIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        size=metadata.st_size,
        modified_ns=metadata.st_mtime_ns,
        changed_ns=metadata.st_ctime_ns,
    )


def _identity_value(identity: _EntryIdentity) -> CurrentFileIdentity:
    return (
        identity.device,
        identity.inode,
        identity.mode,
        identity.size,
        identity.modified_ns,
    )


def _identity_token(metadata: os.stat_result) -> tuple[int, int, int]:
    return metadata.st_dev, metadata.st_ino, metadata.st_mode


def _entry_token_at(descriptor: int, name: str) -> tuple[int, int, int] | None:
    try:
        return _identity_token(os.stat(name, dir_fd=descriptor, follow_symlinks=False))
    except FileNotFoundError:
        return None


def _entry_identity_at(descriptor: int, name: str) -> CurrentFileIdentity | None:
    try:
        identity = _identity(os.stat(name, dir_fd=descriptor, follow_symlinks=False))
    except FileNotFoundError:
        return None
    return _identity_value(identity)


def _file_matches(
    descriptor: int,
    name: str,
    expected_identity: CurrentFileIdentity | None,
    expected_sha256: str | None,
) -> bool:
    if expected_identity is None or expected_sha256 is None:
        return False
    try:
        file_descriptor = os.open(name, _file_flags(), dir_fd=descriptor)
    except OSError:
        return False
    try:
        if _identity_value(_identity(os.fstat(file_descriptor))) != expected_identity:
            return False
        digest = hashlib.sha256()
        while chunk := os.read(file_descriptor, 1024 * 1024):
            digest.update(chunk)
        return (
            _identity_value(_identity(os.fstat(file_descriptor))) == expected_identity
            and digest.hexdigest() == expected_sha256
        )
    except OSError:
        return False
    finally:
        os.close(file_descriptor)


def _staging_name(name: str, identity: CurrentFileIdentity) -> str:
    binding = hashlib.sha256(f"{name}\0{identity!r}".encode()).hexdigest()
    return f".{binding}.{name}.clear-delete"


def _restore_staged_entry(descriptor: int, staging_name: str, name: str) -> None:
    if _entry_identity_at(descriptor, staging_name) is None:
        return
    if _entry_identity_at(descriptor, name) is not None:
        return
    try:
        _rename_no_replace_at(descriptor, staging_name, name)
        os.fsync(descriptor)
    except OSError:
        pass


def _rename_no_replace_at(descriptor: int, source: str, target: str) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    source_bytes, target_bytes = os.fsencode(source), os.fsencode(target)
    if hasattr(library, "renameatx_np"):
        result = library.renameatx_np(descriptor, source_bytes, descriptor, target_bytes, 4)
    elif hasattr(library, "renameat2"):
        result = library.renameat2(descriptor, source_bytes, descriptor, target_bytes, 1)
    else:
        raise OSError(errno.ENOTSUP, os.strerror(errno.ENOTSUP), target)
    if result == 0:
        return
    error = ctypes.get_errno()
    exception = FileExistsError if error == errno.EEXIST else OSError
    raise exception(error, os.strerror(error), target)


def _read_bounded(descriptor: int) -> bytes | None:
    metadata = os.fstat(descriptor)
    if metadata.st_size > _MAX_CURRENT_RECORD_BYTES:
        return None
    remaining = _MAX_CURRENT_RECORD_BYTES + 1
    chunks: list[bytes] = []
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    content = b"".join(chunks)
    return content if len(content) <= _MAX_CURRENT_RECORD_BYTES else None


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )


def _file_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
