from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from ethos.adapters.openspec.preflight.core import openspec_archive_preflight_report
from ethos.adapters.openspec.protocol.core import proposal_protocol_report
from ethos.repository.profile import profile_root

from . import scope

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class OpenSpecRequest(NamedTuple):
    change: str | None
    lifecycle: bool
    changed_paths: tuple[str, ...] = ()


class OpenSpecReportContext(NamedTuple):
    request: OpenSpecRequest
    official_config: dict[str, Any]
    official_package: str
    required_gaps: list[str]
    advisory_gaps: list[str]
    protected_branch_residue: dict[str, object]


class OpenSpecLifecycleRuntime(NamedTuple):
    base_command: tuple[str, ...]
    run_json: Callable[[Path, tuple[str, ...], tuple[str, ...]], dict[str, object]]


material_change_scope_report = scope.material_change_scope_report


def selected_change(list_payload: dict[str, Any], requested: str | None) -> str | None:
    """Select the highest-priority, latest OpenSpec change."""
    changes = list_payload.get("changes", [])
    if requested is not None or not isinstance(changes, list):
        return requested
    for statuses in ({"in-progress"}, {"archiving"}, {"", "complete"}):
        candidates = [
            item
            for item in changes
            if isinstance(item, dict)
            and item.get("name")
            and str(item.get("status") or "") in statuses
        ]
        if candidates:
            return str(
                max(
                    candidates,
                    key=lambda item: (
                        str(item.get("lastModified") or ""),
                        str(item.get("name") or ""),
                    ),
                )["name"]
            )
    if len(changes) == 1 and isinstance(changes[0], dict):
        return str(changes[0].get("name") or "") or None
    return None


def validation_failures(validate_payload: dict[str, Any]) -> list[str]:
    """Translate OpenSpec validation JSON into ETHOS gaps."""
    items = validate_payload.get("items", [])
    if not isinstance(items, list):
        return ["openspec_validation_unreadable"]
    return [
        f"openspec_validation_failed:{item.get('type')}:{item.get('id')}"
        for item in items
        if isinstance(item, dict) and item.get("valid") is False
    ]


def openspec_root_gaps(openspec_root: Path, official_config: dict[str, Any]) -> list[str]:
    gaps = [str(gap) for gap in official_config["required_gaps"]]
    gaps.extend(
        gap
        for path, gap in (
            (openspec_root, "openspec_directory_missing"),
            (openspec_root / "specs", "openspec_specs_missing"),
        )
        if not path.exists()
    )
    return gaps


def openspec_official_cli(
    *, package: str, base_command: tuple[str, ...] | None
) -> dict[str, object]:
    return {
        "package": package,
        "available": base_command is not None,
        "base_command": list(base_command or ()),
    }


def empty_lifecycle(
    root: Path,
    request: OpenSpecRequest,
    protected_branch_residue: dict[str, object],
) -> dict[str, Any]:
    return {
        "enabled": request.lifecycle,
        "changes": [],
        "scope_binding": scope.material_change_scope_report(
            root, changed_paths=request.changed_paths, active_change_names=()
        ),
        "protected_branch_residue": protected_branch_residue,
    }


def _edge_report(
    root: Path,
    context: OpenSpecReportContext,
    base_command: tuple[str, ...] | None,
    commands: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": False,
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
        "lifecycle": empty_lifecycle(root, context.request, context.protected_branch_residue),
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
        root,
        context,
        base_command,
        {"doctor": doctor, "list": {}, "status": {}, "validate": {}},
    )


def openspec_status_result(
    root: Path, base_command: tuple[str, ...], selected: str | None, run_json
) -> dict[str, Any]:
    return (
        run_json(root, base_command, ("status", "--change", selected, "--json")) if selected else {}
    )


