from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

OFFICIAL_NPX_PACKAGE = "@fission-ai/openspec"
REQUIRED_PROPOSAL_METADATA = (
    "subject",
    "reuse",
    "change",
    "facet:lifecycle",
    "facet:surface",
    "facet:authority",
)
VALID_REUSE_STANCES = {"reuse", "extend", "extract", "new"}
VALID_CHANGE_DIRECTIONS = {"add", "modify", "remove", "rename", "retire"}
ARCHIVE_NAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
CHECKBOX_PATTERN = re.compile(r"^\s*-\s+\[([ xX])]")
DELTA_HEADER_PATTERN = re.compile(r"^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements$")
ARCHIVE_METADATA_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")
REQUIRED_ARCHIVE_FILES = ("proposal.md", "design.md", "tasks.md", ".openspec.yaml")


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
            lifecycle,
            base_command,
            signature,
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


def openspec_archive_closeout_report(root: Path) -> dict[str, Any]:
    archive_root = root / "openspec" / "changes" / "archive"
    if not archive_root.is_dir():
        return {
            "ok": True,
            "state": "clean",
            "archive_root": archive_root.relative_to(root).as_posix()
            if _is_relative_to(archive_root, root)
            else archive_root.as_posix(),
            "archives": [],
            "issues": [],
            "required_gaps": [],
            "summary": {"archive_count": 0, "issue_count": 0},
        }
    archives = tuple(path for path in sorted(archive_root.iterdir()) if path.is_dir())
    issues: list[dict[str, str]] = []
    for archive in archives:
        issues.extend(_archive_closeout_issues(archive, root=root))
    required_gaps = sorted({issue["gap"] for issue in issues})
    return {
        "ok": not required_gaps,
        "state": "blocked" if required_gaps else "clean",
        "archive_root": archive_root.relative_to(root).as_posix(),
        "archives": [path.relative_to(root).as_posix() for path in archives],
        "issues": sorted(issues, key=lambda issue: (issue["gap"], issue["path"])),
        "required_gaps": required_gaps,
        "summary": {
            "archive_count": len(archives),
            "issue_count": len(issues),
        },
    }


def _archive_closeout_issues(archive: Path, *, root: Path) -> list[dict[str, str]]:
    name = archive.name
    issues: list[dict[str, str]] = []
    if not ARCHIVE_NAME_PATTERN.fullmatch(name):
        issues.append(_archive_issue("openspec_archive_name_invalid", archive, name, root=root))
    for filename in REQUIRED_ARCHIVE_FILES:
        path = archive / filename
        if not path.is_file():
            stem = "metadata" if filename == ".openspec.yaml" else path.stem
            issues.append(_archive_issue(f"openspec_archive_{stem}_missing", path, name, root=root))
    metadata = archive / ".openspec.yaml"
    if metadata.is_file():
        issues.extend(_archive_metadata_issues(metadata, archive_name=name, root=root))
    design = archive / "design.md"
    if design.is_file() and not design.read_text(encoding="utf-8").strip():
        issues.append(_archive_issue("openspec_archive_design_empty", design, name, root=root))
    tasks = archive / "tasks.md"
    if tasks.is_file():
        issues.extend(_archive_task_issues(tasks, archive_name=name, root=root))
    issues.extend(_archive_delta_issues(archive / "specs", archive_name=name, root=root))
    return issues


