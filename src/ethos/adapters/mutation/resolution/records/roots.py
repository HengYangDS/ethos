"""Current-record location and descriptor-bound parent ownership."""

from __future__ import annotations

import hashlib
import os
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.records.io.posix as posix
from ethos.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from collections.abc import Iterator

_CURRENT = Path("recovery/lane-resolution-v2")
_HISTORY = Path("recovery/lane-resolution")
_WORKTREE_HISTORY = Path("build/artifacts/lane-resolution")
_UNAVAILABLE = "lane_resolution_accepted_control_root_unavailable"
_UNSAFE = "lane_resolution_record_path_unsafe"
_CHANGED = "lane_resolution_current_record_changed"
_VALUE_FIELDS = {b"worktree", b"HEAD", b"branch"}
_FLAG_FIELDS = {b"bare", b"detached", b"locked", b"prunable"}
_OPTIONAL_VALUE_FIELDS = {b"locked", b"prunable"}
_RECEIPTS = "receipts"
_DIRECT_CHILD_PART_COUNT = 2


@dataclass(frozen=True, slots=True)
class RecordParent:
    record_root: Path
    destination: Path
    root_descriptor: int
    parent_descriptor: int
    category: str
    name: str
    root_identity: posix.DirectoryIdentity
    parent_identity: posix.DirectoryIdentity


def record_path_is_safe(record_root: Path, destination: Path) -> bool:
    """Return whether a record path stays under non-symlinked owner components."""
    lexical_root = record_root.absolute()
    lexical_destination = destination.absolute()
    try:
        relative_destination = lexical_destination.relative_to(lexical_root)
    except ValueError:
        return False
    if ".." in relative_destination.parts:
        return False
    try:
        resolved_root = lexical_root.resolve()
    except (OSError, RuntimeError):
        return False
    if resolved_root != lexical_root:
        return False
    current = lexical_root
    for part in relative_destination.parts:
        current /= part
        if current.is_symlink():
            return False
    try:
        destination_safe = lexical_destination.resolve().is_relative_to(resolved_root)
    except (OSError, RuntimeError):
        destination_safe = False
    return destination_safe


