from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

OFFICIAL_NPX_PACKAGE = "@fission-ai/openspec"


def _openspec_base_command() -> tuple[str, ...] | None:
    if shutil.which("openspec"):
        return ("openspec",)
    if shutil.which("npx"):
        return ("npx", "--yes", OFFICIAL_NPX_PACKAGE)
    return None


def _run_json(
    root: Path,
    base_command: tuple[str, ...],
    args: tuple[str, ...],
) -> dict[str, Any]:
    command = (*base_command, *args)
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
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


def _selected_change(list_payload: dict[str, Any], requested: str | None) -> str | None:
    if requested:
        return requested
    changes = list_payload.get("changes", [])
    if not isinstance(changes, list):
        return None
    in_progress = [
        item
        for item in changes
        if isinstance(item, dict) and item.get("status") == "in-progress"
    ]
    if in_progress:
        return str(in_progress[0].get("name") or "")
    if len(changes) == 1 and isinstance(changes[0], dict):
        return str(changes[0].get("name") or "")
    complete = [item for item in changes if isinstance(item, dict) and item.get("name")]
    if complete:
        latest = max(complete, key=lambda item: str(item.get("lastModified") or ""))
        return str(latest.get("name") or "")
    return None


def _validation_failures(validate_payload: dict[str, Any]) -> list[str]:
    items = validate_payload.get("items", [])
    if not isinstance(items, list):
        return ["openspec_validation_unreadable"]
    failures = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("valid") is False:
            failures.append(f"openspec_validation_failed:{item.get('type')}:{item.get('id')}")
    return failures


def openspec_self_governance_report(root: Path, *, change: str | None = None) -> dict[str, Any]:
    openspec_root = root / "openspec"
    required_gaps: list[str] = []
    if not openspec_root.exists():
        required_gaps.append("openspec_directory_missing")
    if not (openspec_root / "config.yaml").exists():
        required_gaps.append("openspec_config_missing")
    if not (openspec_root / "specs").exists():
        required_gaps.append("openspec_specs_missing")

    base_command = _openspec_base_command()
    if base_command is None:
        required_gaps.append("openspec_official_cli_missing")
        return {
            "ok": False,
            "official_cli": {
                "package": OFFICIAL_NPX_PACKAGE,
                "available": False,
                "base_command": [],
            },
            "change": change,
            "schema_name": "",
            "summary": {},
            "required_gaps": required_gaps,
            "commands": {},
        }

    doctor = _run_json(root, base_command, ("doctor", "--json"))
    list_result = _run_json(root, base_command, ("list", "--json"))
    selected_change = _selected_change(list_result["json"], change)
    status = (
        _run_json(root, base_command, ("status", "--change", selected_change, "--json"))
        if selected_change
        else {}
    )
    validate = _run_json(root, base_command, ("validate", "--all", "--strict", "--json"))

    if doctor["exit_code"] != 0 or not doctor["json"].get("root", {}).get("healthy", False):
        required_gaps.append("openspec_doctor_unhealthy")
    if list_result["exit_code"] != 0:
        required_gaps.append("openspec_list_failed")
    if selected_change and (
        status.get("exit_code") != 0 or status.get("json", {}).get("isComplete") is False
    ):
        required_gaps.append(f"openspec_status_incomplete:{selected_change}")
    if validate["exit_code"] != 0:
        required_gaps.extend(_validation_failures(validate["json"]))
    for name, result in (("doctor", doctor), ("list", list_result), ("validate", validate)):
        if result["parse_error"]:
            required_gaps.append(f"openspec_{name}_json_parse_failed")
    if status and status.get("parse_error"):
        required_gaps.append("openspec_status_json_parse_failed")

    return {
        "ok": not required_gaps,
        "official_cli": {
            "package": OFFICIAL_NPX_PACKAGE,
            "available": True,
            "base_command": list(base_command),
        },
        "change": selected_change,
        "schema_name": status.get("json", {}).get("schemaName") if status else "",
        "summary": {
            "change_count": len(list_result["json"].get("changes", [])),
            "validation": validate["json"].get("summary", {}),
        },
        "required_gaps": required_gaps,
        "commands": {
            "doctor": doctor,
            "list": list_result,
            "status": status,
            "validate": validate,
        },
    }
