from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from itertools import islice
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import cast

from ethos.adapters.repo.git import git_stdout_checked
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from pathlib import Path


_TEMPORARY_PROBE_HEADER_LINES = 20
_TEMPORARY_PROBE_PATH_LIMIT = 16
_TEMPORARY_PROBE_MARKER = "TEMP PROBE"


def dirty_content_sha256(root: Path) -> str:
    """Bind tracked and untracked working content without normalizing bytes."""
    digest = hashlib.sha256()
    patch = run_git(root, "diff", "--binary", "HEAD", "--", text=False, observation=True).stdout
    inventory = run_git(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        text=False,
        observation=True,
    ).stdout
    parts = [patch]
    for raw in (item for item in inventory.split(b"\0") if item):
        parts.extend((raw, _read_untracked(root, raw)))
    current_patch = run_git(
        root, "diff", "--binary", "HEAD", "--", text=False, observation=True
    ).stdout
    current_inventory = run_git(
        root,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        text=False,
        observation=True,
    ).stdout
    if patch != current_patch or inventory != current_inventory:
        message = "dirty_content_snapshot_drift"
        raise ValueError(message)
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _read_untracked(root: Path, raw: bytes) -> bytes:
    """Read one regular untracked file without following any path component."""
    relative = raw.decode(errors="surrogateescape")
    path = PurePosixPath(relative)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    nonblock = getattr(os, "O_NONBLOCK", 0)
    unsafe_gap = f"dirty_content_unsafe_path:{relative}"
    unstable_gap = f"dirty_content_unstable_path:{relative}"
    if _unsafe_untracked_path(
        path,
        nofollow=nofollow,
        directory=directory,
        nonblock=nonblock,
    ):
        raise ValueError(unsafe_gap)
    directories: list[int] = []
    file_descriptor: int | None = None
    try:
        directories.append(os.open(root, os.O_RDONLY | directory | nofollow))
        root_before = os.fstat(directories[0])
        for component in path.parts[:-1]:
            directories.append(
                os.open(
                    component,
                    os.O_RDONLY | directory | nofollow,
                    dir_fd=directories[-1],
                )
            )
        file_descriptor = os.open(
            path.parts[-1],
            os.O_RDONLY | nofollow | nonblock,
            dir_fd=directories[-1],
        )
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(unsafe_gap)
        with os.fdopen(file_descriptor, "rb", closefd=True) as source:
            file_descriptor = None
            content = source.read()
            after = os.fstat(source.fileno())
        _validate_untracked_snapshot(
            root=root,
            name=path.parts[-1],
            parent_descriptor=directories[-1],
            root_before=root_before,
            before=before,
            after=after,
            content_length=len(content),
            unstable_gap=unstable_gap,
        )
    except OSError as exc:
        raise ValueError(unsafe_gap) from exc
    else:
        return content
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        for descriptor in reversed(directories):
            os.close(descriptor)


def _unsafe_untracked_path(
    path: PurePosixPath,
    *,
    nofollow: int,
    directory: int,
    nonblock: int,
) -> bool:
    return (
        not nofollow
        or not directory
        or not nonblock
        or path.is_absolute()
        or not path.parts
        or ".." in path.parts
    )


def _validate_untracked_snapshot(
    *,
    root: Path,
    name: str,
    parent_descriptor: int,
    root_before: os.stat_result,
    before: os.stat_result,
    after: os.stat_result,
    content_length: int,
    unstable_gap: str,
) -> None:
    if _stat_identity(before) != _stat_identity(after) or content_length != after.st_size:
        raise ValueError(unstable_gap)
    try:
        current = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        root_current = root.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(unstable_gap) from exc
    if (
        not stat.S_ISREG(current.st_mode)
        or (current.st_dev, current.st_ino) != (after.st_dev, after.st_ino)
        or not stat.S_ISDIR(root_current.st_mode)
        or (root_current.st_dev, root_current.st_ino) != (root_before.st_dev, root_before.st_ino)
    ):
        raise ValueError(unstable_gap)


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def changed_paths(
    root: Path, *, untracked_files: Literal["all", "normal"] = "all"
) -> tuple[str, ...]:
    entries = cast(
        "list[dict[str, str]]",
        dirty_provenance(root, untracked_files=untracked_files)["entries"],
    )
    return tuple(item["path"] for item in entries)


def committed_change_paths(root: Path, base_ref: str) -> tuple[str, ...]:
    """Return committed paths changed from ``base_ref`` to ``HEAD``.

    This is intentionally separate from ``changed_paths``: a clean Work Lane can
    still carry committed product changes relative to the candidate train.
    """
    if not base_ref:
        return ()
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return ()
    return tuple(path for path in completed.stdout.splitlines() if path)


