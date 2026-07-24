"""Strict immutable Git tree/blob snapshot loading for source-budget replay.

The adapter uses ``git ls-tree`` for identity and one ``git cat-file --batch``
exchange for selected content. It reads historical objects without materializing
their tree.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Never

if TYPE_CHECKING:
    from collections.abc import Iterable

_OID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_REGULAR_MODES = frozenset({"100644", "100755"})
_SHA256 = r"[0-9a-f]{64}"
_GIT_TIMEOUT_SECONDS = 30
_GIT_EXECUTABLE = shutil.which("git")
_PATH_CONTENT_PAIR_SIZE = 2
_MISSING_HEADER_FIELD_COUNT = 2
_BLOB_HEADER_FIELD_COUNT = 3


def _invalid(message: str) -> Never:
    raise ValueError(message)


@dataclass(frozen=True, slots=True)
class GitTreeEntry:
    """One validated regular blob entry in a Git tree."""

    relative_path: str
    mode: str
    object_type: str
    oid: str

    def __post_init__(self) -> None:
        raw = self.relative_path.encode("utf-8")
        if (
            _valid_path(raw) != self.relative_path
            or self.mode not in _REGULAR_MODES
            or self.object_type != "blob"
            or not _OID.fullmatch(self.oid)
        ):
            _invalid("invalid Git tree entry")


@dataclass(frozen=True, slots=True)
class GitTreeSnapshot:
    """One immutable commit/tree identity and its complete regular entries."""

    commit_sha: str
    tree_sha: str
    entries: tuple[GitTreeEntry, ...]
    snapshot_digest: str

    def __post_init__(self) -> None:
        paths = tuple(item.relative_path for item in self.entries)
        if (
            not _OID.fullmatch(self.commit_sha)
            or not _OID.fullmatch(self.tree_sha)
            or paths != tuple(sorted(set(paths)))
            or self.snapshot_digest != _tree_digest(self.commit_sha, self.tree_sha, self.entries)
        ):
            _invalid("invalid Git tree snapshot")


@dataclass(frozen=True, slots=True)
class GitTreeSnapshotLoad:
    """All-or-nothing Git tree snapshot load."""

    snapshot: GitTreeSnapshot | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        invalid = (self.snapshot is None) == (not self.required_gaps)
        invalid = invalid or self.required_gaps != tuple(sorted(set(self.required_gaps)))
        if invalid:
            _invalid("invalid Git tree snapshot load")


@dataclass(frozen=True, slots=True)
class SnapshotBytes:
    """Selected path-keyed immutable blob bytes from one tree snapshot."""

    tree_snapshot_digest: str
    contents: tuple[tuple[str, bytes], ...]
    content_digest: str

    def __post_init__(self) -> None:
        valid_header = (
            type(self.tree_snapshot_digest) is str
            and re.fullmatch(_SHA256, self.tree_snapshot_digest) is not None
            and type(self.contents) is tuple
            and type(self.content_digest) is str
            and re.fullmatch(_SHA256, self.content_digest) is not None
        )
        if not valid_header:
            _invalid("invalid snapshot bytes")
        valid_contents = all(
            type(item) is tuple
            and len(item) == _PATH_CONTENT_PAIR_SIZE
            and type(item[0]) is str
            and type(item[1]) is bytes
            for item in self.contents
        )
        if not valid_contents:
            _invalid("invalid snapshot bytes")
        paths = tuple(item[0] for item in self.contents)
        if paths != tuple(sorted(set(paths))) or self.content_digest != _bytes_digest(
            self.contents
        ):
            _invalid("invalid snapshot bytes")


@dataclass(frozen=True, slots=True)
class SnapshotBytesLoad:
    """All-or-nothing selected blob load."""

    snapshot: SnapshotBytes | None
    required_gaps: tuple[str, ...]

    def __post_init__(self) -> None:
        invalid = (self.snapshot is None) == (not self.required_gaps)
        invalid = invalid or self.required_gaps != tuple(sorted(set(self.required_gaps)))
        if invalid:
            _invalid("invalid snapshot bytes load")


def _gaps(*values: str) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _git_environment() -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LANG": "C",
            "LC_ALL": "C",
        }
    )
    return environment


def _run_git(
    root: Path,
    *args: str,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess[bytes] | None:
    if _GIT_EXECUTABLE is None:
        return None
    try:
        return subprocess.run(  # noqa: S603, RUF100 - exact audited argv, no shell
            [_GIT_EXECUTABLE, "--no-replace-objects", "-C", str(root), *args],
            input=input_bytes,
            capture_output=True,
            check=False,
            env=_git_environment(),
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (
        FileNotFoundError,
        MemoryError,
        NotADirectoryError,
        OSError,
        ValueError,
        subprocess.SubprocessError,
    ):
        return None


def _command_succeeded(
    completed: subprocess.CompletedProcess[bytes] | None,
) -> bool:
    return bool(
        type(completed) is subprocess.CompletedProcess
        and completed.returncode == 0
        and type(completed.stdout) is bytes
        and type(completed.stderr) is bytes
        and not completed.stderr
    )


def _bound_root(root: Path) -> Path | None:
    try:
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    completed = _run_git(resolved, "rev-parse", "--show-toplevel")
    if (
        not _command_succeeded(completed)
        or completed is None
        or completed.stdout.count(b"\n") != 1
        or not completed.stdout.endswith(b"\n")
    ):
        return None
    try:
        observed = Path(completed.stdout[:-1].decode("utf-8")).resolve(strict=True)
    except (OSError, RuntimeError, UnicodeDecodeError):
        return None
    return resolved if observed == resolved else None


def _identity(root: Path, expression: str) -> str | None:
    completed = _run_git(root, "rev-parse", "--verify", "--end-of-options", expression)
    if not _command_succeeded(completed) or completed is None:
        return None
    if not completed.stdout.endswith(b"\n") or completed.stdout.count(b"\n") != 1:
        return None
    try:
        value = completed.stdout[:-1].decode("ascii")
    except UnicodeDecodeError:
        return None
    return value if _OID.fullmatch(value) else None


def _valid_path(raw: bytes) -> str | None:
    try:
        value = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    parts = value.split("/")
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or any(part in {"", ".", ".."} for part in parts)
        or value.encode("utf-8") != raw
    ):
        return None
    return value


def _parse_ls_tree_record(
    record: bytes,
    previous: bytes,
) -> tuple[GitTreeEntry | None, str | None]:
    try:
        header, path_raw = record.split(b"\t", 1)
        mode_raw, type_raw, oid_raw = header.split(b" ")
        mode = mode_raw.decode("ascii")
        object_type = type_raw.decode("ascii")
        oid = oid_raw.decode("ascii")
    except (UnicodeDecodeError, ValueError):
        return None, "git_snapshot_ls_tree_invalid"
    relative = _valid_path(path_raw)
    if relative is None:
        return None, "git_snapshot_path_invalid"
    if mode not in _REGULAR_MODES or object_type != "blob":
        return None, f"git_snapshot_object_unsupported:{relative}"
    if not _OID.fullmatch(oid) or (previous and path_raw <= previous):
        return None, "git_snapshot_ls_tree_invalid"
    return GitTreeEntry(relative, mode, object_type, oid), None


def _parse_ls_tree(
    raw: bytes,
) -> tuple[tuple[GitTreeEntry, ...] | None, tuple[str, ...]]:
    if not raw:
        return (), ()
    if not raw.endswith(b"\0"):
        return None, ("git_snapshot_ls_tree_invalid",)
    entries: list[GitTreeEntry] = []
    previous = b""
    for record in raw[:-1].split(b"\0"):
        entry, gap = _parse_ls_tree_record(record, previous)
        if entry is None:
            return None, _gaps(gap or "git_snapshot_ls_tree_invalid")
        previous = record.split(b"\t", 1)[1]
        entries.append(entry)
    return tuple(entries), ()


def _tree_digest(
    commit_sha: str,
    tree_sha: str,
    entries: Iterable[GitTreeEntry],
) -> str:
    payload = {
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "entries": [
            {
                "path": entry.relative_path,
                "mode": entry.mode,
                "type": entry.object_type,
                "oid": entry.oid,
            }
            for entry in entries
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _tree_snapshot_from_bound_root(root: Path, treeish: str) -> GitTreeSnapshotLoad:
    commit_sha = _identity(root, f"{treeish}^{{commit}}")
    if commit_sha is None:
        return GitTreeSnapshotLoad(None, ("git_snapshot_commit_unresolved",))
    tree_sha = _identity(root, f"{commit_sha}^{{tree}}")
    if tree_sha is None:
        return GitTreeSnapshotLoad(None, ("git_snapshot_tree_unresolved",))
    completed = _run_git(root, "ls-tree", "-r", "-z", "--full-tree", tree_sha)
    if not _command_succeeded(completed) or completed is None:
        return GitTreeSnapshotLoad(None, ("git_snapshot_ls_tree_failed",))
    entries, gaps = _parse_ls_tree(completed.stdout)
    if entries is None:
        return GitTreeSnapshotLoad(None, gaps)
    snapshot = GitTreeSnapshot(
        commit_sha=commit_sha,
        tree_sha=tree_sha,
        entries=entries,
        snapshot_digest=_tree_digest(commit_sha, tree_sha, entries),
    )
    return GitTreeSnapshotLoad(snapshot, ())


def tree_snapshot(root: Path, treeish: str) -> GitTreeSnapshotLoad:
    """Peel one treeish and load its strict full-tree blob identity."""
    if not isinstance(root, Path) or type(treeish) is not str or not treeish:
        return GitTreeSnapshotLoad(None, ("git_snapshot_request_invalid",))
    bound_root = _bound_root(root)
    if bound_root is None:
        return GitTreeSnapshotLoad(None, ("git_snapshot_root_invalid",))
    return _tree_snapshot_from_bound_root(bound_root, treeish)


def _worktree_snapshot_from_bound_root(root: Path) -> GitTreeSnapshotLoad:
    before = _identity(root, "HEAD^{commit}")
    if before is None:
        return GitTreeSnapshotLoad(None, ("git_snapshot_commit_unresolved",))
    completed = _run_git(
        root,
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
    )
    if not _command_succeeded(completed) or completed is None:
        return GitTreeSnapshotLoad(None, ("git_snapshot_worktree_status_failed",))
    after = _identity(root, "HEAD^{commit}")
    if before != after:
        return GitTreeSnapshotLoad(None, ("git_snapshot_head_changed",))
    if completed.stdout:
        return GitTreeSnapshotLoad(None, ("git_snapshot_worktree_dirty",))
    return _tree_snapshot_from_bound_root(root, before)


def worktree_snapshot(root: Path) -> GitTreeSnapshotLoad:
    """Load immutable HEAD only when tracked and untracked state is clean."""
    if not isinstance(root, Path):
        return GitTreeSnapshotLoad(None, ("git_snapshot_request_invalid",))
    bound_root = _bound_root(root)
    if bound_root is None:
        return GitTreeSnapshotLoad(None, ("git_snapshot_root_invalid",))
    return _worktree_snapshot_from_bound_root(bound_root)


def _parse_batch_header(header: bytes, oid: str) -> tuple[int | None, str | None]:
    try:
        fields = header.decode("ascii").split(" ")
    except UnicodeDecodeError:
        return None, "git_snapshot_blob_batch_invalid"
    if len(fields) == _MISSING_HEADER_FIELD_COUNT and fields == [oid, "missing"]:
        return None, f"git_snapshot_blob_missing:{oid}"
    if len(fields) != _BLOB_HEADER_FIELD_COUNT or fields[0] != oid or fields[1] != "blob":
        return None, "git_snapshot_blob_batch_invalid"
    size_text = fields[2]
    if not size_text.isdecimal() or (len(size_text) > 1 and size_text.startswith("0")):
        return None, "git_snapshot_blob_batch_invalid"
    return int(size_text), None


def _batch_contents(
    raw: bytes,
    requested: tuple[str, ...],
) -> tuple[dict[str, bytes] | None, str | None]:
    position = 0
    contents: dict[str, bytes] = {}
    for oid in requested:
        newline = raw.find(b"\n", position)
        if newline < 0:
            return None, "git_snapshot_blob_batch_invalid"
        size, gap = _parse_batch_header(raw[position:newline], oid)
        if size is None:
            return None, gap or "git_snapshot_blob_batch_invalid"
        position = newline + 1
        end = position + size
        if end >= len(raw) or raw[end : end + 1] != b"\n":
            return None, "git_snapshot_blob_batch_invalid"
        contents[oid] = raw[position:end]
        position = end + 1
    if position != len(raw):
        return None, "git_snapshot_blob_batch_invalid"
    return contents, None


def _bytes_digest(contents: tuple[tuple[str, bytes], ...]) -> str:
    payload = [
        {
            "path": path,
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for path, content in contents
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _selected_entries(
    snapshot: GitTreeSnapshot,
    relative_paths: tuple[str, ...],
) -> tuple[tuple[GitTreeEntry, ...] | None, tuple[str, ...]]:
    if type(relative_paths) is not tuple or any(type(path) is not str for path in relative_paths):
        return None, ("git_snapshot_request_invalid",)
    if relative_paths != tuple(sorted(set(relative_paths))):
        return None, ("git_snapshot_path_selection_invalid",)
    entries = {entry.relative_path: entry for entry in snapshot.entries}
    if any(path not in entries for path in relative_paths):
        return None, ("git_snapshot_path_selection_invalid",)
    return tuple(entries[path] for path in relative_paths), ()


def _read_bound_snapshot_blobs(
    root: Path,
    snapshot: GitTreeSnapshot,
    selected: tuple[GitTreeEntry, ...],
) -> SnapshotBytesLoad:
    requested = tuple(dict.fromkeys(entry.oid for entry in selected))
    if requested:
        batch_input = b"".join(oid.encode("ascii") + b"\n" for oid in requested)
        completed = _run_git(root, "cat-file", "--batch", input_bytes=batch_input)
        if not _command_succeeded(completed) or completed is None:
            return SnapshotBytesLoad(None, ("git_snapshot_blob_batch_failed",))
        by_oid, gap = _batch_contents(completed.stdout, requested)
        if by_oid is None:
            return SnapshotBytesLoad(
                None,
                _gaps(gap or "git_snapshot_blob_batch_invalid"),
            )
    else:
        by_oid = {}
    contents = tuple((entry.relative_path, by_oid[entry.oid]) for entry in selected)
    return SnapshotBytesLoad(
        SnapshotBytes(
            tree_snapshot_digest=snapshot.snapshot_digest,
            contents=contents,
            content_digest=_bytes_digest(contents),
        ),
        (),
    )


def read_snapshot_blobs(
    root: Path,
    snapshot: GitTreeSnapshot,
    relative_paths: tuple[str, ...],
) -> SnapshotBytesLoad:
    """Read selected snapshot blobs through one strict deduplicated batch."""
    if not isinstance(root, Path) or type(snapshot) is not GitTreeSnapshot:
        return SnapshotBytesLoad(None, ("git_snapshot_request_invalid",))
    bound_root = _bound_root(root)
    if bound_root is None:
        return SnapshotBytesLoad(None, ("git_snapshot_root_invalid",))
    selected, gaps = _selected_entries(snapshot, relative_paths)
    if selected is None:
        return SnapshotBytesLoad(None, gaps)
    return _read_bound_snapshot_blobs(bound_root, snapshot, selected)
