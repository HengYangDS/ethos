from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import cast

from ethos.adapters.openspec.archive import openspec_archive_closeout_report
from ethos.adapters.openspec.proposal import proposal_protocol_report
from ethos.repository.audit_openspec import official_config_report
from ethos.repository.audit_openspec import protected_branch_active_change_report
from ethos.repository.openspec_metadata import openspec_metadata_compatibility_report
from ethos.repository.profile import profile_root

__all__ = ["openspec_metadata_compatibility_report"]

OFFICIAL_NPX_PACKAGE = "@fission-ai/openspec"
OPENSPEC_COMMAND_TIMEOUT_SECONDS = 15


def _current_branch(root: Path) -> str:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


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
    timeout_seconds = OPENSPEC_COMMAND_TIMEOUT_SECONDS
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        if not stderr:
            stderr = f"openspec command timed out after {timeout_seconds} seconds"
        return {
            "command": list(command),
            "exit_code": 124,
            "stdout": stdout,
            "stderr": stderr,
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


def _selected_change(list_payload: dict[str, Any], requested: str | None) -> str | None:
    if requested:
        return requested
    changes = list_payload.get("changes", [])
    if not isinstance(changes, list):
        return None
    in_progress = [
        item for item in changes if isinstance(item, dict) and item.get("status") == "in-progress"
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


def openspec_governance_report(
    root: Path,
    *,
    change: str | None = None,
    lifecycle: bool = False,
) -> dict[str, Any]:
    base_command = _openspec_base_command()
    if base_command is None:
        return _openspec_governance_report(
            root,
            change=change,
            lifecycle=lifecycle,
            base_command=None,
        )
    signature = _openspec_workspace_signature(root)
    return deepcopy(
        _cached_openspec_governance_report(
            root.resolve().as_posix(),
            change,
            lifecycle=lifecycle,
            base_command=base_command,
            _signature=signature,
        )
    )


def completed_active_changes_report(root: Path) -> dict[str, Any]:
    if not (root / "openspec").exists():
        return _completed_active_changes_payload(
            root,
            completed_changes=[],
            required_gaps=[],
            list_result={},
        )
    base_command = _openspec_base_command()
    if base_command is None:
        return _completed_active_changes_payload(
            root,
            completed_changes=[],
            required_gaps=["openspec_official_cli_missing"],
            list_result={},
        )

    list_result = _run_json(root, base_command, ("list", "--json"))
    required_gaps: list[str] = []
    if list_result["exit_code"] != 0:
        required_gaps.append("openspec_list_failed")
    if list_result["parse_error"]:
        required_gaps.append("openspec_list_json_parse_failed")
    completed_changes = [] if required_gaps else _completed_active_change_names(list_result["json"])
    required_gaps.extend(
        f"openspec_completed_change_unarchived:{name}" for name in completed_changes
    )
    archive_closeout = openspec_archive_closeout_report(root)
    required_gaps.extend(archive_closeout["required_gaps"])
    return _completed_active_changes_payload(
        root,
        completed_changes=completed_changes,
        required_gaps=required_gaps,
        list_result=list_result,
        archive_closeout=archive_closeout,
    )


def _completed_active_change_names(list_payload: dict[str, Any]) -> list[str]:
    changes = list_payload.get("changes", [])
    if not isinstance(changes, list):
        return []
    completed = []
    for item in changes:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or item.get("state") or "")
        name = str(item.get("name") or item.get("id") or "")
        if name and status in {"complete", "completed", "done"}:
            completed.append(name)
    return completed


def _completed_active_changes_payload(
    root: Path,
    *,
    completed_changes: list[str],
    required_gaps: list[str],
    list_result: dict[str, Any],
    archive_closeout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": not required_gaps,
        "state": "blocked" if required_gaps else "clean",
        "root": root.as_posix(),
        "completed_changes": completed_changes,
        "archive_closeout": archive_closeout
        or {
            "ok": True,
            "state": "clean",
            "archive_root": "",
            "archives": [],
            "issues": [],
            "required_gaps": [],
            "summary": {"archive_count": 0, "issue_count": 0},
        },
        "required_gaps": required_gaps,
        "commands": {"list": list_result} if list_result else {},
    }


def _openspec_workspace_signature(root: Path) -> tuple[tuple[str, int, int], ...]:
    openspec_root = root / "openspec"
    if not openspec_root.exists():
        return ()
    signature: list[tuple[str, int, int]] = []
    for path in sorted(item for item in openspec_root.rglob("*") if item.is_file()):
        stat = path.stat()
        signature.append((path.relative_to(root).as_posix(), stat.st_mtime_ns, stat.st_size))
    return tuple(signature)


@lru_cache(maxsize=32)
def _cached_openspec_governance_report(
    root_posix: str,
    change: str | None,
    *,
    lifecycle: bool,
    base_command: tuple[str, ...],
    _signature: tuple[tuple[str, int, int], ...],
) -> dict[str, Any]:
    return _openspec_governance_report(
        Path(root_posix),
        change=change,
        lifecycle=lifecycle,
        base_command=base_command,
    )


def _openspec_governance_report(
    root: Path,
    *,
    change: str | None,
    lifecycle: bool,
    base_command: tuple[str, ...] | None,
) -> dict[str, Any]:
    openspec_root = root / "openspec"
    required_gaps: list[str] = []
    if not openspec_root.exists():
        required_gaps.append("openspec_directory_missing")
    official_config = official_config_report(root)
    required_gaps.extend(cast("list[str]", official_config["required_gaps"]))
    if not (openspec_root / "specs").exists():
        required_gaps.append("openspec_specs_missing")

    current_branch = _current_branch(root)
    protected_branch_residue = protected_branch_active_change_report(
        root, current_branch=current_branch
    )
    advisory_gaps = [
        str(gap) for gap in cast("list[object]", protected_branch_residue["advisory_gaps"])
    ]

    if base_command is None:
        required_gaps.append("openspec_official_cli_missing")
        return {
            "ok": False,
            "official_config": official_config,
            "official_cli": {
                "package": OFFICIAL_NPX_PACKAGE,
                "available": False,
                "base_command": [],
            },
            "change": change,
            "schema_name": "",
            "summary": {},
            "required_gaps": required_gaps,
            "advisory_gaps": advisory_gaps,
            "commands": {},
            "lifecycle": {
                "enabled": lifecycle,
                "changes": [],
                "protected_branch_residue": protected_branch_residue,
            },
        }

    doctor = _run_json(root, base_command, ("doctor", "--json"))
    if doctor["parse_error"] == "openspec_command_timeout":
        required_gaps.extend(["openspec_doctor_unhealthy", "openspec_doctor_json_parse_failed"])
        return {
            "ok": False,
            "official_config": official_config,
            "official_cli": {
                "package": OFFICIAL_NPX_PACKAGE,
                "available": True,
                "base_command": list(base_command),
            },
            "change": change,
            "schema_name": "",
            "summary": {},
            "required_gaps": required_gaps,
            "advisory_gaps": advisory_gaps,
            "lifecycle": {
                "enabled": lifecycle,
                "changes": [],
                "protected_branch_residue": protected_branch_residue,
            },
            "commands": {"doctor": doctor, "list": {}, "status": {}, "validate": {}},
        }
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
    lifecycle_report = _lifecycle_report(
        root,
        selected_change=change,
        list_payload=list_result["json"],
        enabled=lifecycle,
        protected_branch_residue=protected_branch_residue,
    )
    required_gaps.extend(lifecycle_report["required_gaps"])

    return {
        "ok": not required_gaps,
        "official_config": official_config,
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
        "advisory_gaps": advisory_gaps,
        "lifecycle": {
            "enabled": lifecycle,
            "changes": lifecycle_report["changes"],
            "protected_branch_residue": lifecycle_report["protected_branch_residue"],
        },
        "commands": {
            "doctor": doctor,
            "list": list_result,
            "status": status,
            "validate": validate,
        },
    }


def _active_claim_openspec_carriers(root: Path) -> set[str]:
    claims_dir = profile_root(root, "claims")
    carriers: set[str] = set()
    for path in sorted(claims_dir.rglob("*.toml")) if claims_dir.exists() else []:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        claim = payload.get("claim", {})
        if claim.get("state") != "active":
            continue
        carrier = payload.get("carriers", {}).get("openspec", "")
        if carrier:
            carriers.add(str(carrier))
    return carriers


def _claim_binds_change(carriers: set[str], change_name: str) -> bool:
    accepted = {
        change_name,
        f"openspec/changes/{change_name}",
        f"openspec/changes/{change_name}/proposal.md",
    }
    return bool(carriers & accepted)


def _lifecycle_report(
    root: Path,
    *,
    selected_change: str | None,
    list_payload: dict[str, Any],
    enabled: bool,
    protected_branch_residue: dict[str, object] | None = None,
) -> dict[str, Any]:
    residue = protected_branch_residue or {
        "ok": True,
        "records": [],
        "advisory_gaps": [],
        "summary": {"residue_count": 0},
    }
    if not enabled:
        return {
            "required_gaps": [],
            "changes": [],
            "protected_branch_residue": residue,
        }
    changes_payload = list_payload.get("changes", [])
    if selected_change:
        change_names = [selected_change]
    elif isinstance(changes_payload, list):
        change_names = [
            str(item.get("name"))
            for item in changes_payload
            if isinstance(item, dict) and item.get("name")
        ]
    else:
        change_names = []

    active_claim_carriers = _active_claim_openspec_carriers(root)
    required_gaps: list[str] = []
    changes: list[dict[str, Any]] = []
    for change_name in change_names:
        change_root = root / "openspec" / "changes" / change_name
        carriers = {
            "proposal": (change_root / "proposal.md").exists(),
            "design": (change_root / "design.md").exists(),
            "tasks": (change_root / "tasks.md").exists(),
            "delta_specs": any((change_root / "specs").glob("**/*.md"))
            if (change_root / "specs").exists()
            else False,
            "claim_binding": _claim_binds_change(active_claim_carriers, change_name),
        }
        for artifact in ("proposal", "design", "tasks", "delta_specs"):
            if not carriers[artifact]:
                required_gaps.append(f"openspec_{artifact}_missing:{change_name}")
        if not carriers["claim_binding"]:
            required_gaps.append(f"openspec_claim_binding_missing:{change_name}")
        proposal_protocol = proposal_protocol_report(root, change_name)
        required_gaps.extend(proposal_protocol["required_gaps"])
        changes.append(
            {
                "name": change_name,
                "path": change_root.relative_to(root).as_posix(),
                "carriers": carriers,
                "proposal_protocol": proposal_protocol,
                "required_gaps": [
                    gap
                    for gap in required_gaps
                    if gap.endswith(f":{change_name}") or f":{change_name}:" in gap
                ],
            }
        )
    return {
        "required_gaps": required_gaps,
        "changes": changes,
        "protected_branch_residue": residue,
    }
