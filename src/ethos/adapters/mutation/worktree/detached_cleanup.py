"""Safe inventory and cleanup for detached temporary Git worktrees."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.contracts.verdict import close_verdict


def housekeeping_worktrees(
    *,
    root: Path,
    temporary_roots: tuple[Path, ...] | None = None,
    authorized: bool = False,
    apply: bool = False,
) -> dict[str, object]:
    """Inventory worktrees and remove only clean detached temporary entries."""
    repo, roots = repository_root(root), _temporary_roots(temporary_roots)
    entries = _inventory(repo, roots)
    if entries is None:
        return _report([], roots, [], ["housekeeping_inventory_failed"], apply=apply)
    gaps = ["authorization_required"] if apply and not authorized else []
    removed: list[str] = []
    for planned in entries if apply and not gaps else ():
        if planned["removable"] is not True:
            continue
        path, current = Path(str(planned["path"])), _entry(repo, Path(str(planned["path"])), roots)
        if (
            current is None
            or current["removable"] is not True
            or current["head"] != planned["head"]
        ):
            gaps.append(f"housekeeping_candidate_stale:{path}")
        else:
            try:
                remove_worktree(
                    repo,
                    path,
                    branch="detached",
                    head=str(planned["head"]),
                )
            except ValueError:
                gaps.append(f"housekeeping_remove_failed:{path}")
            else:
                removed.append(str(path))
    return _report(entries, roots, removed, gaps, apply=apply)


def _report(
    entries: list[dict[str, object]],
    roots: tuple[Path, ...],
    removed: list[str],
    gaps: list[str],
    *,
    apply: bool,
) -> dict[str, object]:
    summary = {
        "worktree_count": len(entries),
        "detached_count": sum(entry["detached"] is True for entry in entries),
        "removable_count": sum(entry["removable"] is True for entry in entries),
        "protected_count": sum(entry["removable"] is not True for entry in entries),
        "removed_count": len(removed),
    }
    state = "blocked" if gaps else "cleaned" if removed else "ready" if apply else "planned"
    required_gaps = sorted(set(gaps))
    next_action = (
        "ethos lane housekeeping --authorize --apply --json"
        if not required_gaps and summary["removable_count"] and not apply
        else ""
    )
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required_gaps)),
        "state": state,
        "summary": summary,
        "entries": entries,
        "temporary_roots": [path.as_posix() for path in roots],
        "removed_paths": removed,
        "required_gaps": required_gaps,
        "next_action": next_action,
    }


def _inventory(repo: Path, roots: tuple[Path, ...]) -> list[dict[str, object]] | None:
    listed = run_git(repo, "worktree", "list", "--porcelain", check=False)
    if listed.returncode:
        return None
    records = (
        dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        for block in listed.stdout.split("\n\n")
        if block.strip()
    )
    entries: list[dict[str, object]] = []
    for record in records:
        if (entry := _entry_from_record(repo, record, roots)) is None:
            return None
        entries.append(entry)
    return entries


def _entry(repo: Path, path: Path, roots: tuple[Path, ...]) -> dict[str, object] | None:
    entries = _inventory(repo, roots)
    return (
        None
        if entries is None
        else next((entry for entry in entries if entry["path"] == path.resolve().as_posix()), None)
    )


def _entry_from_record(
    repo: Path, record: dict[str, str], roots: tuple[Path, ...]
) -> dict[str, object] | None:
    if not (raw_path := record.get("worktree", "")):
        return None
    path, branch = Path(raw_path).resolve(), record.get("branch", "").removeprefix("refs/heads/")
    detached = "detached" in record and not branch
    reasons = _protection_reasons(repo, path, branch, record, roots)
    return {
        "path": path.as_posix(),
        "head": record.get("HEAD", ""),
        "branch": branch or "detached",
        "detached": detached,
        "removable": detached and not reasons,
        "reasons": reasons,
    }


def _protection_reasons(
    repo: Path, path: Path, branch: str, record: dict[str, str], roots: tuple[Path, ...]
) -> list[str]:
    structural = (
        (bool(branch), "worktree_branch_bound"),
        ("locked" in record, "worktree_locked"),
        (path == repo.resolve(), "worktree_is_audit_root"),
        (not path.exists(), "worktree_missing"),
    )
    if reason := next((code for blocked, code in structural if blocked), ""):
        return [reason]
    status = run_git(path, "status", "--porcelain", check=False)
    dynamic = (
        (bool(status.returncode), "worktree_status_unavailable"),
        (bool(status.stdout.strip()), "worktree_dirty"),
        (
            not any(path != root and path.is_relative_to(root) for root in roots),
            "worktree_outside_temporary_roots",
        ),
    )
    reason = next((code for blocked, code in dynamic if blocked), "")
    return [reason] if reason else []


def _temporary_roots(explicit: tuple[Path, ...] | None) -> tuple[Path, ...]:
    if explicit is not None:
        return tuple(path.resolve() for path in explicit)
    configured = (
        Path(value).expanduser().resolve()
        for value in os.environ.get("ETHOS_HOUSEKEEPING_ROOTS", "").split(os.pathsep)
        if value.strip()
    )
    temporary = Path(tempfile.gettempdir()).resolve()
    return tuple(
        dict.fromkeys((temporary, (Path(temporary.anchor) / "tmp").resolve(), *configured))
    )
