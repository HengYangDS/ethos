"""Safe inventory and cleanup for detached temporary Git worktrees."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git


def housekeeping_worktrees(
    *,
    root: Path,
    temporary_roots: tuple[Path, ...] | None = None,
    authorized: bool = False,
    apply: bool = False,
) -> dict[str, object]:
    """Inventory worktrees and remove only clean detached temporary entries."""
    repo = repo_root(root)
    roots = _temporary_roots(temporary_roots)
    entries = _inventory(repo, roots)
    if entries is None:
        return {
            "ok": False,
            "state": "blocked",
            "summary": {
                "worktree_count": 0,
                "detached_count": 0,
                "removable_count": 0,
                "protected_count": 0,
                "removed_count": 0,
            },
            "entries": [],
            "temporary_roots": [path.as_posix() for path in roots],
            "removed_paths": [],
            "required_gaps": ["housekeeping_inventory_failed"],
        }
    gaps = ["housekeeping_authorization_required"] if apply and not authorized else []
    removed: list[str] = []
    if apply and not gaps:
        for entry in entries:
            if entry["removable"] is not True:
                continue
            current = _entry(repo, Path(str(entry["path"])), roots)
            if current is None or current["removable"] is not True:
                gaps.append(f"housekeeping_candidate_stale:{entry['path']}")
                continue
            completed = run_git(
                repo,
                "worktree",
                "remove",
                str(entry["path"]),
                check=False,
            )
            if completed.returncode:
                gaps.append(f"housekeeping_remove_failed:{entry['path']}")
            else:
                removed.append(str(entry["path"]))
    summary = {
        "worktree_count": len(entries),
        "detached_count": sum(entry["detached"] is True for entry in entries),
        "removable_count": sum(entry["removable"] is True for entry in entries),
        "protected_count": sum(entry["removable"] is not True for entry in entries),
        "removed_count": len(removed),
    }
    return {
        "ok": not gaps,
        "state": "blocked"
        if gaps
        else "cleaned"
        if apply and removed
        else "ready"
        if apply
        else "planned",
        "summary": summary,
        "entries": entries,
        "temporary_roots": [path.as_posix() for path in roots],
        "removed_paths": removed,
        "required_gaps": sorted(set(gaps)),
    }


def _inventory(
    repo: Path,
    roots: tuple[Path, ...],
) -> list[dict[str, object]] | None:
    listed = run_git(repo, "worktree", "list", "--porcelain", check=False)
    if listed.returncode:
        return None
    output = listed.stdout
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in [*output.splitlines(), ""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return [
        entry
        for record in records
        if (entry := _entry_from_record(repo, record, roots)) is not None
    ]


def _entry(repo: Path, path: Path, roots: tuple[Path, ...]) -> dict[str, object] | None:
    entries = _inventory(repo, roots)
    if entries is None:
        return None
    return next(
        (entry for entry in entries if entry["path"] == path.resolve().as_posix()),
        None,
    )


def _entry_from_record(
    repo: Path,
    record: dict[str, str],
    roots: tuple[Path, ...],
) -> dict[str, object] | None:
    raw_path = record.get("worktree", "")
    if not raw_path:
        return None
    path = Path(raw_path).resolve()
    branch = record.get("branch", "").removeprefix("refs/heads/")
    detached = "detached" in record and not branch
    reasons: list[str] = []
    if branch:
        reasons.append("worktree_branch_bound")
    elif "locked" in record:
        reasons.append("worktree_locked")
    elif path == repo.resolve():
        reasons.append("worktree_is_audit_root")
    elif not path.exists():
        reasons.append("worktree_missing")
    else:
        status = run_git(path, "status", "--porcelain", check=False)
        if status.returncode:
            reasons.append("worktree_status_unavailable")
        elif status.stdout.strip():
            reasons.append("worktree_dirty")
        elif not any(_below(path, candidate) for candidate in roots):
            reasons.append("worktree_outside_temporary_roots")
    return {
        "path": path.as_posix(),
        "head": record.get("HEAD", ""),
        "branch": branch or "detached",
        "detached": detached,
        "removable": detached and not reasons,
        "reasons": reasons,
    }


def _temporary_roots(explicit: tuple[Path, ...] | None) -> tuple[Path, ...]:
    if explicit is not None:
        return tuple(path.resolve() for path in explicit)
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    candidates = (
        Path(tempfile.gettempdir()).resolve(),
        Path("/tmp").resolve(),
        (codex_home / "worktrees").resolve(),
    )
    return tuple(dict.fromkeys(candidates))


def _below(path: Path, parent: Path) -> bool:
    return path != parent and path.is_relative_to(parent)