def display_record_path(root: Path, path: Path) -> str:
    """Keep worktree paths relative while representing sibling records absolutely."""
    candidate = path.resolve()
    try:
        return candidate.relative_to(root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def accepted_control_root(root: Path) -> Path:
    """Return the registered checkout holding the configured accepted branch."""
    primary = _primary_control_root(root)
    branch = f"refs/heads/{load_branch_role_policy(primary).accepted_branch}"
    head = _git_output(primary, "rev-parse", "--verify", branch)
    for record in _registered_worktrees(primary) if head else ():
        candidate = Path(record.get("worktree", "")).resolve()
        if (
            record.get("branch") == branch
            and candidate.is_dir()
            and _git_output(candidate, "rev-parse", "HEAD") == head
        ):
            return candidate
    raise ValueError(_UNAVAILABLE)


def current_record_root(root: Path) -> Path:
    control = accepted_control_root(root)
    return control.parent / f"{control.name}-records" / _CURRENT


def record_path(
    root: Path,
    category: str,
    decision_id: str,
    *,
    artifact_root: Path | None = None,
) -> Path:
    """Return one digest-addressed record path under the stable owner."""
    return (
        (artifact_root or current_record_root(root))
        / category
        / f"{hashlib.sha256(decision_id.encode()).hexdigest()}.json"
    )


def receipt_path(
    root: Path,
    decision_id: str,
    *,
    artifact_root: Path | None = None,
) -> Path:
    """Return the deterministic immutable receipt path."""
    return record_path(root, _RECEIPTS, decision_id, artifact_root=artifact_root)


def historical_record_roots(root: Path) -> tuple[Path, ...]:
    control = accepted_control_root(root)
    candidates = [control.parent / f"{control.name}-records" / _HISTORY]
    candidates.extend(
        Path(record["worktree"]).absolute() / _WORKTREE_HISTORY
        for record in _registered_worktrees(root)
        if record.get("worktree") and Path(record["worktree"]).is_dir()
    )
    return tuple(dict.fromkeys(path.absolute() for path in candidates))


def direct_child_parts(root: Path, destination: Path) -> tuple[str, str]:
    try:
        relative = destination.absolute().relative_to(root.absolute())
    except ValueError as error:
        raise OSError(_UNSAFE) from error
    if len(relative.parts) != _DIRECT_CHILD_PART_COUNT or ".." in relative.parts:
        raise OSError(_UNSAFE)
    return relative.parts


@contextmanager
def open_directory_pair(
    path: Path, child: str, *, create: bool
) -> Iterator[tuple[int, int, posix.DirectoryIdentity, posix.DirectoryIdentity]]:
    root = posix.open_directory_path(path, create=create)
    nested: int | None = None
    try:
        nested = posix.open_directory_child(root, child, create=create)
        yield (
            root,
            nested,
            posix.directory_identity(os.fstat(root)),
            posix.directory_identity(os.fstat(nested)),
        )
    finally:
        if nested is not None:
            os.close(nested)
        os.close(root)


def directory_binding_matches(
    path: Path,
    child: str,
    root_identity: posix.DirectoryIdentity,
    child_identity: posix.DirectoryIdentity,
) -> bool:
    try:
        return posix.directory_binding(path, child) == (root_identity, child_identity)
    except OSError:
        return False


@contextmanager
def open_record_parent(
    record_root: Path, destination: Path, *, create: bool
) -> Iterator[RecordParent]:
    category, name = direct_child_parts(record_root, destination)
    if not record_path_is_safe(record_root, destination):
        raise OSError(_UNSAFE)
    try:
        with open_directory_pair(record_root, category, create=create) as opened:
            parent = RecordParent(
                record_root, destination, *opened[:2], category, name, *opened[2:]
            )
            require_parent_identity(parent)
            yield parent
    except (FileExistsError, FileNotFoundError):
        raise
    except OSError as error:
        raise OSError(_UNSAFE) from error


def require_parent_identity(parent: RecordParent) -> None:
    if not directory_binding_matches(
        parent.record_root, parent.category, parent.root_identity, parent.parent_identity
    ):
        raise OSError(_UNSAFE)


def require_entry_identity(
    parent: RecordParent, name: str, *, match_name: str | None = None, changed: bool
) -> posix.FileIdentity:
    identity = posix.entry_file_identity(parent.parent_descriptor, name)
    matches = (
        match_name is None
        or posix.entry_file_identity(parent.parent_descriptor, match_name) == identity
    )
    if identity is not None and matches:
        return identity
    raise ValueError(_CHANGED) if changed else OSError(_UNSAFE)


def canonical_record_path(root: Path, path: Path) -> bool:
    try:
        category = current_record_root(root) / "decisions"
    except ValueError:
        return False
    candidate = path.absolute()
    return (
        candidate.parent == category.absolute()
        and candidate.suffix == ".json"
        and record_path_is_safe(category, candidate)
    )


def _primary_control_root(root: Path) -> Path:
    raw = _git_output(root, "rev-parse", "--git-common-dir")
    common = Path(raw) if raw else Path()
    if raw and not common.is_absolute():
        common = root / common
    primary = common.resolve().parent
    if not raw or not primary.is_dir():
        raise ValueError(_UNAVAILABLE)
    return primary


def _registered_worktrees(root: Path) -> list[dict[str, str]]:
    try:
        completed = _git_run(root, "worktree", "list", "--porcelain")
        valid = not completed.returncode and not completed.stderr
        valid &= isinstance(completed.stdout, bytes) and isinstance(completed.stderr, bytes)
    except (OSError, subprocess.SubprocessError, TypeError) as error:
        raise ValueError(_UNAVAILABLE) from error
    if not valid:
        raise ValueError(_UNAVAILABLE)
    return _parse_registered_worktrees(completed.stdout)


def _parse_registered_worktrees(output: bytes) -> list[dict[str, str]]:
    if not output.endswith(b"\n\n"):
        raise ValueError(_UNAVAILABLE)
    records = [_parse_registered_worktree(raw) for raw in output.split(b"\n\n")[:-1]]
    if not records or len({record["worktree"] for record in records}) != len(records):
        raise ValueError(_UNAVAILABLE)
    return records


def _parse_registered_worktree(raw: bytes) -> dict[str, str]:
    record: dict[str, str] = {}
    for line in raw.splitlines():
        key, separator, value = line.partition(b" ")
        decoded = key.decode()
        if decoded in record or key not in _VALUE_FIELDS | _FLAG_FIELDS:
            raise ValueError(_UNAVAILABLE)
        if key in _VALUE_FIELDS and (not separator or not value):
            raise ValueError(_UNAVAILABLE)
        if key in _FLAG_FIELDS - _OPTIONAL_VALUE_FIELDS and separator:
            raise ValueError(_UNAVAILABLE)
        if b"\0" in value:
            raise ValueError(_UNAVAILABLE)
        record[decoded] = value.decode() if separator else ""
    head = record.get("HEAD", "")
    branch = record.get("branch", "")
    if (
        not record.get("worktree")
        or not _oid(head)
        or (branch and not branch.startswith("refs/heads/"))
    ):
        raise ValueError(_UNAVAILABLE)
    return record


def _oid(value: str) -> bool:
    return len(value) in {40, 64} and not set(value).difference("0123456789abcdef")


def _git_output(root: Path, *args: str) -> str:
    try:
        completed = _git_run(root, *args)
        output = completed.stdout
        if completed.returncode or completed.stderr or not isinstance(output, bytes):
            return ""
        if not output.endswith(b"\n") or output.count(b"\n") != 1:
            return ""
        return output[:-1].decode()
    except (OSError, UnicodeDecodeError, subprocess.SubprocessError, TypeError):
        return ""


def _git_run(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LC_ALL": "C",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
    }
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        env=environment,
        shell=False,
    )
