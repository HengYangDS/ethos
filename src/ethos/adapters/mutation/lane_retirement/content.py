"""Observe the complete destructive preimage of one reviewed linked worktree."""

from __future__ import annotations

import hashlib
import os
import stat
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from typing import cast

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.filesystem import is_junction


def _fail(reason: str) -> None:
    raise ValueError(reason)


def _identity(value: os.stat_result) -> list[str]:
    # Native coordinates are opaque identities, not bounded JSON arithmetic.
    return list(
        map(
            str,
            (
                value.st_dev,
                value.st_ino,
                value.st_mode,
                value.st_uid,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
                value.st_nlink,
            ),
        )
    )


def _directory(
    path: Path, stack: ExitStack, expected: dict[Path, dict[str, object]] | None = None
) -> int:
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    stack.callback(os.close, descriptor)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
        stack.callback(os.close, descriptor)
        current /= part
        if expected is not None and current in expected:
            _require_node(
                {"kind": "directory", "identity": _identity(os.fstat(descriptor))},
                expected[current],
            )
    return descriptor


def _entry(name: str, directory: int) -> dict[str, object]:
    before = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if before.st_uid != os.getuid():
        _fail("retirement_content_owner_mismatch")
    if before.st_dev != os.fstat(directory).st_dev:
        _fail("retirement_content_filesystem_mismatch")
    record: dict[str, object] = {"identity": _identity(before)}
    if stat.S_ISDIR(before.st_mode):
        record["kind"] = "directory"
    elif stat.S_ISLNK(before.st_mode):
        record.update(kind="symlink", target=os.readlink(name, dir_fd=directory))
    elif stat.S_ISREG(before.st_mode):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, "rb") as stream:
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                _fail("retirement_content_drift")
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                _fail("retirement_content_drift")
        record.update(kind="file", sha256=digest)
    else:
        _fail("retirement_content_unsafe")
    if _identity(os.stat(name, dir_fd=directory, follow_symlinks=False)) != _identity(before):
        _fail("retirement_content_drift")
    return record


def _snapshot(root: Path, index: Path) -> dict[str, object]:
    with ExitStack() as stack:
        root_parent = _directory(root.parent, stack)
        root_record = _entry(root.name, root_parent)
        root_fd = _directory(root, stack)
        if _identity(os.fstat(root_fd)) != root_record["identity"]:
            _fail("retirement_content_drift")
        index_parent = _directory(index.parent, stack)
        index_record = _entry(index.name, index_parent)
        if index_record["kind"] != "file":
            _fail("retirement_index_unsafe")
        entries: dict[str, dict[str, object]] = {}
        for parent, directories, files, descriptor in os.fwalk(
            ".", dir_fd=root_fd, follow_symlinks=False, onerror=_walk_error
        ):
            expected = root_record if parent == "." else entries[Path(parent).as_posix()]
            if _identity(os.fstat(descriptor)) != expected["identity"]:
                _fail("retirement_content_drift")
            for name in sorted((*directories, *files)):
                record = _entry(name, descriptor)
                if name == ".git" and (parent != "." or record["kind"] != "file"):
                    _fail("retirement_nested_repository")
                entries[(Path(parent) / name).as_posix()] = record
        if (
            _entry(root.name, root_parent) != root_record
            or _entry(index.name, index_parent) != index_record
        ):
            _fail("retirement_content_drift")
    return {
        "root": root_record,
        "index_path": index.as_posix(),
        "index": index_record,
        "entries": entries,
    }


def _walk_error(error: OSError) -> None:
    raise error


def _require_node(current: object, expected: object, removed_links: int = 0) -> None:
    current, expected = cast("dict[str, object]", current), cast("dict[str, object]", expected)
    observed = cast("list[str]", current.get("identity", []))
    original = cast("list[str]", expected.get("identity", []))
    if current.get("kind") == expected.get("kind") == "directory":
        if (
            observed[:2] == original[:2]
            and observed[3] == original[3]
            and int(observed[2]) in {int(original[2]), int(original[2]) | stat.S_IRWXU}
        ):
            return
    elif current == expected or (
        removed_links > 0
        and current == {**expected, "identity": observed}
        and observed[:6] == original[:6]
        and int(observed[6]) >= int(original[6])
        and int(observed[7]) == int(original[7]) - removed_links
    ):
        return
    _fail("retirement_content_drift")


