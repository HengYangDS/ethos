"""Preserve official OpenSpec result meaning in lifecycle observations."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import NamedTuple

import ethos.adapters.openspec.lifecycle.scope as scope
from ethos.adapters.openspec.selection import selected_change
from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

_ACTIVE_STATUSES = frozenset({"in-progress", "no-tasks"})
_COMPLETED_STATUSES = frozenset({"complete"})
_KNOWN_STATUSES = _ACTIVE_STATUSES | _COMPLETED_STATUSES


class OpenSpecRequest(NamedTuple):
    change: str | None
    lifecycle: bool
    changed_paths: tuple[str, ...] = ()
    require_workspace: bool = True


class OpenSpecReportContext(NamedTuple):
    request: OpenSpecRequest
    official_config: dict[str, Any]
    official_package: str
    required_gaps: list[str]
    advisory_gaps: list[str]
    branch_intent: dict[str, object]


def official_change_rows(list_payload: dict[str, Any]) -> list[dict[str, str]] | None:
    """Validate and normalize the official active-change list."""
    changes = list_payload.get("changes")
    if not isinstance(changes, list):
        return None
    rows: list[dict[str, str]] = []
    for item in changes:
        if not isinstance(item, dict):
            return None
        name, status = item.get("name"), item.get("status")
        completed, total = item.get("completedTasks"), item.get("totalTasks")
        if (
            not isinstance(name, str)
            or not name
            or status not in _KNOWN_STATUSES
            or not isinstance(completed, int)
            or isinstance(completed, bool)
            or not isinstance(total, int)
            or isinstance(total, bool)
            or completed < 0
            or total < completed
        ):
            return None
        expected = "no-tasks" if total == 0 else "complete" if completed == total else "in-progress"
        if status != expected:
            return None
        rows.append({"name": name, "status": str(status)})
    return rows


def _validation_items(validate_payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Select exactly one supported official validation envelope."""
    if "items" in validate_payload and set(validate_payload) <= {
        "items",
        "summary",
        "version",
        "root",
    }:
        items = validate_payload["items"]
    elif "itemFindings" in validate_payload and set(validate_payload) <= {
        "report",
        "itemFindings",
        "summary",
        "root",
    }:
        report = validate_payload.get("report")
        items = validate_payload["itemFindings"]
        if not (
            isinstance(report, dict)
            and report.get("kind") == "validation-findings"
            and report.get("version") == "1.0"
            and isinstance(report.get("returnedItems"), int)
            and not isinstance(report["returnedItems"], bool)
            and isinstance(report.get("totalItems"), int)
            and not isinstance(report["totalItems"], bool)
            and 0 <= report["returnedItems"] <= report["totalItems"]
            and isinstance(items, list)
            and len(items) == report["returnedItems"]
        ):
            return None
    else:
        return None
    return items if isinstance(items, list) else None


def _valid_issue_gaps(item: dict[str, Any]) -> list[str]:
    """Keep canonical spec guidance strict without rejecting normal Change INFO."""
    issues = item.get("issues", [])
    if not isinstance(issues, list):
        return ["openspec_validation_unreadable"]
    gaps: list[str] = []
    for issue in issues:
        if (
            not isinstance(issue, dict)
            or issue.get("level") not in {"ERROR", "WARNING", "INFO"}
            or not isinstance(issue.get("path"), str)
        ):
            gaps.append("openspec_validation_unreadable")
        elif item["type"] == "spec" or issue["level"] != "INFO":
            gaps.append(
                f"openspec_validation_issue:{issue['level']}:"
                f"{item['type']}:{item['id']}:{issue['path'] or 'root'}"
            )
    return gaps


def validation_failures(validate_payload: dict[str, Any]) -> list[str]:
    """Admit native validity and issue content from one declared report envelope."""
    items = _validation_items(validate_payload)
    if items is None:
        return ["openspec_validation_unreadable"]
    gaps: list[str] = []
    for item in items:
        if not (
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and item["id"].strip()
            and item.get("type") in ("change", "spec")
            and isinstance(item.get("valid"), bool)
        ):
            gaps.append("openspec_validation_unreadable")
        elif not item["valid"]:
            gaps.append(f"openspec_validation_failed:{item['type']}:{item['id']}")
        else:
            gaps.extend(_valid_issue_gaps(item))
    return list(dict.fromkeys(gaps))


def validation_result_gaps(result: dict[str, Any]) -> list[str]:
    """Combine native validation content, exit and transport at one boundary."""
    gaps = validation_failures(result["json"])
    if result["exit_code"] != 0 and not gaps:
        gaps.append("openspec_validate_failed")
    if result["parse_error"]:
        gaps.append("openspec_validate_json_parse_failed")
    return gaps


def openspec_root_gaps(openspec_root: Path, official_config: dict[str, Any]) -> list[str]:
    return [
        *map(str, official_config["required_gaps"]),
        *(
            gap
            for path, gap in (
                (openspec_root, "openspec_directory_missing"),
                (openspec_root / "specs", "openspec_specs_missing"),
            )
            if not path.exists()
        ),
    ]


def openspec_official_cli(
    *, package: str, base_command: tuple[str, ...] | None
) -> dict[str, object]:
    return {
        "package": package,
        "available": base_command is not None,
        "base_command": list(base_command or ()),
    }


