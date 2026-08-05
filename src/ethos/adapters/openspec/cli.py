"""Repository-locked OpenSpec 1.7 command and JSON contracts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from importlib import resources
from pathlib import Path
from typing import Any

from ethos.adapters.repo.git import run_command

OFFICIAL_PACKAGE = "@fission-ai/openspec"
OFFICIAL_VERSION = "1.7.0"
OFFICIAL_PACKAGE_SPEC = f"{OFFICIAL_PACKAGE}@{OFFICIAL_VERSION}"
OPENSPEC_COMMAND_TIMEOUT_SECONDS = 60
_SOURCE_COMMAND_LENGTH = 2

_SOURCE_ROOT = Path(__file__).resolve().parents[4]
_PACKAGE = _SOURCE_ROOT / "node_modules" / "@fission-ai" / "openspec" / "package.json"
_ENTRY = _PACKAGE.parent / "bin" / "openspec.js"
_LOCK = _SOURCE_ROOT / "package-lock.json"
_SOURCE_NODE = shutil.which("node")
_GIT = shutil.which("git") or "/usr/bin/git"


def current_branch(root: Path) -> str:
    completed = run_command(
        root,
        (_GIT, "branch", "--show-current"),
        text=True,
        capture_output=True,
        check=False,
    )
    return "" if completed.returncode else completed.stdout.strip()


def openspec_base_command() -> tuple[str, ...] | None:
    """Return only the source-locked or installed exact OpenSpec command."""
    source = (_SOURCE_NODE, _ENTRY.as_posix()) if _SOURCE_NODE and _ENTRY.is_file() else None
    if source and verify_official_cli(source)["verdict"] == "pass":
        return source
    installed = shutil.which("openspec")
    command = (installed,) if installed else None
    return command if command and verify_official_cli(command)["verdict"] == "pass" else None


def verify_official_cli(command: tuple[str, ...]) -> dict[str, object]:
    """Verify package, lock, executable, and reported version as one identity."""
    gaps: list[str] = []
    source_entry = len(command) == _SOURCE_COMMAND_LENGTH and Path(command[1]).resolve() == _ENTRY
    if source_entry:
        package = _json_object(_PACKAGE)
        lock = _json_object(_LOCK)
        packages = lock.get("packages")
        packages = packages if isinstance(packages, dict) else {}
        root = packages.get("", {})
        locked = packages.get("node_modules/@fission-ai/openspec", {})
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
        )
    else:
        declaration = _json_object(
            Path(str(resources.files("ethos").joinpath("data", "openspec", "package.json")))
        )
        executable = Path(command[0]).resolve() if len(command) == 1 else Path()
        package = _nearest_package(executable)
        checks = (
            (len(command) == 1, "openspec_entry_mismatch"),
            (package.get("name") == OFFICIAL_PACKAGE, "openspec_package_identity_mismatch"),
            (package.get("version") == OFFICIAL_VERSION, "openspec_package_version_mismatch"),
            (
                declaration.get("dependencies", {}).get(OFFICIAL_PACKAGE) == OFFICIAL_VERSION,
                "openspec_distribution_pin_mismatch",
            ),
        )
    gaps.extend(gap for valid, gap in checks if not valid)
    version = ""
    if not gaps:
        completed = run_command(
            _SOURCE_ROOT if source_entry else Path.cwd(),
            (*command, "--version"),
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
        completed = run_command(
            root,
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=OPENSPEC_COMMAND_TIMEOUT_SECONDS,
            env={"PATH": os.environ.get("PATH", os.defpath)},
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


def _nearest_package(executable: Path) -> dict[str, Any]:
    for parent in executable.parents:
        package = _json_object(parent / "package.json")
        if package.get("name") == OFFICIAL_PACKAGE:
            return package
    return {}