def _require_index(expected: dict[str, object]) -> None:
    index = Path(str(expected["index_path"]))
    with ExitStack() as stack:
        if _entry(index.name, _directory(index.parent, stack)) != expected["index"]:
            _fail("retirement_content_drift")


def verify_reviewed_content(root: Path, expected: dict[str, object]) -> Counter[tuple[str, ...]]:
    """Verify survivors and index; count only absent reviewed inode aliases."""
    _require_index(expected)
    removed: Counter[tuple[str, ...]] = Counter()
    if os.path.lexists(root):
        current = _snapshot(root, Path(str(expected["index_path"])))
        _require_node(current["root"], expected["root"])
        if current["index"] != expected["index"]:
            _fail("retirement_content_drift")
        entries = cast("dict[str, dict[str, object]]", expected["entries"])
        survivors = cast("dict[str, dict[str, object]]", current["entries"])
        removed.update(
            tuple(cast("list[str]", node["identity"])[:2])
            for name, node in entries.items()
            if name not in survivors and node["kind"] != "directory"
        )
        for name, node in survivors.items():
            _require_node(
                node, entries.get(name, {}), removed[tuple(cast("list[str]", node["identity"])[:2])]
            )
    return removed


def remove_reviewed_content(root: Path, expected: dict[str, object]) -> None:
    """Unlink only reviewed survivors, retaining Git recovery data until the end."""
    removed = verify_reviewed_content(root, expected)
    entries = cast("dict[str, dict[str, object]]", expected["entries"])
    nodes = {root / name: node for name, node in entries.items()}
    nodes[root] = cast("dict[str, object]", expected["root"])
    for path in sorted(nodes, key=lambda p: (p == root, p == root / ".git", -len(p.parts), str(p))):
        _require_index(expected)
        with ExitStack() as stack:
            try:
                parent = _directory(path.parent, stack, nodes)
                current = _entry(path.name, parent)
            except FileNotFoundError:
                continue
            identity = tuple(cast("list[str]", current["identity"])[:2])
            _require_node(current, nodes[path], removed[identity])
            parent_stat = os.fstat(parent)
            if parent_stat.st_uid != os.getuid():
                _fail("retirement_content_owner_mismatch")
            if path != root and parent_stat.st_mode & stat.S_IRWXU != stat.S_IRWXU:
                os.fchmod(parent, parent_stat.st_mode | stat.S_IRWXU)
            if current["kind"] == "directory":
                os.rmdir(path.name, dir_fd=parent)
            else:
                os.unlink(path.name, dir_fd=parent)
                removed[identity] += 1
    _require_index(expected)


def reviewed_content(root: Path) -> dict[str, object]:
    """Bind all literal nodes and the index; ignored files receive no exemption."""
    if not all(hasattr(os, name) for name in ("fwalk", "O_NOFOLLOW", "O_DIRECTORY")):
        _fail("retirement_content_observation_unavailable")
    if root.is_symlink() or is_junction(root) or not root.is_dir():
        _fail("retirement_content_unsafe")
    index = Path(
        run_git(
            root, "rev-parse", "--path-format=absolute", "--git-path", "index", observation=True
        ).stdout.strip()
    )
    if index.is_symlink() or is_junction(index) or not index.is_file():
        _fail("retirement_index_unsafe")
    first = _snapshot(root, index)
    if cast("dict[str, dict[str, object]]", first["entries"]).get(".git", {}).get("kind") != "file":
        _fail("retirement_content_unsafe")
    entries = run_git(root, "ls-files", "--stage", "-z", observation=True).stdout
    if any(
        row.partition("\t")[0].rsplit(" ", 1)[-1] != "0" or row.startswith("160000 ")
        for row in entries.split("\0")
        if row
    ):
        _fail("retirement_index_unmerged_or_submodule")
    if first != _snapshot(root, index):
        _fail("retirement_content_drift")
    return first