def empty_lifecycle(
    root: Path, request: OpenSpecRequest, branch_intent: dict[str, object]
) -> dict[str, Any]:
    return {
        "enabled": request.lifecycle,
        "changes": [],
        "scope_binding": scope.material_change_scope_report(
            root, changed_paths=request.changed_paths, active_change_names=()
        ),
        "branch_intent": branch_intent,
    }


def _edge_report(
    root: Path,
    context: OpenSpecReportContext,
    base_command: tuple[str, ...] | None,
    commands: dict[str, Any],
) -> dict[str, Any]:
    return {
        "verdict": "block",
        "official_config": context.official_config,
        "official_cli": openspec_official_cli(
            package=context.official_package, base_command=base_command
        ),
        "change": context.request.change,
        "schema_name": "",
        "summary": {},
        "required_gaps": context.required_gaps,
        "advisory_gaps": context.advisory_gaps,
        "commands": commands,
        "lifecycle": empty_lifecycle(root, context.request, context.branch_intent),
    }


def openspec_unavailable_report(root: Path, context: OpenSpecReportContext) -> dict[str, Any]:
    return _edge_report(root, context, None, {})


def openspec_timeout_report(
    *,
    root: Path,
    context: OpenSpecReportContext,
    base_command: tuple[str, ...],
    doctor: dict[str, Any],
) -> dict[str, Any]:
    return _edge_report(
        root, context, base_command, {"doctor": doctor, "list": {}, "status": {}, "validate": {}}
    )


def openspec_command_gaps(
    *,
    doctor: dict[str, Any],
    list_result: dict[str, Any],
    status: dict[str, Any],
    validate: dict[str, Any],
    selected: str | None,
) -> list[str]:
    gaps = [
        gap
        for blocked, gap in (
            (
                doctor["exit_code"] != 0
                or not doctor["json"].get("root", {}).get("healthy", False),
                "openspec_doctor_unhealthy",
            ),
            (list_result["exit_code"] != 0, "openspec_list_failed"),
            (status_incomplete(status, selected), f"openspec_status_incomplete:{selected}"),
        )
        if blocked
    ]
    gaps.extend(validation_result_gaps(validate))
    gaps.extend(
        f"openspec_{name}_json_parse_failed"
        for name, result in (("doctor", doctor), ("list", list_result))
        if result["parse_error"]
    )
    if status and status.get("parse_error"):
        gaps.append("openspec_status_json_parse_failed")
    return gaps


def status_incomplete(status: dict[str, Any], selected: str | None) -> bool:
    return bool(
        selected
        and (status.get("exit_code") != 0 or status.get("json", {}).get("isComplete") is False)
    )


def _capabilities(root: Path, status: dict[str, Any]) -> list[str]:
    paths = status.get("artifactPaths", {}).get("specs", {}).get("existingOutputPaths", [])
    prefix = (root / "openspec" / "changes" / str(status.get("changeName")) / "specs").resolve()
    capabilities: list[str] = []
    for value in paths if isinstance(paths, list) else ():
        try:
            relative = Path(str(value)).resolve().relative_to(prefix)
        except ValueError:
            continue
        if relative.name == "spec.md" and relative.parent.parts:
            capabilities.append(relative.parent.as_posix())
    return sorted(set(capabilities))


def _change_report(
    root: Path,
    name: str,
    status: dict[str, Any],
    apply: dict[str, Any],
) -> tuple[dict[str, object], list[str]]:
    artifacts = status.get("artifacts", [])
    gaps = [
        f"openspec_artifact_incomplete:{name}:{item.get('id')}"
        for item in artifacts
        if isinstance(item, dict) and item.get("status") not in {"done", "skipped"}
    ]
    if logical_change_identifier_issue(name):
        gaps.append(f"openspec_active_change_identifier_invalid:{name}")
    return {
        "name": name,
        "path": str(status.get("changeRoot") or f"openspec/changes/{name}"),
        "artifacts": artifacts,
        "capabilities": _capabilities(root, status),
        "progress": apply.get("progress", {}),
        "required_gaps": gaps,
    }, gaps


def lifecycle_report(
    root: Path,
    *,
    request: OpenSpecRequest,
    list_payload: dict[str, Any],
    status_payload: dict[str, Any] | None = None,
    apply_payload: dict[str, Any] | None = None,
    branch_intent: dict[str, object] | None = None,
) -> dict[str, Any]:
    intent = branch_intent or {
        "verdict": "pass",
        "records": [],
        "advisory_gaps": [],
        "required_gaps": [],
        "summary": {"change_count": 0},
    }
    if not request.lifecycle:
        lifecycle = empty_lifecycle(root, request, intent)
        lifecycle.pop("enabled")
        return {"required_gaps": [], **lifecycle}
    rows = official_change_rows(list_payload) or []
    selected = selected_change(rows, request.change, root=root)
    names = [selected] if selected else []
    changes, required_gaps = [], []
    for name in names:
        status = status_payload or {}
        apply = apply_payload or {}
        if status.get("changeName") != name:
            required_gaps.append(f"openspec_status_change_mismatch:{name}")
            continue
        if apply.get("changeName") != name:
            required_gaps.append(f"openspec_apply_change_mismatch:{name}")
            continue
        change, gaps = _change_report(root, name, status, apply)
        changes.append(change)
        required_gaps.extend(gaps)
    binding = scope.material_change_scope_report(
        root, changed_paths=request.changed_paths, active_change_names=tuple(names)
    )
    required_gaps.extend(string_sequence(binding.get("required_gaps")))
    return {
        "required_gaps": required_gaps,
        "changes": changes,
        "scope_binding": binding,
        "branch_intent": intent,
    }