def _archive_metadata_issues(
    path: Path,
    *,
    archive_name: str,
    root: Path,
) -> list[dict[str, str]]:
    metadata = _read_archive_metadata(path)
    issues: list[dict[str, str]] = []
    if metadata.get("schema") != "spec-driven":
        issues.append(
            _archive_issue(
                "openspec_archive_metadata_schema_invalid",
                path,
                archive_name,
                root=root,
            )
        )
    created = metadata.get("created", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", created):
        issues.append(
            _archive_issue(
                "openspec_archive_metadata_created_invalid",
                path,
                archive_name,
                root=root,
            )
        )
    elif ARCHIVE_NAME_PATTERN.fullmatch(archive_name) and created > archive_name[:10]:
        issues.append(
            _archive_issue(
                "openspec_archive_metadata_created_after_archive",
                path,
                archive_name,
                root=root,
            )
        )
    return issues


def _read_archive_metadata(path: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ARCHIVE_METADATA_PATTERN.fullmatch(line)
        if match is not None:
            metadata[match.group(1)] = match.group(2).strip().strip("\"'")
    return metadata


def _archive_task_issues(
    path: Path,
    *,
    archive_name: str,
    root: Path,
) -> list[dict[str, str]]:
    marks = [
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := CHECKBOX_PATTERN.match(line))
    ]
    issues: list[dict[str, str]] = []
    if not marks:
        issues.append(
            _archive_issue(
                "openspec_archive_tasks_no_checkboxes",
                path,
                archive_name,
                root=root,
            )
        )
    if any(mark == " " for mark in marks):
        issues.append(
            _archive_issue(
                "openspec_archive_tasks_incomplete",
                path,
                archive_name,
                root=root,
            )
        )
    return issues


def _archive_delta_issues(
    specs_root: Path,
    *,
    archive_name: str,
    root: Path,
) -> list[dict[str, str]]:
    if not specs_root.is_dir():
        return [
            _archive_issue(
                "openspec_archive_delta_specs_missing",
                specs_root,
                archive_name,
                root=root,
            )
        ]
    spec_paths = tuple(sorted(specs_root.glob("*/spec.md")))
    if not spec_paths:
        return [
            _archive_issue(
                "openspec_archive_delta_specs_missing",
                specs_root,
                archive_name,
                root=root,
            )
        ]
    issues: list[dict[str, str]] = []
    for path in spec_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        if not any(DELTA_HEADER_PATTERN.fullmatch(line) for line in lines):
            issues.append(
                _archive_issue(
                    "openspec_archive_delta_header_missing",
                    path,
                    archive_name,
                    root=root,
                )
            )
        if not any(line.startswith("### Requirement:") for line in lines):
            issues.append(
                _archive_issue(
                    "openspec_archive_delta_requirement_missing",
                    path,
                    archive_name,
                    root=root,
                )
            )
        if not any(line.startswith("#### Scenario:") for line in lines):
            issues.append(
                _archive_issue(
                    "openspec_archive_delta_scenario_missing",
                    path,
                    archive_name,
                    root=root,
                )
            )
    return issues


def _archive_issue(code: str, path: Path, archive_name: str, *, root: Path) -> dict[str, str]:
    return {
        "archive": archive_name,
        "code": code,
        "gap": f"{code}:{archive_name}",
        "path": (
            path.relative_to(root).as_posix() if _is_relative_to(path, root) else path.as_posix()
        ),
    }


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


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
    if not (openspec_root / "config.yaml").exists():
        required_gaps.append("openspec_config_missing")
    if not (openspec_root / "specs").exists():
        required_gaps.append("openspec_specs_missing")

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
            "lifecycle": {"enabled": lifecycle, "changes": []},
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
    lifecycle_report = _lifecycle_report(
        root,
        selected_change=change,
        list_payload=list_result["json"],
        enabled=lifecycle,
    )
    required_gaps.extend(lifecycle_report["required_gaps"])

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
        "lifecycle": {
            "enabled": lifecycle,
            "changes": lifecycle_report["changes"],
        },
        "commands": {
            "doctor": doctor,
            "list": list_result,
            "status": status,
            "validate": validate,
        },
    }


def _active_claim_openspec_carriers(root: Path) -> set[str]:
    claims_dir = root / "claims"
    carriers: set[str] = set()
    for path in sorted(claims_dir.glob("*.toml")) if claims_dir.exists() else []:
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
) -> dict[str, Any]:
    if not enabled:
        return {"required_gaps": [], "changes": []}
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
        proposal_protocol = _proposal_protocol_report(root, change_name)
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
    return {"required_gaps": required_gaps, "changes": changes}


