"""Descriptor-bound snapshots for current lane-resolution records."""

from __future__ import annotations

import hashlib
import os
import stat
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.records.io.posix as posix

if TYPE_CHECKING:
    from pathlib import Path
    from types import TracebackType

_MAX_CURRENT_RECORD_BYTES = 16 * 1024 * 1024
_MAX_CURRENT_DIRECTORY_ENTRIES = 100_000
_RECORD_PATH_UNSAFE = "lane_resolution_record_path_unsafe"
_PRESERVATION_PACKAGE_NAMES = {
    "manifest.json",
    "repository.bundle",
    "tracked.patch",
    "index.patch",
    "untracked.tar",
}
CurrentFileIdentity = posix.FileIdentity


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
        root_identity: posix.DirectoryIdentity,
        entries: dict[str, posix.FileIdentity],
    ) -> None:
        self.root = root
        self._descriptor = descriptor
        self._root_identity = root_identity
        self._entries = entries
        self._directories: dict[str, tuple[int, dict[str, posix.FileIdentity]]] = {}

    @property
    def names(self) -> tuple[str, ...]:
        """Return the bounded root entry names captured by this snapshot."""
        self._require_root()
        return tuple(sorted(self._entries))

    def root_entry_identity(self, name: str) -> tuple[int, int, int] | None:
        """Return the device, inode, and mode captured for one root child."""
        self._require_root()
        identity = self._entries.get(name)
        if identity is None:
            return None
        return identity[:3]

    def file_identity(self, directory: str, name: str) -> CurrentFileIdentity | None:
        """Return the exact regular-file identity captured for one child."""
        opened = self._directories.get(directory)
        if opened is None:
            return None
        descriptor, entries = opened
        identity = entries.get(name)
        try:
            self._require_directory(directory, descriptor)
            current = _entry_identity(descriptor, name)
        except OSError:
            return None
        if identity is None or current != identity or not stat.S_ISREG(identity[2]):
            return None
        return identity

    def open_directory(self, name: str) -> tuple[tuple[str, ...], str]:
        """Open one direct child directory without following or rebinding its path."""
        if name in self._directories:
            descriptor, entries = self._directories[name]
            try:
                self._require_directory(name, descriptor)
            except OSError:
                return (), "invalid"
            return tuple(sorted(entries)), "valid"
        identity = self._entries.get(name)
        if identity is None:
            return (), "missing"
        if not stat.S_ISDIR(identity[2]):
            return (), "invalid"
        try:
            self._require_root()
            descriptor = posix.open_directory_child(self._descriptor, name, create=False)
        except OSError:
            return (), "invalid"
        entries: dict[str, posix.FileIdentity] | None = None
        try:
            if posix.file_identity(os.fstat(descriptor)) == identity:
                entries = _entries(descriptor)
                if entries is not None:
                    self._require_directory(name, descriptor)
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
        if identity is None or not stat.S_ISREG(identity[2]):
            return None
        try:
            self._require_directory(directory, descriptor)
            content = posix.read_bound_file(
                descriptor,
                name,
                identity,
                max_bytes=_MAX_CURRENT_RECORD_BYTES,
            )
            self._require_directory(directory, descriptor)
        except OSError:
            return None
        return content

    def digest_file(self, directory: str, name: str) -> str | None:
        """Hash one regular file through its held directory without a size cap."""
        opened = self._directories.get(directory)
        if opened is None:
            return None
        descriptor, entries = opened
        identity = entries.get(name)
        if identity is None or not stat.S_ISREG(identity[2]):
            return None
        try:
            self._require_directory(directory, descriptor)
            result = posix.digest_bound_file(descriptor, name, identity)
            self._require_directory(directory, descriptor)
        except OSError:
            return None
        return result

    def _require_root(self) -> None:
        if posix.directory_path_identity(self.root) != self._root_identity:
            raise OSError(_RECORD_PATH_UNSAFE)

    def _require_directory(self, name: str, descriptor: int) -> None:
        self._require_root()
        identity = self._entries.get(name)
        visible = posix.entry_directory_identity(self._descriptor, name)
        held = posix.directory_identity(os.fstat(descriptor))
        if identity is None or identity[:3] != held or visible != held:
            raise OSError(_RECORD_PATH_UNSAFE)

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
        descriptor = posix.open_directory_path(root, create=False)
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "invalid"
    owned = True
    try:
        root_identity = posix.directory_identity(os.fstat(descriptor))
        entries = _entries(descriptor)
        if entries is None or posix.directory_path_identity(root) != root_identity:
            return None, "invalid"
    except OSError:
        return None, "invalid"
    else:
        owned = False
        return CurrentRecordSnapshot(
            root=root,
            descriptor=descriptor,
            root_identity=root_identity,
            entries=entries,
        ), "valid"
    finally:
        if owned:
            os.close(descriptor)


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
        descriptor = posix.open_directory_path(root, create=False)
    except OSError:
        return "root_invalid"
    root_identity = posix.directory_identity(os.fstat(descriptor))
    state = "rename_failed"
    try:
        if not posix.directory_descriptor_is_live(root, descriptor, root_identity):
            state = "root_invalid"
        elif _entry_token_at(descriptor, source_name) != expected_identity:
            state = "identity_mismatch"
        elif _entry_token_at(descriptor, quarantine_name) is not None:
            state = "collision"
        else:
            try:
                posix.rename_no_replace(descriptor, source_name, quarantine_name)
            except FileExistsError:
                state = "collision"
            except OSError:
                pass
            else:
                if _entry_token_at(descriptor, quarantine_name) != expected_identity:
                    state = "identity_mismatch"
                else:
                    os.fsync(descriptor)
                    state = (
                        "moved"
                        if posix.directory_descriptor_is_live(root, descriptor, root_identity)
                        else "root_invalid"
                    )
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
        root_descriptor = posix.open_directory_path(root, create=False)
    except OSError:
        return False
    root_identity = posix.directory_identity(os.fstat(root_descriptor))
    package_descriptor: int | None = None
    removed = False
    try:
        package_descriptor = _open_quarantined_package(
            root_descriptor, quarantine_name, binding.identity
        )
        if package_descriptor is not None and posix.child_directory_is_live(
            root,
            root_descriptor,
            root_identity,
            package_descriptor,
            quarantine_name,
            binding.identity,
        ):
            names = _quarantined_package_names(package_descriptor, binding)
            if names is not None and _remove_bound_children(
                root,
                root_descriptor,
                root_identity,
                package_descriptor,
                quarantine_name,
                binding,
                names,
            ):
                removed = _remove_quarantine_directory(
                    root,
                    root_descriptor,
                    root_identity,
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
    descriptor = posix.open_directory_child(root_descriptor, quarantine_name, create=False)
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


def _remove_bound_children(  # noqa: PLR0913, RUF100 - exact quarantine binding
    root: Path,
    root_descriptor: int,
    root_identity: posix.DirectoryIdentity,
    descriptor: int,
    quarantine_name: str,
    binding: QuarantinedPackageBinding,
    names: tuple[str, ...],
) -> bool:
    deletion_order = sorted(names, key=lambda name: name == "manifest.json")
    return all(
        _remove_bound_child(
            root,
            root_descriptor,
            root_identity,
            descriptor,
            quarantine_name,
            binding.identity,
            name,
            binding.file_identities[name],
            binding.sha256[name],
        )
        for name in deletion_order
    )


def _remove_bound_child(  # noqa: PLR0913, RUF100 - exact payload binding
    root: Path,
    root_descriptor: int,
    root_identity: posix.DirectoryIdentity,
    descriptor: int,
    quarantine_name: str,
    quarantine_identity: tuple[int, int, int],
    name: str,
    identity: CurrentFileIdentity,
    expected_sha256: str,
) -> bool:
    if not posix.child_directory_is_live(
        root,
        root_descriptor,
        root_identity,
        descriptor,
        quarantine_name,
        quarantine_identity,
    ):
        return False
    staging_name = _staging_name(name, identity)
    source_descriptor: int | None = None
    if _entry_identity_at(descriptor, staging_name) is None:
        with suppress(OSError):
            source_descriptor = posix.open_identity_bound_file(descriptor, name, identity)
    if source_descriptor is None:
        return False
    try:
        posix.rename_no_replace(descriptor, name, staging_name)
    except OSError:
        os.close(source_descriptor)
        return False
    deleted = False
    recovery_identity = identity
    try:
        staging_identity = posix.file_identity(os.fstat(source_descriptor))
        _require_safe(condition=staging_identity is not None)
        exact_identity = staging_identity
        recovery_identity = exact_identity
        if posix.entry_file_identity(descriptor, staging_name) != exact_identity:
            _restore_staged_entry(descriptor, staging_name, name, identity)
            return False
        _require_safe(
            condition=posix.child_directory_is_live(
                root,
                root_descriptor,
                root_identity,
                descriptor,
                quarantine_name,
                quarantine_identity,
            )
        )
        os.fsync(descriptor)
        if not _file_matches(descriptor, staging_name, exact_identity, expected_sha256):
            _restore_staged_entry(descriptor, staging_name, name, identity)
            return False
        posix.remove_owned_entry(descriptor, staging_name, exact_identity)
        deleted = True
        _require_safe(
            condition=posix.child_directory_is_live(
                root,
                root_descriptor,
                root_identity,
                descriptor,
                quarantine_name,
                quarantine_identity,
            )
        )
    except BaseException:
        if not deleted:
            _restore_staged_entry(descriptor, staging_name, name, recovery_identity)
        raise
    finally:
        os.close(source_descriptor)
    return True


def _require_safe(*, condition: bool) -> None:
    if not condition:
        raise OSError(_RECORD_PATH_UNSAFE)


def _remove_quarantine_directory(  # noqa: PLR0913, RUF100 - exact directory binding
    root: Path,
    root_descriptor: int,
    root_identity: posix.DirectoryIdentity,
    package_descriptor: int,
    quarantine_name: str,
    expected_identity: tuple[int, int, int],
) -> bool:
    os.fsync(package_descriptor)
    if not posix.child_directory_is_live(
        root,
        root_descriptor,
        root_identity,
        package_descriptor,
        quarantine_name,
        expected_identity,
    ):
        return False
    os.rmdir(quarantine_name, dir_fd=root_descriptor)
    os.fsync(root_descriptor)
    return (
        posix.directory_descriptor_is_live(root, root_descriptor, root_identity)
        and _entry_token_at(root_descriptor, quarantine_name) is None
    )


def _entries(descriptor: int) -> dict[str, posix.FileIdentity] | None:
    entries: dict[str, posix.FileIdentity] = {}
    with os.scandir(descriptor) as iterator:
        for index, entry in enumerate(iterator):
            if index >= _MAX_CURRENT_DIRECTORY_ENTRIES:
                return None
            entries[entry.name] = posix.file_identity(entry.stat(follow_symlinks=False))
    return entries


def _entry_identity(descriptor: int, name: str) -> posix.FileIdentity | None:
    return posix.entry_file_identity(descriptor, name)


def _identity_token(metadata: os.stat_result) -> tuple[int, int, int]:
    return metadata.st_dev, metadata.st_ino, metadata.st_mode


def _entry_token_at(descriptor: int, name: str) -> tuple[int, int, int] | None:
    try:
        return _identity_token(os.stat(name, dir_fd=descriptor, follow_symlinks=False))
    except FileNotFoundError:
        return None


def _entry_identity_at(descriptor: int, name: str) -> CurrentFileIdentity | None:
    return posix.entry_file_identity(descriptor, name)


def _file_matches(
    descriptor: int,
    name: str,
    expected_identity: CurrentFileIdentity | None,
    expected_sha256: str | None,
) -> bool:
    return bool(
        expected_identity is not None
        and expected_sha256 is not None
        and posix.digest_matches_identity(descriptor, name, expected_identity, expected_sha256)
    )


def _staging_name(name: str, identity: CurrentFileIdentity) -> str:
    binding = hashlib.sha256(f"{name}\0{identity!r}".encode()).hexdigest()
    return f".{binding}.{name}.clear-delete"


def _restore_staged_entry(
    descriptor: int,
    staging_name: str,
    name: str,
    expected_identity: CurrentFileIdentity,
) -> None:
    staged_identity = posix.entry_file_identity(descriptor, staging_name)
    if staged_identity is None:
        return
    if staged_identity[:5] != expected_identity[:5]:
        if _entry_identity_at(descriptor, name) is None:
            posix.rename_no_replace(descriptor, staging_name, name)
            os.fsync(descriptor)
        raise OSError(_RECORD_PATH_UNSAFE)
    if _entry_identity_at(descriptor, name) is not None:
        posix.remove_owned_entry(descriptor, staging_name, staged_identity)
    else:
        posix.rename_no_replace(descriptor, staging_name, name)
    os.fsync(descriptor)
