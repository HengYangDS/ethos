from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.rstrip("\n")


def changed_paths(root: Path) -> tuple[str, ...]:
    entries = cast("list[dict[str, str]]", dirty_provenance(root)["entries"])
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


def dirty_provenance(root: Path) -> dict[str, object]:
    """Structured local dirty-state provenance from Git porcelain v1.

    The old status payload only exposed path strings. Closeout repair needs the
    reason a path is dirty: tracked edit vs deletion vs untracked residue vs index
    conflict. Keep this Git-native and lightweight so it can run inside status,
    hooks, and failed-mutation diagnostics without a second state store.
    """
    try:
        output = _run_git(root, "status", "--porcelain", "--untracked-files=all")
    except subprocess.CalledProcessError as exc:
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
            "error": (exc.stderr or str(exc)).strip(),
        }
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