def _proposal_protocol_report(root: Path, change_name: str) -> dict[str, Any]:
    proposal = root / "openspec" / "changes" / change_name / "proposal.md"
    if not proposal.exists():
        return {"ok": True, "required_gaps": [], "capabilities": [], "out_of_scope": False}
    text = proposal.read_text(encoding="utf-8")
    gaps: list[str] = []
    out_of_scope = any(
        line.strip().casefold() in {"## out of scope", "## out-of-scope"}
        for line in text.splitlines()
    )
    if not out_of_scope:
        gaps.append(f"openspec_proposal_out_of_scope_missing:{change_name}")
    capabilities = _proposal_capability_entries(text)
    if not capabilities:
        gaps.append(f"openspec_proposal_capabilities_missing:{change_name}")
    for entry in capabilities:
        capability = entry["capability"]
        metadata = entry["metadata"]
        if not (root / "openspec" / "specs" / capability / "spec.md").exists():
            gaps.append(f"openspec_proposal_capability_unknown:{change_name}:{capability}")
        profile_gaps = _capability_profile_gaps(root, change_name, capability)
        gaps.extend(profile_gaps)
        for field in REQUIRED_PROPOSAL_METADATA:
            if not metadata.get(field):
                gaps.append(
                    f"openspec_proposal_metadata_missing:{change_name}:{capability}:{field}"
                )
        reuse = metadata.get("reuse", "")
        if reuse and reuse not in VALID_REUSE_STANCES:
            gaps.append(f"openspec_proposal_reuse_invalid:{change_name}:{capability}:{reuse}")
        direction = metadata.get("change", "")
        if direction and direction not in VALID_CHANGE_DIRECTIONS:
            gaps.append(f"openspec_proposal_change_invalid:{change_name}:{capability}:{direction}")
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "capabilities": capabilities,
        "out_of_scope": out_of_scope,
    }


def _proposal_capability_entries(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- `") and "`:" in stripped:
            if current:
                entries.append(_proposal_capability_entry(current["capability"], current["raw"]))
            capability = stripped.split("`", 2)[1]
            current = {"capability": capability, "raw": stripped.split("`:", 1)[1]}
            continue
        if current and line[:1].isspace() and not stripped.startswith("- `"):
            current["raw"] = f"{current['raw']} {stripped}"
            continue
        if current and stripped.startswith("- "):
            entries.append(_proposal_capability_entry(current["capability"], current["raw"]))
            current = None
    if current:
        entries.append(_proposal_capability_entry(current["capability"], current["raw"]))
    return entries


def _proposal_capability_entry(capability: str, raw: str) -> dict[str, Any]:
    metadata: dict[str, str] = {}
    for part in raw.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        metadata[key.strip()] = value.strip().strip("`")
    return {"capability": capability, "metadata": metadata}


def _capability_profile_gaps(root: Path, change_name: str, capability: str) -> list[str]:
    profile_path = root / "openspec" / "specs" / capability / "capability.toml"
    if not profile_path.exists():
        return [f"openspec_capability_profile_missing:{change_name}:{capability}"]
    try:
        payload = tomllib.loads(profile_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return [f"openspec_capability_profile_invalid:{change_name}:{capability}"]
    gaps: list[str] = []
    for field in ("family", "primary_invariant", "routing_question"):
        if not payload.get(field):
            gaps.append(
                f"openspec_capability_profile_field_missing:{change_name}:{capability}:{field}"
            )
    for field in ("decision_axes", "recommended_facets"):
        if not payload.get(field):
            gaps.append(
                f"openspec_capability_profile_field_missing:{change_name}:{capability}:{field}"
            )
    if not payload.get("boundary_rules"):
        gaps.append(
            f"openspec_capability_profile_field_missing:{change_name}:{capability}:boundary_rules"
        )
    owner = payload.get("owner", {})
    for field in ("package", "scope"):
        if not owner.get(field):
            gaps.append(
                f"openspec_capability_profile_field_missing:{change_name}:{capability}:owner.{field}"
            )
    proof = payload.get("proof_profile", {})
    for field in ("default_command", "executed_command", "required_gates"):
        if not proof.get(field):
            gaps.append(
                f"openspec_capability_profile_field_missing:{change_name}:{capability}:proof_profile.{field}"
            )
    return gaps
