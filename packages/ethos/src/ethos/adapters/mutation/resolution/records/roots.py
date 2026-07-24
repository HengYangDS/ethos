"""Current and historical lane-resolution record root locations."""

from __future__ import annotations

import os
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.records.io.posix as posix
from ethos.adapters.mutation.resolution._shared import record_destination_safe
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from collections.abc import Iterator

_CURRENT_RECORD_ROOT = Path("recovery/lane-resolution-v2")
_HISTORICAL_RECORD_ROOT = Path("recovery/lane-resolution")
_WORKTREE_HISTORY_ROOT = Path("build/artifacts/lane-resolution")
_CONTROL_ROOT_UNAVAILABLE = "lane_resolution_accepted_control_root_unavailable"
_RECORD_PATH_UNSAFE = "lane_resolution_record_path_unsafe"
_CURRENT_RECORD_CHANGED = "lane_resolution_current_record_changed"
_DIRECT_CHILD_DEPTH = 2


@dataclass(frozen=True, slots=True)
class RecordParent:
    """Hold one exact current-record root, category, and destination binding."""

    record_root: Path
    destination: Path
    root_descriptor: int
    parent_descriptor: int
    category: str
    name: str
    root_identity: posix.DirectoryIdentity
    parent_identity: posix.DirectoryIdentity


def accepted_control_root(root: Path) -> Path:
    """Return the registered checkout for the configured accepted branch."""
    primary_root = _primary_control_root(root)
    accepted_ref = f"refs/heads/{load_branch_role_policy(primary_root).accepted_branch}"
    accepted_head = _git_output(primary_root, "rev-parse", "--verify", accepted_ref)
    if not accepted_head:
        raise ValueError(_CONTROL_ROOT_UNAVAILABLE)
    for current in _registered_worktrees(primary_root):
        if current.get("branch") != accepted_ref:
            continue
        candidate = Path(current.get("worktree", "")).resolve()
        if candidate.is_dir() and _git_output(candidate, "rev-parse", "HEAD") == accepted_head:
            return candidate
    raise ValueError(_CONTROL_ROOT_UNAVAILABLE)


def current_record_root(root: Path) -> Path:
    """Return the sole versioned root authorized for current records."""
    control_root = accepted_control_root(root)
    return control_root.parent / f"{control_root.name}-records" / _CURRENT_RECORD_ROOT


def historical_record_roots(root: Path) -> tuple[Path, ...]:
    """Return deduplicated read-only predecessor record locations."""
    control_root = accepted_control_root(root)
    candidates = (
        control_root.parent / f"{control_root.name}-records" / _HISTORICAL_RECORD_ROOT,
        *(
            Path(record["worktree"]).absolute() / _WORKTREE_HISTORY_ROOT
            for record in _registered_worktrees(root)
            if record.get("worktree") and Path(record["worktree"]).is_dir()
        ),
    )
    return tuple(dict.fromkeys(path.absolute() for path in candidates))


def direct_child_parts(root: Path, destination: Path) -> tuple[str, str]:
    """Return exactly one direct category and child name below a lexical root."""
    try:
        relative = destination.absolute().relative_to(root.absolute())
    except ValueError as error:
        raise OSError(_RECORD_PATH_UNSAFE) from error
    if len(relative.parts) != _DIRECT_CHILD_DEPTH or ".." in relative.parts:
        raise OSError(_RECORD_PATH_UNSAFE)
    return relative.parts[0], relative.parts[1]


@contextmanager
def open_directory_pair(
    path: Path,
    child: str,
    *,
    create: bool,
) -> Iterator[tuple[int, int, posix.DirectoryIdentity, posix.DirectoryIdentity]]:
    """Hold one lexical root and direct child with their verified identities."""
    root_descriptor = posix.open_directory_path(path, create=create)
    child_descriptor: int | None = None
    try:
        child_descriptor = posix.open_directory_child(root_descriptor, child, create=create)
        yield (
            root_descriptor,
            child_descriptor,
            posix.directory_identity(os.fstat(root_descriptor)),
            posix.directory_identity(os.fstat(child_descriptor)),
        )
    finally:
        if child_descriptor is not None:
            os.close(child_descriptor)
        os.close(root_descriptor)


def directory_binding_matches(
    path: Path,
    child: str,
    root_identity: posix.DirectoryIdentity,
    child_identity: posix.DirectoryIdentity,
) -> bool:
    """Return whether a lexical root and child still match captured identities."""
    try:
        return posix.directory_binding(path, child) == (root_identity, child_identity)
    except OSError:
        return False


@contextmanager
def open_record_parent(
    record_root: Path,
    destination: Path,
    *,
    create: bool,
) -> Iterator[RecordParent]:
    """Hold one exact current-record category binding for an operation."""
    category, name = direct_child_parts(record_root, destination)
    if not record_destination_safe(record_root, destination):
        raise OSError(_RECORD_PATH_UNSAFE)
    binding = open_directory_pair(record_root, category, create=create)
    try:
        root_descriptor, parent_descriptor, root_identity, parent_identity = binding.__enter__()
    except (FileNotFoundError, FileExistsError):
        raise
    except OSError as error:
        raise OSError(_RECORD_PATH_UNSAFE) from error
    parent = RecordParent(
        record_root,
        destination,
        root_descriptor,
        parent_descriptor,
        category,
        name,
        root_identity,
        parent_identity,
    )
    try:
        require_parent_identity(parent)
        yield parent
    finally:
        binding.__exit__(None, None, None)


def require_parent_identity(parent: RecordParent) -> None:
    """Require one held record parent to remain its exact lexical binding."""
    if not directory_binding_matches(
        parent.record_root,
        parent.category,
        parent.root_identity,
        parent.parent_identity,
    ):
        raise OSError(_RECORD_PATH_UNSAFE)


def require_entry_identity(
    parent: RecordParent,
    name: str,
    *,
    match_name: str | None = None,
    changed: bool,
) -> posix.FileIdentity:
    """Return one exact visible entry identity or the domain-specific CAS error."""
    identity = posix.entry_file_identity(parent.parent_descriptor, name)
    if identity is not None and (
        match_name is None
        or posix.entry_file_identity(parent.parent_descriptor, match_name) == identity
    ):
        return identity
    if changed:
        raise ValueError(_CURRENT_RECORD_CHANGED)
    raise OSError(_RECORD_PATH_UNSAFE)


def canonical_record_path(root: Path, path: Path) -> bool:
    """Return whether a decision is a direct JSON child of its current category."""
    try:
        decision_root = current_record_root(root) / "decisions"
    except ValueError:
        return False
    candidate = path.absolute()
    return (
        candidate.parent == decision_root.absolute()
        and candidate.suffix == ".json"
        and record_destination_safe(decision_root, candidate)
    )


def _primary_control_root(root: Path) -> Path:
    common_raw = _git_output(root, "rev-parse", "--git-common-dir")
    if not common_raw:
        raise ValueError(_CONTROL_ROOT_UNAVAILABLE)
    common = Path(common_raw)
    if not common.is_absolute():
        common = root / common
    primary = common.resolve().parent
    if not primary.is_dir():
        raise ValueError(_CONTROL_ROOT_UNAVAILABLE)
    return primary


def _registered_worktrees(root: Path) -> list[dict[str, str]]:
    completed = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise ValueError(_CONTROL_ROOT_UNAVAILABLE)
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in [*completed.stdout.splitlines(), ""]:
        if line:
            key, _, value = line.partition(" ")
            current[key] = value
            continue
        if current:
            records.append(current)
        current = {}
    return records


def _git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""
