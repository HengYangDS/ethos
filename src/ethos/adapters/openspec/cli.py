"""Repository-locked OpenSpec 1.7 command and JSON contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

OFFICIAL_PACKAGE = "@fission-ai/openspec"
OFFICIAL_VERSION = "1.7.0"
OFFICIAL_PACKAGE_SPEC = f"{OFFICIAL_PACKAGE}@{OFFICIAL_VERSION}"
OPENSPEC_COMMAND_TIMEOUT_SECONDS = 60

_ROOT = Path(__file__).resolve().parents[4]
_PACKAGE = _ROOT / "node_modules" / "@fission-ai" / "openspec" / "package.json"
_ENTRY = _PACKAGE.parent / "bin" / "openspec.js"
_LOCK = _ROOT / "package-lock.json"
_NODE = shutil.which("node")


def current_branch(root: Path) -> str:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return "" if completed.returncode else completed.stdout.strip()


def openspec_base_command() -> tuple[str, ...] | None:
    """Return only the repository-locked OpenSpec entry, never a fallback."""
    command = (_NODE, _ENTRY.as_posix()) if _NODE and _ENTRY.is_file() else None
    return command if command and verify_official_cli(command)["verdict"] == "pass" else None


def verify_official_cli(command: tuple[str, ...]) -> dict[str, object]:
    """Verify package, lock, executable, and reported version as one identity."""
    gaps: list[str] = []
    package = _json_object(_PACKAGE)
    lock = _json_object(_LOCK)
    root = lock.get("packages", {}).get("", {}) if isinstance(lock.get("packages"), dict) else {}
    locked = (
        lock.get("packages", {}).get("node_modules/@fission-ai/openspec", {})
        if isinstance(lock.get("packages"), dict)
        else {}
    )
    checks = (
        (package.get("name") == OFFICIAL_PACKAGE, "openspec_package_identity_mismatch"),
        (package.get("version") == OFFICIAL_VERSION, "openspec_package_version_mismatch"),
        (
            isinstance(root, dict)
            and root.get("devDependencies", {}).get(OFFICIAL_PACKAGE) == OFFICIAL_VERSION,
            "openspec_root_pin_mismatch",
        ),
        (
            isinstance(locked, dict) and locked.get("version") == OFFICIAL_VERSION,
            "openspec_lock_version_mismatch",
        ),
        (len(command) == 2 and Path(command[1]).resolve() == _ENTRY, "openspec_entry_mismatch"),
    )
    gaps.extend(gap for valid, gap in checks if not valid)
    version = ""
    if not gaps:
        completed = subprocess.run(
            [*command, "--version"],
            cwd=_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=OPENSPEC_COMMAND_TIMEOUT_SECONDS,
        )
        version = completed.stdout.strip()
        if completed.returncode or version != OFFICIAL_VERSION:
            gaps.append("openspec_effective_version_mismatch")
    return {
        "verdict": "block" if gaps else "pass",
        "package": OFFICIAL_PACKAGE_SPEC,
        "version": version,
        "base_command": list(command),
        "required_gaps": gaps,
    }


def status_contract_gaps(payload: dict[str, Any]) -> list[str]:
    """Validate the OpenSpec 1.7 artifact dependency graph projection."""
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return ["openspec_status_artifact_graph_missing"]
    valid = all(
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("status"), str)
        and isinstance(item.get("requires"), list)
        for item in artifacts
    )
    return [] if valid else ["openspec_status_artifact_graph_invalid"]


def instructions_contract_gaps(operation: str, payload: dict[str, Any]) -> list[str]:
    """Validate official OpenSpec 1.7 apply/archive instruction projections."""
    common = isinstance(payload.get("changeName"), str) and isinstance(payload.get("root"), dict)
    if operation == "archive":
        return [] if common else ["openspec_archive_instructions_invalid"]
    apply = (
        common
        and payload.get("state") in {"blocked", "ready", "all_done"}
        and isinstance(payload.get("progress"), dict)
        and isinstance(payload.get("tasks"), list)
        and isinstance(payload.get("instruction"), str)
    )
    return [] if apply else ["openspec_apply_instructions_invalid"]


def config_contract_gaps(payload: dict[str, Any]) -> list[str]:
    """Reject machine-global root selection that can escape the repository."""
    return ["openspec_default_store_forbidden"] if payload.get("defaultStore") else []


def run_json(
    root: Path,
    base_command: tuple[str, ...],
    args: tuple[str, ...],
) -> dict[str, Any]:
    command = (*base_command, *args)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=OPENSPEC_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "command": list(command),
            "exit_code": 124,
            "stdout": stdout,
            "stderr": stderr or "openspec command timed out after 60 seconds",
            "json": {},
            "parse_error": "openspec_command_timeout",
        }
    payload: dict[str, Any] = {}
    parse_error = ""
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)
        else:
            if isinstance(parsed, dict):
                payload = parsed
            else:
                parse_error = "openspec_json_not_object"
    return {
        "command": list(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": payload,
        "parse_error": parse_error,
    }


def _json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
