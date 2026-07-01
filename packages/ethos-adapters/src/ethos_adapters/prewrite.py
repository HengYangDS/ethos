from __future__ import annotations

import subprocess
from pathlib import Path

from ethos_adapters.status import workspace_status

PROTECTED_WRITE_ROLES = frozenset({"accepted_root", "candidate", "submit", "detached", "other"})


def prewrite_guard(
    *,
    root: Path,
    paths: list[Path],
    editor_root: Path | None = None,
    require_editor_root: bool = False,
) -> dict[str, object]:
    status = workspace_status(root)
    role = str(status["role"])
    checked_paths = [_check_path(root=root, path=path, role=role) for path in paths]
    tracked_write_requested = any(path["tracked_candidate"] for path in checked_paths)
    editor_check = _editor_root_check(
        root=root,
        editor_root=editor_root,
        require_editor_root=require_editor_root or tracked_write_requested,
    )
    blocked_paths = [path for path in checked_paths if path["allowed"] is False]
    error = _error(editor_check=editor_check, blocked_paths=blocked_paths)
    return {
        "ok": error == "",
        "error": error,
        "role": role,
        "branch": status["branch"],
        "editor_root": editor_check,
        "paths": checked_paths,
        "blocked_paths": blocked_paths,
        "required_gaps": [error] if error else [],
    }


def _editor_root_check(
    *,
    root: Path,
    editor_root: Path | None,
    require_editor_root: bool,
) -> dict[str, object]:
    expected = root.resolve()
    if editor_root is None:
        return {
            "ok": not require_editor_root,
            "required": require_editor_root,
            "expected": expected.as_posix(),
            "actual": "",
            "reason": "editor_root_missing" if require_editor_root else "not_checked",
        }
    actual = editor_root.resolve()
    return {
        "ok": actual == expected,
        "required": require_editor_root,
        "expected": expected.as_posix(),
        "actual": actual.as_posix(),
        "reason": "matched" if actual == expected else "editor_root_mismatch",
    }


def _check_path(*, root: Path, path: Path, role: str) -> dict[str, object]:
    root_path = root.resolve()
    resolved = (path if path.is_absolute() else root_path / path).resolve()
    try:
        relative_path = resolved.relative_to(root_path).as_posix()
    except ValueError:
        return {
            "path": resolved.as_posix(),
            "relative_path": "",
            "ignored": False,
            "tracked_candidate": False,
            "allowed": False,
            "reason": "path_outside_worktree",
        }
    ignored = _is_ignored(root_path, relative_path)
    tracked_candidate = not ignored
    protected = role in PROTECTED_WRITE_ROLES and tracked_candidate
    return {
        "path": resolved.as_posix(),
        "relative_path": relative_path,
        "ignored": ignored,
        "tracked_candidate": tracked_candidate,
        "allowed": not protected,
        "reason": "protected_lane_tracked_write" if protected else "allowed",
    }


def _is_ignored(root: Path, relative_path: str) -> bool:
    completed = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative_path],
        cwd=root,
        check=False,
    )
    return completed.returncode == 0


def _error(
    *,
    editor_check: dict[str, object],
    blocked_paths: list[dict[str, object]],
) -> str:
    if any(path["reason"] == "path_outside_worktree" for path in blocked_paths):
        return "prewrite_path_outside_worktree"
    if blocked_paths:
        return "protected_lane_prewrite_blocked"
    if editor_check["ok"] is not True:
        return str(editor_check["reason"])
    return ""
