"""Byte-exact Git and descriptor-bound untracked preservation."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import run_git

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import BinaryIO

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_READ_SIZE = 1024 * 1024
_SPOOL_MEMORY_LIMIT = 1024 * 1024
_MEMBER_CHANGED = "lane_resolution_untracked_member_changed"
_MEMBER_UNSUPPORTED = "lane_resolution_untracked_member_unsupported"
_MEMBER_UNVERIFIABLE = "lane_resolution_untracked_member_unverifiable"
_PATH_INVALID = "lane_resolution_untracked_path_invalid"
_BUNDLE_FAILED = "lane_resolution_bundle_failed"
_TRACKED_DIFF_FAILED = "lane_resolution_diff_failed"
_INDEX_DIFF_FAILED = "lane_resolution_index_diff_failed"
_DIFF_FLAGS = ("--no-ext-diff", "--no-textconv", "--binary")

type _Identity = tuple[int, int, int, int, int, int]
type _DirectoryBinding = tuple[int, str, int, _Identity]


def write_git_preservation_payloads(
    *,
    source: Path,
    bundle: Path,
    tracked_patch: Path,
    index_patch: Path,
    lane_ref: str,
) -> None:
    """Write one bundle plus byte-exact worktree and index patches with fixed Git."""
    bundled = run_git(
        source,
        "bundle",
        "create",
        bundle.as_posix(),
        lane_ref,
        check=False,
    )
    if bundled.returncode:
        raise ValueError(bundled.stderr.strip() or _BUNDLE_FAILED)
    tracked = run_git_bytes(source, "diff", *_DIFF_FLAGS, "HEAD", "--")
    if tracked.returncode:
        raise ValueError(_byte_diagnostic(tracked.stderr, _TRACKED_DIFF_FAILED))
    tracked_patch.write_bytes(tracked.stdout)
    index = run_git_bytes(source, "diff", "--cached", *_DIFF_FLAGS, "HEAD", "--")
    if index.returncode:
        raise ValueError(_byte_diagnostic(index.stderr, _INDEX_DIFF_FAILED))
    index_patch.write_bytes(index.stdout)


def write_untracked_archive(*, source: Path, archive: Path, inventory: list[bytes]) -> None:
    """Write exact inventoried members without following path components."""
    try:
        with (
            _bound_source(source) as (root_descriptor, root_identity),
            tarfile.open(archive, "w", dereference=False) as stream,
        ):
            for raw_name in inventory:
                relative = _relative_member(raw_name)
                with _capture_member(
                    source=source,
                    root_descriptor=root_descriptor,
                    root_identity=root_identity,
                    relative=relative,
                ) as (info, payload):
                    stream.addfile(info, payload)
    except (OSError, tarfile.TarError) as error:
        raise ValueError(_MEMBER_UNVERIFIABLE) from error


def digest_untracked_inventory(*, source: Path, inventory: bytes) -> str:
    """Digest exact inventory plus descriptor-bound regular and symlink member bytes."""
    members = _inventory_members(inventory)
    if not members:
        return hashlib.sha256(b"").hexdigest()
    digest = hashlib.sha256(inventory)
    with _bound_source(source) as (root_descriptor, root_identity):
        for raw_name in members:
            with _capture_member(
                source=source,
                root_descriptor=root_descriptor,
                root_identity=root_identity,
                relative=_relative_member(raw_name),
            ) as (info, payload):
                digest.update(info.type)
                if payload is None:
                    target = os.fsencode(info.linkname)
                    digest.update(len(target).to_bytes(8, "big") + target)
                else:
                    digest.update(info.size.to_bytes(8, "big"))
                    while chunk := payload.read(_READ_SIZE):
                        digest.update(chunk)
    return digest.hexdigest()


def run_git_bytes(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Run fixed-literal Git while retaining raw stdout and stderr bytes."""
    environment = {"PATH": os.environ.get("PATH", os.defpath), "GIT_NO_REPLACE_OBJECTS": "1"}
    environment |= {"LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1"}
    environment |= {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_ATTR_NOSYSTEM": "1"}
    return subprocess.run(
        ["git", *args],  # noqa: S607, RUF100 - fixed Git preservation boundary
        cwd=root,
        check=False,
        capture_output=True,
        env=environment,
        shell=False,
    )


def _byte_diagnostic(stderr: bytes, fallback: str) -> str:
    return stderr.decode(errors="replace").strip() or fallback


def _relative_member(raw_name: bytes) -> Path:
    relative = Path(raw_name.decode(errors="surrogateescape"))
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(_PATH_INVALID)
    return relative


def _inventory_members(inventory: bytes) -> tuple[bytes, ...]:
    if type(inventory) is not bytes:
        raise ValueError(_PATH_INVALID)
    if not inventory:
        return ()
    members = tuple(inventory[:-1].split(b"\0")) if inventory.endswith(b"\0") else ()
    if not members or any(not member for member in members):
        raise ValueError(_PATH_INVALID)
    return members


@contextmanager
def _bound_source(source: Path) -> Iterator[tuple[int, _Identity]]:
    descriptor = -1
    try:
        visible = source.stat(follow_symlinks=False)
        if not stat.S_ISDIR(visible.st_mode):
            raise ValueError(_MEMBER_UNSUPPORTED)
        descriptor = os.open(source, _DIRECTORY_FLAGS)
        identity = _identity(os.fstat(descriptor))
        if _identity(visible) != identity:
            raise ValueError(_MEMBER_CHANGED)
        yield descriptor, identity
        _verify_root(source, descriptor, identity)
    except OSError as error:
        raise ValueError(_MEMBER_UNVERIFIABLE) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


@contextmanager
def _capture_member(
    *,
    source: Path,
    root_descriptor: int,
    root_identity: _Identity,
    relative: Path,
) -> Iterator[tuple[tarfile.TarInfo, BinaryIO | None]]:
    opened_directories: list[int] = []
    bindings: list[_DirectoryBinding] = []
    parent_descriptor = root_descriptor
    try:
        for component in relative.parts[:-1]:
            visible = os.stat(component, dir_fd=parent_descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(visible.st_mode):
                raise ValueError(_MEMBER_UNSUPPORTED)
            descriptor = os.open(component, _DIRECTORY_FLAGS, dir_fd=parent_descriptor)
            pinned_identity = _identity(os.fstat(descriptor))
            if _identity(visible) != pinned_identity:
                os.close(descriptor)
                raise ValueError(_MEMBER_CHANGED)
            bindings.append((parent_descriptor, component, descriptor, pinned_identity))
            opened_directories.append(descriptor)
            parent_descriptor = descriptor
        with _capture_final(
            parent_descriptor=parent_descriptor,
            name=relative.parts[-1],
            archive_name=relative.as_posix(),
        ) as captured:
            _verify_directory_bindings(bindings)
            _verify_root(source, root_descriptor, root_identity)
            yield captured
    except OSError as error:
        raise ValueError(_MEMBER_UNVERIFIABLE) from error
    finally:
        for descriptor in reversed(opened_directories):
            os.close(descriptor)


@contextmanager
def _capture_final(
    *, parent_descriptor: int, name: str, archive_name: str
) -> Iterator[tuple[tarfile.TarInfo, BinaryIO | None]]:
    visible = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if stat.S_ISREG(visible.st_mode):
        with _capture_regular(
            parent_descriptor=parent_descriptor,
            name=name,
            archive_name=archive_name,
            visible=visible,
        ) as captured:
            yield captured
        return
    if stat.S_ISLNK(visible.st_mode):
        yield _capture_symlink(
            parent_descriptor=parent_descriptor,
            name=name,
            archive_name=archive_name,
            visible=visible,
        )
        return
    raise ValueError(_MEMBER_UNSUPPORTED)


@contextmanager
def _capture_regular(
    *,
    parent_descriptor: int,
    name: str,
    archive_name: str,
    visible: os.stat_result,
) -> Iterator[tuple[tarfile.TarInfo, BinaryIO]]:
    descriptor = -1
    try:
        descriptor = os.open(name, _FILE_FLAGS, dir_fd=parent_descriptor)
        pinned = os.fstat(descriptor)
        if _identity(visible) != _identity(pinned):
            raise ValueError(_MEMBER_CHANGED)
        with tempfile.SpooledTemporaryFile(max_size=_SPOOL_MEMORY_LIMIT, mode="w+b") as payload:
            byte_count = 0
            while byte_count < pinned.st_size:
                read_size = min(_READ_SIZE, pinned.st_size - byte_count)
                chunk = os.read(descriptor, read_size)
                if not chunk:
                    break
                payload.write(chunk)
                byte_count += len(chunk)
            after = os.fstat(descriptor)
            final_visible = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            if (
                _identity(pinned) != _identity(after)
                or _identity(pinned) != _identity(final_visible)
                or byte_count != pinned.st_size
            ):
                raise ValueError(_MEMBER_CHANGED)
            info = _tar_info(archive_name, pinned)
            info.type = tarfile.REGTYPE
            info.size = byte_count
            payload.seek(0)
            yield info, cast("BinaryIO", payload)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _capture_symlink(
    *,
    parent_descriptor: int,
    name: str,
    archive_name: str,
    visible: os.stat_result,
) -> tuple[tarfile.TarInfo, None]:
    linkname = os.readlink(name, dir_fd=parent_descriptor)
    final_visible = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if _identity(visible) != _identity(final_visible):
        raise ValueError(_MEMBER_CHANGED)
    info = _tar_info(archive_name, visible)
    info.type = tarfile.SYMTYPE
    info.linkname = linkname
    info.size = 0
    return info, None


def _verify_directory_bindings(bindings: list[_DirectoryBinding]) -> None:
    for parent_descriptor, name, descriptor, expected in bindings:
        visible = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        pinned = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(visible.st_mode)
            or _identity(visible) != expected
            or _identity(pinned) != expected
        ):
            raise ValueError(_MEMBER_CHANGED)


def _verify_root(source: Path, descriptor: int, expected: _Identity) -> None:
    visible = source.stat(follow_symlinks=False)
    pinned = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(visible.st_mode)
        or _identity(visible) != expected
        or _identity(pinned) != expected
    ):
        raise ValueError(_MEMBER_CHANGED)


def _tar_info(name: str, metadata: os.stat_result) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.mode = stat.S_IMODE(metadata.st_mode)
    info.uid = metadata.st_uid
    info.gid = metadata.st_gid
    info.mtime = metadata.st_mtime
    return info


def _identity(metadata: os.stat_result) -> _Identity:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )
