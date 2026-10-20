"""Read bounded regular content through one stable no-follow descriptor chain."""

from __future__ import annotations

import os
import stat
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.repository.registry.docs.registry import DocumentOrigins
from ethos.repository.registry.docs.registry import docs_root
from ethos.repository.registry.docs.registry import retained_document_origins

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from ethos.repository.registry.docs.registry import RetainedDocument

# Whether this host offers the no-follow descriptor chain that read_regular_bytes prefers.
DESCRIPTOR_CHAIN_READS = (
    all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"))
    and os.open in os.supports_dir_fd
)


@dataclass(frozen=True, slots=True)
class _ReadSnapshot:
    root: Path
    directories: tuple[int, ...]
    components: tuple[str, ...]
    before: os.stat_result
    after: os.stat_result
    content_length: int


def read_regular_bytes(
    root: Path,
    relative: str,
    *,
    unsafe_gap: str,
    unstable_gap: str,
    size_gap: str,
    max_bytes: int = 64 * 1024 * 1024,
    expected_mode: int | None = None,
) -> bytes:
    """Observe one stable regular input, refusing unsupported native guarantees.

    The caller cap and first descriptor size are checked before allocation.
    Growth never expands that bound. This observes content
    and directory identity, not authorization or a persistent filesystem snapshot.
    Native aliases above the selected root resolve once; its canonical descriptor
    chain and repository-relative components are opened without following links.
    A host without that chain binds the same member identity through plain paths.
    """
    if not DESCRIPTOR_CHAIN_READS:
        return _portable_regular_bytes(
            root,
            relative,
            gaps=(unsafe_gap, unstable_gap, size_gap),
            max_bytes=max_bytes,
            expected_mode=expected_mode,
        )
    nonblock = getattr(os, "O_NONBLOCK", 0)
    if not nonblock:
        raise ValueError(unsafe_gap)
    file_descriptor: int | None = None
    try:
        with _parent_descriptors(root, relative, unsafe_gap) as (
            canonical,
            components,
            directories,
        ):
            file_descriptor = os.open(
                components[-1], os.O_RDONLY | os.O_NOFOLLOW | nonblock, dir_fd=directories[-1]
            )
            before = os.fstat(file_descriptor)
            if not stat.S_ISREG(before.st_mode) or (
                expected_mode is not None and stat.S_IMODE(before.st_mode) != expected_mode
            ):
                raise ValueError(unsafe_gap)
            limit = min(before.st_size, max_bytes)
            if before.st_size > max_bytes:
                raise ValueError(size_gap)
            with os.fdopen(file_descriptor, "rb", closefd=True) as source:
                file_descriptor = None
                content = source.read(limit + 1)
                after = os.fstat(source.fileno())
            if len(content) > limit:
                raise ValueError(size_gap)
            _validate_snapshot(
                _ReadSnapshot(root, tuple(directories), components, before, after, len(content)),
                unstable_gap,
                canonical,
            )
    except (OSError, NotImplementedError) as error:
        raise ValueError(unsafe_gap) from error
    else:
        return content
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)


def read_link_target(root: Path, relative: str, *, unsafe_gap: str, unstable_gap: str) -> str:
    """Read a stable alias through the same no-follow parent chain as regular input."""
    try:
        with _parent_descriptors(root, relative, unsafe_gap) as (
            canonical,
            components,
            directories,
        ):
            before = os.stat(components[-1], dir_fd=directories[-1], follow_symlinks=False)
            if not stat.S_ISLNK(before.st_mode):
                raise ValueError(unsafe_gap)
            target = os.readlink(components[-1], dir_fd=directories[-1])
            after = os.stat(components[-1], dir_fd=directories[-1], follow_symlinks=False)
            _validate_snapshot(
                _ReadSnapshot(
                    root, tuple(directories), components, before, after, len(os.fsencode(target))
                ),
                unstable_gap,
                canonical,
            )
            return target
    except (OSError, NotImplementedError) as error:
        raise ValueError(unsafe_gap) from error


@contextmanager
def _parent_descriptors(
    root: Path, relative: str, gap: str
) -> Generator[tuple[Path, tuple[str, ...], list[int]]]:
    path = PurePosixPath(relative)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not all((nofollow, directory)) or _member_path_invalid(root, relative):
        raise ValueError(gap)
    directories: list[int] = []
    try:
        canonical = root.resolve(strict=True)
        components = (*canonical.parts[1:], *path.parts)
        directories.append(os.open(canonical.anchor, os.O_RDONLY | directory | nofollow))
        for component in components[:-1]:
            directories.append(
                os.open(component, os.O_RDONLY | directory | nofollow, dir_fd=directories[-1])
            )
        yield canonical, components, directories
    finally:
        for descriptor in reversed(directories):
            os.close(descriptor)


def _member_path_invalid(root: Path, relative: str) -> bool:
    """Accept only a relative member below a root that is not itself an alias."""
    path = PurePosixPath(relative)
    return (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or "\\" in relative
        or "\0" in relative
        or root.is_symlink()
    )


def _portable_regular_bytes(
    root: Path,
    relative: str,
    *,
    gaps: tuple[str, str, str],
    max_bytes: int,
    expected_mode: int | None,
) -> bytes:
    """Read through plain paths whose every component stays one non-alias identity.

    Such hosts do not expose native mode bits, so a requested mode remains a refusal.
    """
    unsafe_gap, unstable_gap, size_gap = gaps
    if expected_mode is not None or _member_path_invalid(root, relative):
        raise ValueError(unsafe_gap)
    try:
        canonical = root.resolve(strict=True)
        parts = PurePosixPath(relative).parts
        chain = tuple(canonical.joinpath(*parts[: index + 1]) for index in range(len(parts)))
        before = _plain_chain(chain, unsafe_gap)
        with chain[-1].open("rb") as source:
            opened = os.fstat(source.fileno())
            if _identity(opened)[:2] != _identity(before[-1])[:2]:
                raise ValueError(unstable_gap)
            if opened.st_size > max_bytes:
                raise ValueError(size_gap)
            content = source.read(opened.st_size + 1)
            after = os.fstat(source.fileno())
        current = _plain_chain(chain, unstable_gap)
    except OSError as error:
        raise ValueError(unsafe_gap) from error
    if len(content) > opened.st_size:
        raise ValueError(size_gap)
    if (
        _identity(opened) != _identity(after)
        or len(content) != after.st_size
        or _identity(current[-1]) != _identity(after)
        or any(
            old[:2] != new[:2]
            for old, new in zip(map(_identity, before), map(_identity, current), strict=True)
        )
    ):
        raise ValueError(unstable_gap)
    return content


def _plain_chain(chain: tuple[Path, ...], gap: str) -> tuple[os.stat_result, ...]:
    """Observe directories, then one regular member, refusing links and Windows reparse points."""
    observed = tuple(item.lstat() for item in chain)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if any(
        stat.S_ISLNK(item.st_mode) or getattr(item, "st_file_attributes", 0) & reparse
        for item in observed
    ) or not (
        all(stat.S_ISDIR(item.st_mode) for item in observed[:-1])
        and stat.S_ISREG(observed[-1].st_mode)
    ):
        raise ValueError(gap)
    return observed


def _validate_snapshot(snapshot: _ReadSnapshot, gap: str, canonical: Path) -> None:
    before, after = snapshot.before, snapshot.after
    if (
        _identity(before) != _identity(after)
        or before.st_mode != after.st_mode
        or snapshot.content_length != after.st_size
    ):
        raise ValueError(gap)
    try:
        for parent, component, child in zip(
            snapshot.directories, snapshot.components, snapshot.directories[1:], strict=False
        ):
            current = os.stat(component, dir_fd=parent, follow_symlinks=False)
            if (
                not stat.S_ISDIR(current.st_mode)
                or _identity(current)[:2] != _identity(os.fstat(child))[:2]
            ):
                raise ValueError(gap)
        current = os.stat(
            snapshot.components[-1], dir_fd=snapshot.directories[-1], follow_symlinks=False
        )
        root_current = snapshot.root.stat(follow_symlinks=False)
        root_descriptor = snapshot.directories[len(canonical.parts) - 1]
        if (
            stat.S_IFMT(current.st_mode) != stat.S_IFMT(after.st_mode)
            or _identity(current) != _identity(after)
            or not stat.S_ISDIR(root_current.st_mode)
            or _identity(root_current)[:2] != _identity(os.fstat(root_descriptor))[:2]
        ):
            raise ValueError(gap)
    except (OSError, NotImplementedError) as error:
        raise ValueError(gap) from error


def _identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def observed_document_origins(root: Path) -> DocumentOrigins:
    """Return native original verification or bounded refusal as composition data."""
    try:
        return DocumentOrigins(_verified_document_origins(root))
    except GitExecutionError:
        raise
    except ValueError as error:
        return DocumentOrigins({}, (str(error),))


def _verified_document_origins(root: Path) -> dict[str, RetainedDocument]:
    """Verify declared immutable originals through native Git and safe live reads."""
    origins = retained_document_origins(root)
    if not origins:
        return {}
    declaration = (docs_root(root) / "_meta/taxonomy.toml").relative_to(root).as_posix()
    gap = f"docs_metadata_invalid:{declaration}:retained_origin"
    revisions: dict[str, list[str]] = defaultdict(list)
    for path, entry in origins.items():
        revisions[entry.origin.partition(":")[0]].append(path)
    read_objects(root, tuple(revisions), kind="commit", gap=gap)
    members = _retained_tree_members(root, revisions, gap)
    originals = read_objects(root, tuple(oid for _path, _mode, oid in members), gap=gap)
    for (path, mode, _oid), original in zip(members, originals, strict=True):
        actual = read_regular_bytes(
            root,
            path,
            unsafe_gap=gap,
            unstable_gap=gap,
            size_gap=gap,
            max_bytes=max(len(original), 1),
            expected_mode=0o755 if mode == "100755" else 0o644,
        )
        if actual != original:
            raise ValueError(gap)
    return origins


def _retained_tree_members(
    root: Path, revisions: dict[str, list[str]], gap: str
) -> list[tuple[str, str, str]]:
    """Observe exact regular blobs through the existing native Git adapter."""
    members = []
    for revision, paths in revisions.items():
        observed = run_git(
            root,
            "ls-tree",
            "-z",
            revision,
            "--",
            *paths,
            text=False,
            check=False,
            timeout=30,
            observation=True,
        )
        records = {}
        if observed.returncode:
            raise ValueError(gap)
        for raw in observed.stdout.split(b"\0"):
            if raw:
                header, member = raw.split(b"\t", 1)
                records[member.decode()] = header.decode().split()
        if set(records) != set(paths):
            raise ValueError(gap)
        for path in paths:
            mode, kind, oid = records[path]
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise ValueError(gap)
            members.append((path, mode, oid))
    return members
