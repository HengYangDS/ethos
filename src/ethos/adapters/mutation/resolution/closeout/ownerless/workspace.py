"""Descriptor-bound observation for optional repository-root workspace files."""

from __future__ import annotations

import os
import stat
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Literal
from typing import NoReturn

import ethos.adapters.mutation.resolution.records.io.posix as posix
from ethos.adapters.mutation.resolution.observation import DescriptorIdentity
from ethos.adapters.mutation.resolution.observation import ExactFileSnapshot
from ethos.adapters.mutation.resolution.observation import OwnerlessGitObservationError

if TYPE_CHECKING:
    from pathlib import Path


def read_optional_root_bound_regular_file(
    root: Path, relative_path: str, *, maximum_bytes: int
) -> ExactFileSnapshot | None:
    """Read one optional regular file without a separate existence check."""
    parts = _relative_parts(relative_path)
    if type(maximum_bytes) is not int or maximum_bytes < 0:
        _fail("unverifiable", "root_bound_file")
    canonical_root, root_descriptor, root_identity = _pin_root(root)
    opened: list[tuple[int, str, int, DescriptorIdentity]] = []
    try:
        parent = _open_parent(
            canonical_root,
            root_descriptor,
            root_identity,
            opened,
            parts[:-1],
        )
        if parent is None:
            return None
        snapshot = _read_optional_file(
            canonical_root,
            root_descriptor,
            root_identity,
            opened,
            parent,
            parts[-1],
            maximum_bytes,
        )
        _require_bound_chain(canonical_root, root_descriptor, root_identity, opened)
    except OwnerlessGitObservationError:
        raise
    except (OSError, TypeError, ValueError) as error:
        _raise("unverifiable", "root_bound_file", error)
    else:
        return snapshot
    finally:
        for _parent, _name, descriptor, _identity_value in reversed(opened):
            os.close(descriptor)
        os.close(root_descriptor)


def _open_parent(
    root: Path,
    root_descriptor: int,
    root_identity: DescriptorIdentity,
    opened: list[tuple[int, str, int, DescriptorIdentity]],
    parts: tuple[str, ...],
) -> int | None:
    parent = root_descriptor
    for name in parts:
        if posix.entry_directory_identity(parent, name) is None:
            if _entry_absent(
                root,
                root_descriptor,
                root_identity,
                opened,
                parent,
                name,
                kind="directory",
            ):
                return None
            _fail("unverifiable", "root_bound_file")
        child = posix.open_directory_child(parent, name, create=False)
        identity = _identity(os.fstat(child))
        opened.append((parent, name, child, identity))
        parent = child
    return parent


def _read_optional_file(
    root: Path,
    root_descriptor: int,
    root_identity: DescriptorIdentity,
    opened: list[tuple[int, str, int, DescriptorIdentity]],
    parent: int,
    name: str,
    maximum_bytes: int,
) -> ExactFileSnapshot | None:
    identity = posix.entry_file_identity(parent, name)
    if identity is None:
        if _entry_absent(
            root,
            root_descriptor,
            root_identity,
            opened,
            parent,
            name,
            kind="file",
        ):
            return None
        _fail("unverifiable", "root_bound_file")
    if not stat.S_ISREG(identity[2]):
        _fail("unverifiable", "root_bound_file")
    raw = posix.read_bound_file(parent, name, identity, max_bytes=maximum_bytes)
    if raw is None:
        _fail("unverifiable", "root_bound_file")
    return ExactFileSnapshot(raw, DescriptorIdentity(*identity))


def _entry_absent(
    root: Path,
    root_descriptor: int,
    root_identity: DescriptorIdentity,
    opened: list[tuple[int, str, int, DescriptorIdentity]],
    parent: int,
    name: str,
    *,
    kind: Literal["directory", "file"],
) -> bool:
    _require_bound_chain(root, root_descriptor, root_identity, opened)
    current = (
        posix.entry_directory_identity(parent, name)
        if kind == "directory"
        else posix.entry_file_identity(parent, name)
    )
    _require_bound_chain(root, root_descriptor, root_identity, opened)
    return current is None


def _require_bound_chain(
    root: Path,
    root_descriptor: int,
    root_identity: DescriptorIdentity,
    opened: list[tuple[int, str, int, DescriptorIdentity]],
) -> None:
    for parent, name, descriptor, identity in opened:
        directory = (identity.device, identity.inode, identity.mode)
        if (
            _identity(os.fstat(descriptor)) != identity
            or posix.entry_directory_identity(parent, name) != directory
        ):
            _fail("unverifiable", "root_bound_file")
    root_directory = (root_identity.device, root_identity.inode, root_identity.mode)
    if _identity(
        os.fstat(root_descriptor)
    ) != root_identity or not posix.directory_descriptor_is_live(
        root, root_descriptor, root_directory
    ):
        _fail("unverifiable", "root_bound_file")


def _pin_root(root: Path) -> tuple[Path, int, DescriptorIdentity]:
    canonical = root.absolute()
    descriptor = -1
    try:
        descriptor = posix.open_directory_path(canonical, create=False)
        identity = _identity(os.fstat(descriptor))
        root_directory = (identity.device, identity.inode, identity.mode)
        if not posix.directory_descriptor_is_live(canonical, descriptor, root_directory):
            _fail("unverifiable", "root")
    except OwnerlessGitObservationError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except (OSError, TypeError, ValueError) as error:
        if descriptor >= 0:
            os.close(descriptor)
        _raise("unverifiable", "root", error)
    return canonical, descriptor, identity


def _relative_parts(relative: str) -> tuple[str, ...]:
    if type(relative) is not str:
        _fail("unverifiable", "path")
    path = PurePosixPath(relative)
    invalid = not relative or not path.parts or path.is_absolute() or path.as_posix() != relative
    if invalid or {".", ".."}.intersection(path.parts):
        _fail("unverifiable", "path")
    return path.parts


def _identity(metadata: os.stat_result) -> DescriptorIdentity:
    return DescriptorIdentity(*posix.file_identity(metadata))


def _raise(kind: str, detail: str, cause: BaseException) -> NoReturn:
    raise OwnerlessGitObservationError(kind, detail) from cause


def _fail(kind: str, detail: str) -> NoReturn:
    raise OwnerlessGitObservationError(kind, detail)