def change_scope_paths(root: Path, *, base_ref: str = "") -> tuple[str, ...]:
    """Return committed and dirty paths that define the current change scope."""
    committed = committed_change_paths(root, base_ref)
    dirty = changed_paths(root)
    return tuple(dict.fromkeys((*committed, *dirty)))


def change_scope_paths_from_status(root: Path, status_payload: dict[str, Any]) -> tuple[str, ...]:
    """Return current change-scope paths using workspace status role semantics."""
    role = str(status_payload.get("role") or "")
    role_policy = cast("dict[str, object]", status_payload.get("role_policy") or {})
    base_ref = str(role_policy.get("candidate_branch") or "") if role == "work_lane" else ""
    return change_scope_paths(root, base_ref=base_ref)


def dirty_provenance(
    root: Path, *, untracked_files: Literal["all", "normal"] = "all"
) -> dict[str, object]:
    """Structured local dirty-state provenance from Git porcelain v1.

    The old status payload only exposed path strings. Closeout repair needs the
    reason a path is dirty: tracked edit vs deletion vs untracked residue vs index
    conflict. Keep this Git-native and lightweight so it can run inside status,
    hooks, and failed-mutation diagnostics without a second state store.
    """
    try:
        output = git_stdout_checked(
            root, "status", "--porcelain", f"--untracked-files={untracked_files}"
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return _unavailable_dirty_provenance(exc)
    entries = [_dirty_entry(line) for line in output.splitlines() if line]
    summary = {
        "tracked": sum(1 for entry in entries if entry["kind"] == "tracked"),
        "untracked": sum(1 for entry in entries if entry["kind"] == "untracked"),
        "deleted": sum(1 for entry in entries if entry["kind"] == "deleted"),
        "conflicted": sum(1 for entry in entries if entry["kind"] == "conflicted"),
        "unavailable": 0,
    }
    return {
        "dirty": bool(entries),
        "state": "dirty" if entries else "clean",
        "entries": entries,
        "summary": summary,
        "temporary_probes": _temporary_probe_summary(root, entries),
    }


def _unavailable_dirty_provenance(exc: BaseException) -> dict[str, object]:
    """Build a fail-soft dirty-state payload for an unreadable Git worktree."""
    stderr = getattr(exc, "stderr", "")
    return {
        "dirty": True,
        "state": "unavailable",
        "entries": [],
        "summary": {
            "tracked": 0,
            "untracked": 0,
            "deleted": 0,
            "conflicted": 0,
            "unavailable": 1,
        },
        "temporary_probes": _empty_temporary_probe_summary(),
        "error": (stderr or str(exc)).strip(),
    }


def _dirty_entry(line: str) -> dict[str, str]:
    index = line[0] if line else " "
    worktree = line[1] if len(line) > 1 else " "
    raw_path = line[3:] if len(line) > 3 and line[2] == " " else line[2:].strip()
    path = _porcelain_path(raw_path)
    return {
        "path": path,
        "index": index,
        "worktree": worktree,
        "kind": _dirty_kind(index, worktree),
    }


def _porcelain_path(raw: str) -> str:
    # Git rename/copy porcelain uses "old -> new". The new path is what closeout
    # commands need to clean or stage.
    if " -> " in raw:
        return raw.rsplit(" -> ", 1)[1].strip('"')
    return raw.strip('"')


def _dirty_kind(index: str, worktree: str) -> str:
    if index == "?" and worktree == "?":
        return "untracked"
    if "U" in {index, worktree} or (index, worktree) in {("A", "A"), ("D", "D")}:
        return "conflicted"
    if index == "D" or worktree == "D":
        return "deleted"
    return "tracked"


def _temporary_probe_summary(root: Path, entries: list[dict[str, str]]) -> dict[str, object]:
    paths = [entry["path"] for entry in entries if _is_temporary_test_probe(root, entry)]
    return {
        "count": len(paths),
        "paths": paths[:_TEMPORARY_PROBE_PATH_LIMIT],
        "truncated": len(paths) > _TEMPORARY_PROBE_PATH_LIMIT,
    }


def _empty_temporary_probe_summary() -> dict[str, object]:
    return {"count": 0, "paths": [], "truncated": False}


def _is_temporary_test_probe(root: Path, entry: dict[str, str]) -> bool:
    if entry["kind"] != "untracked":
        return False
    relative_path = PurePosixPath(entry["path"])
    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or not relative_path.parts
        or relative_path.parts[0] != "tests"
        or relative_path.suffix != ".py"
        or not relative_path.name.startswith("test_")
    ):
        return False
    try:
        with (root / relative_path).open(encoding="utf-8", errors="replace") as source:
            header = "".join(islice(source, _TEMPORARY_PROBE_HEADER_LINES))
    except OSError:
        return False
    return _TEMPORARY_PROBE_MARKER in header