def openspec_command_gaps(
    *,
    doctor: dict[str, Any],
    list_result: dict[str, Any],
    status: dict[str, Any],
    validate: dict[str, Any],
    selected: str | None,
) -> list[str]:
    gaps = []
    if doctor["exit_code"] != 0 or not doctor["json"].get("root", {}).get("healthy", False):
        gaps.append("openspec_doctor_unhealthy")
    if list_result["exit_code"] != 0:
        gaps.append("openspec_list_failed")
    if status_incomplete(status, selected):
        gaps.append(f"openspec_status_incomplete:{selected}")
    if validate["exit_code"] != 0:
        gaps.extend(validation_failures(validate["json"]))
    gaps.extend(
        f"openspec_{name}_json_parse_failed"
        for name, result in (
            ("doctor", doctor),
            ("list", list_result),
            ("validate", validate),
        )
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


def active_claim_openspec_carriers(root: Path) -> set[str]:
    claims = profile_root(root, "claims")
    carriers = set()
    for path in sorted(claims.rglob("*.toml")) if claims.exists() else []:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        if payload.get("claim", {}).get("state") == "active" and (
            carrier := payload.get("carriers", {}).get("openspec", "")
        ):
            carriers.add(str(carrier))
    return carriers


def claim_binds_change(carriers: set[str], change_name: str) -> bool:
    return bool(
        carriers
        & {
            change_name,
            f"openspec/changes/{change_name}",
            f"openspec/changes/{change_name}/proposal.md",
        }
    )


def lifecycle_report(
    root: Path,
    *,
    request: OpenSpecRequest,
    list_payload: dict[str, Any],
    protected_branch_residue: dict[str, object] | None = None,
    runtime: OpenSpecLifecycleRuntime | None = None,
) -> dict[str, Any]:
    residue = protected_branch_residue or {
        "ok": True,
        "records": [],
        "advisory_gaps": [],
        "summary": {"residue_count": 0},
    }
    if not request.lifecycle:
        lifecycle = empty_lifecycle(root, request, residue)
        lifecycle.pop("enabled")
        return {"required_gaps": [], **lifecycle}
    payload = list_payload.get("changes", [])
    names = (
        [request.change]
        if request.change
        else [
            str(item["name"])
            for item in payload
            if isinstance(item, dict)
            and item.get("name")
            and str(item.get("status") or "") in {"", "in-progress", "archiving", "complete"}
        ]
        if isinstance(payload, list)
        else []
    )
    bootstrap_names = tuple(names)
    if not names and isinstance(payload, list):
        no_tasks = tuple(
            str(item["name"])
            for item in payload
            if isinstance(item, dict)
            and item.get("name")
            and str(item.get("status") or "") == "no-tasks"
        )
        bootstrap_names = no_tasks if len(no_tasks) == 1 else ()
    claim_carriers = active_claim_openspec_carriers(root)
    required_gaps: list[str] = []
    changes = []
    for name in names:
        change_root = root / "openspec" / "changes" / name
        carriers = {
            "proposal": (change_root / "proposal.md").exists(),
            "design": (change_root / "design.md").exists(),
            "tasks": (change_root / "tasks.md").exists(),
            "delta_specs": (change_root / "specs").exists()
            and any((change_root / "specs").glob("**/*.md")),
            "claim_binding": claim_binds_change(claim_carriers, name),
        }
        gaps = [
            f"openspec_{artifact}_missing:{name}" for artifact in carriers if not carriers[artifact]
        ]
        protocol = proposal_protocol_report(root, name)
        gaps.extend(map(str, protocol["required_gaps"]))
        preflight = (
            openspec_archive_preflight_report(
                root, name, base_command=runtime.base_command, run_json=runtime.run_json
            )
            if runtime
            else {
                "ok": True,
                "state": "not_run",
                "change": name,
                "isolated": True,
                "command": [],
                "diagnostics": [],
                "required_gaps": [],
            }
        )
        gaps.extend(map(str, preflight["required_gaps"]))
        required_gaps.extend(gaps)
        changes.append(
            {
                "name": name,
                "path": change_root.relative_to(root).as_posix(),
                "carriers": carriers,
                "proposal_protocol": protocol,
                "archive_preflight": preflight,
                "required_gaps": gaps,
            }
        )
    binding = scope.material_change_scope_report(
        root, changed_paths=request.changed_paths, active_change_names=bootstrap_names
    )
    required_gaps.extend(map(str, binding["required_gaps"]))
    return {
        "required_gaps": required_gaps,
        "changes": changes,
        "scope_binding": binding,
        "protected_branch_residue": residue,
    }
