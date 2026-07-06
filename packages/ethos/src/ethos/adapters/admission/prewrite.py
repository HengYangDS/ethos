from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.adapters.repo.status import workspace_status
from ethos_core.contracts.branch_roles import PROTECTED_WRITE_ROLES


def prewrite_guard(
    *,
    root: Path,
    paths: list[Path],
    editor_root: Path | None = None,
    require_editor_root: bool = False,
) -> dict[str, object]:
    status = workspace_status(root)
    role = str(status["role"])
    runtime_check = _runtime_binding_check(status)
    checked_paths = [_check_path(root=root, path=path, role=role) for path in paths]
    tracked_write_requested = any(path["tracked_candidate"] for path in checked_paths)
    editor_check = _editor_root_check(
        root=root,
        editor_root=editor_root,
        require_editor_root=require_editor_root or tracked_write_requested,
    )
    blocked_paths = [path for path in checked_paths if path["allowed"] is False]
    error = _error(
        runtime_check=runtime_check,
        editor_check=editor_check,
        blocked_paths=blocked_paths,
    )
    return {
        "ok": error == "",
        "error": error,
        "role": role,
        "branch": status["branch"],
        "runtime_binding": runtime_check,
        "editor_root": editor_check,
        "paths": checked_paths,
        "blocked_paths": blocked_paths,
        "required_gaps": [error] if error else [],
    }


def _runtime_binding_check(status: dict[str, object]) -> dict[str, object]:
    binding = status.get("runtime_binding")
    if not isinstance(binding, dict):
        return {
            "ok": True,
            "reason": "runtime_binding_unavailable",
            "audit_root": "",
            "runner_source_root": "",
            "schema_source_root": "",
            "product_audit_root": False,
        }
    audit_root = str(binding.get("audit_root") or "")
    runner_source_root = str(binding.get("runner_source_root") or "")
    schema_source_root = str(binding.get("schema_source_root") or "")
    product_audit_root = (
        bool(audit_root)
        and (Path(audit_root) / "packages" / "ethos" / "src" / "ethos" / "__init__.py").exists()
    )
    runner_matches = binding.get("runner_matches_audit_root") is True
    schema_matches = binding.get("schema_matches_audit_root") is True
    ok = (not product_audit_root) or (runner_matches and schema_matches)
    reason = "matched" if ok else "root_binding_mismatch"
    return {
        "ok": ok,
        "reason": reason,
        "audit_root": audit_root,
        "runner_source_root": runner_source_root,
        "schema_source_root": schema_source_root,
        "product_audit_root": product_audit_root,
        "runner_matches_audit_root": runner_matches,
        "schema_matches_audit_root": schema_matches,
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
    runtime_check: dict[str, object],
    editor_check: dict[str, object],
    blocked_paths: list[dict[str, object]],
) -> str:
    if runtime_check["ok"] is not True:
        return str(runtime_check["reason"])
    if any(path["reason"] == "path_outside_worktree" for path in blocked_paths):
        return "prewrite_path_outside_worktree"
    if blocked_paths:
        return "protected_lane_prewrite_blocked"
    if editor_check["ok"] is not True:
        return str(editor_check["reason"])
    return ""
