from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ethos.adapters.openspec.cli import official_run_json

RunJson = Callable[[Path, tuple[str, ...], tuple[str, ...]], dict[str, object]]


def _official_run_json() -> RunJson:
    return official_run_json


def openspec_archive_preflight_report(
    root: Path,
    change_name: str,
    *,
    base_command: tuple[str, ...],
    run_json: RunJson | None = None,
) -> dict[str, Any]:
    """Run official archive against a disposable OpenSpec workspace copy."""
    run_json = run_json or _official_run_json()

    source = root / "openspec"
    command = ("archive", change_name, "--yes", "--json")
    if not source.is_dir():
        return archive_preflight_failure_report(
            change_name,
            command,
            code="workspace_missing",
            message="OpenSpec workspace is missing.",
        )
    try:
        temporary = TemporaryDirectory(prefix="ethos-openspec-archive-preflight-")
    except OSError:
        return archive_preflight_failure_report(
            change_name,
            command,
            code="isolated_workspace_unavailable",
            message="Isolated OpenSpec workspace could not be created.",
        )

    temporary_root = Path(temporary.name)
    temporary_roots = isolated_root_spellings(temporary_root)
    result: dict[str, object] | None = None
    failure: dict[str, Any] | None = None
    try:
        try:
            shutil.copytree(source, temporary_root / "openspec")
        except OSError:
            failure = archive_preflight_failure_report(
                change_name,
                command,
                code="workspace_copy_failed",
                message="OpenSpec workspace copy failed.",
            )
        else:
            try:
                result = run_json(temporary_root, base_command, command)
            except (OSError, subprocess.SubprocessError):
                failure = archive_preflight_failure_report(
                    change_name,
                    command,
                    code="official_archive_invocation_failed",
                    message="Official OpenSpec archive command could not start.",
                )
    finally:
        try:
            temporary.cleanup()
        except OSError:
            if failure is None:
                failure = archive_preflight_failure_report(
                    change_name,
                    command,
                    code="isolated_workspace_cleanup_failed",
                    message="Isolated OpenSpec workspace cleanup failed.",
                )

    if failure is not None:
        return failure
    if result is None:
        return archive_preflight_failure_report(
            change_name,
            command,
            code="official_archive_invocation_failed",
            message="Official OpenSpec archive command could not start.",
        )
    return archive_preflight_payload(
        change_name,
        command,
        result,
        temporary_roots=temporary_roots,
    )


def archive_preflight_failure_report(
    change_name: str,
    command: tuple[str, ...],
    *,
    code: str,
    message: str,
) -> dict[str, Any]:
    """Return one source-safe fail-closed preflight report."""
    return {
        "ok": False,
        "state": "blocked",
        "change": change_name,
        "isolated": True,
        "command": list(command),
        "exit_code": -1,
        "diagnostics": [{"severity": "error", "code": code, "message": message}],
        "required_gaps": [f"openspec_archive_preflight_failed:{change_name}:{code}"],
    }


def isolated_root_spellings(temporary_root: Path) -> tuple[str, ...]:
    """Return literal and resolved spellings for an isolated workspace root."""
    return tuple(dict.fromkeys((temporary_root.as_posix(), temporary_root.resolve().as_posix())))


def archive_preflight_payload(
    change_name: str,
    command: tuple[str, ...],
    result: dict[str, object],
    *,
    temporary_roots: tuple[str, ...],
) -> dict[str, Any]:
    """Project official archive JSON into source-safe lifecycle evidence."""
    payload = result.get("json")
    archive_payload = payload.get("archive") if isinstance(payload, dict) else None
    diagnostics = archive_diagnostics(payload, temporary_roots=temporary_roots)
    exit_code = result.get("exit_code")
    parse_error = str(result.get("parse_error") or "")
    failure_code = archive_preflight_failure_code(
        archive_payload=archive_payload,
        diagnostics=diagnostics,
        exit_code=exit_code,
        parse_error=parse_error,
    )
    required_gaps = (
        []
        if not failure_code
        else [f"openspec_archive_preflight_failed:{change_name}:{failure_code}"]
    )
    return {
        "ok": not required_gaps,
        "state": "ready" if not required_gaps else "blocked",
        "change": change_name,
        "isolated": True,
        "command": list(command),
        "exit_code": exit_code if isinstance(exit_code, int) else -1,
        "diagnostics": diagnostics,
        "required_gaps": required_gaps,
    }


def archive_diagnostics(
    payload: object,
    *,
    temporary_roots: tuple[str, ...],
) -> list[dict[str, str]]:
    """Return official diagnostics without isolated-workspace absolute paths."""
    if not isinstance(payload, dict):
        return []
    status = payload.get("status")
    if not isinstance(status, list):
        return []
    diagnostics: list[dict[str, str]] = []
    for item in status:
        if not isinstance(item, dict):
            continue
        diagnostic: dict[str, str] = {}
        for key in ("severity", "code", "message", "fix"):
            value = item.get(key)
            if isinstance(value, str) and value:
                diagnostic[key] = redact_isolated_root(value, temporary_roots)
        if diagnostic:
            diagnostics.append(diagnostic)
    return diagnostics


def redact_isolated_root(value: str, temporary_roots: tuple[str, ...]) -> str:
    """Replace isolated-workspace path spellings with a stable public marker."""
    redacted = value
    for temporary_root in sorted(temporary_roots, key=len, reverse=True):
        redacted = redacted.replace(temporary_root, "<isolated-openspec-root>")
    return redacted


def archive_preflight_failure_code(
    *,
    archive_payload: object,
    diagnostics: list[dict[str, str]],
    exit_code: object,
    parse_error: str,
) -> str:
    """Return one stable failure code for an official archive preflight."""
    for diagnostic in diagnostics:
        if diagnostic.get("severity") == "error" and diagnostic.get("code"):
            return diagnostic["code"]
    if parse_error == "openspec_command_timeout":
        return parse_error
    if parse_error:
        return "official_archive_json_parse_failed"
    if not isinstance(exit_code, int) or exit_code != 0:
        return "official_archive_failed"
    if not isinstance(archive_payload, dict):
        return "official_archive_result_invalid"
    return ""
