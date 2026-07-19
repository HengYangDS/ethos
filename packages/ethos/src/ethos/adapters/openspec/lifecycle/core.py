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
    from pathlib import Path


class OpenSpecRequest(NamedTuple):
    """OpenSpec report request used by the cached orchestration path."""

    change: str | None
    lifecycle: bool
    changed_paths: tuple[str, ...] = ()
    require_workspace: bool = True


class OpenSpecReportContext(NamedTuple):
    """Shared context for OpenSpec governance report edge payloads."""

    request: OpenSpecRequest
    official_config: dict[str, Any]
    official_package: str
    required_gaps: list[str]
    advisory_gaps: list[str]
    protected_branch_residue: dict[str, object]


material_change_scope_report = scope.material_change_scope_report


def selected_change(list_payload: dict[str, Any], requested: str | None) -> str | None:
    """Select the OpenSpec change to inspect from list JSON and optional request."""
    selected = requested
    changes = list_payload.get("changes", [])
    if selected is None and isinstance(changes, list):
        status_groups = (
            {"in-progress"},
            {"archiving"},
            {"", "complete"},
        )
        for statuses in status_groups:
            candidates = [
                item
                for item in changes
                if isinstance(item, dict)
                and item.get("name")
                and str(item.get("status") or "") in statuses
            ]
            if candidates:
                selected = _latest_change_name(candidates)
                break
        if selected is None and len(changes) == 1 and isinstance(changes[0], dict):
            selected = str(changes[0].get("name") or "") or None
    return selected


def _latest_change_name(changes: list[dict[str, Any]]) -> str:
    """Return the deterministically latest named OpenSpec Change."""
    latest = max(
        changes,
        key=lambda item: (
            str(item.get("lastModified") or ""),
            str(item.get("name") or ""),
        ),
    )
    return str(latest["name"])


def validation_failures(validate_payload: dict[str, Any]) -> list[str]:
    """Translate OpenSpec validation JSON into ETHOS gap strings."""
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


def openspec_root_gaps(openspec_root: Path, official_config: dict[str, Any]) -> list[str]:
    """Return root-level OpenSpec substrate gaps."""
    gaps = list(official_config["required_gaps"])
    if not openspec_root.exists():
        gaps.append("openspec_directory_missing")
    if not (openspec_root / "specs").exists():
        gaps.append("openspec_specs_missing")
    return [str(gap) for gap in gaps]


def openspec_official_cli(
    *,
    package: str,
    base_command: tuple[str, ...] | None,
) -> dict[str, object]:
    """Describe official OpenSpec CLI availability."""
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
    """Return an empty lifecycle payload preserving request and residue context."""
    return {
        "enabled": request.lifecycle,
        "changes": [],
        "scope_binding": scope.material_change_scope_report(
            root,
            changed_paths=request.changed_paths,
            active_change_names=(),
        ),
        "protected_branch_residue": protected_branch_residue,
    }


def openspec_unavailable_report(root: Path, context: OpenSpecReportContext) -> dict[str, Any]:
    """Build a governance report when the official CLI is unavailable."""
    return {
        "ok": False,
        "official_config": context.official_config,
        "official_cli": openspec_official_cli(
            package=context.official_package,
            base_command=None,
        ),
        "change": context.request.change,
        "schema_name": "",
        "summary": {},
        "required_gaps": context.required_gaps,
        "advisory_gaps": context.advisory_gaps,
        "commands": {},
        "lifecycle": empty_lifecycle(root, context.request, context.protected_branch_residue),
    }


def openspec_timeout_report(
    *,
    root: Path,
    context: OpenSpecReportContext,
    base_command: tuple[str, ...],
    doctor: dict[str, Any],
) -> dict[str, Any]:
    """Build a governance report for deterministic official-CLI timeouts."""
    return {
        "ok": False,
        "official_config": context.official_config,
        "official_cli": openspec_official_cli(
            package=context.official_package,
            base_command=base_command,
        ),
        "change": context.request.change,
        "schema_name": "",
        "summary": {},
        "required_gaps": context.required_gaps,
        "advisory_gaps": context.advisory_gaps,
        "lifecycle": empty_lifecycle(root, context.request, context.protected_branch_residue),
        "commands": {"doctor": doctor, "list": {}, "status": {}, "validate": {}},
    }


def openspec_status_result(
    root: Path,
    base_command: tuple[str, ...],
    selected: str | None,
    run_json,
) -> dict[str, Any]:
    """Return official status JSON for the selected change, if any."""
    if not selected:
        return {}
    return run_json(root, base_command, ("status", "--change", selected, "--json"))


def openspec_command_gaps(
    *,
    doctor: dict[str, Any],
    list_result: dict[str, Any],
    status: dict[str, Any],
    validate: dict[str, Any],
    selected: str | None,
) -> list[str]:
    """Translate official OpenSpec command results into ETHOS gap strings."""
    gaps: list[str] = []
    if doctor["exit_code"] != 0 or not doctor["json"].get("root", {}).get("healthy", False):
        gaps.append("openspec_doctor_unhealthy")
    if list_result["exit_code"] != 0:
        gaps.append("openspec_list_failed")
    if status_incomplete(status, selected):
        gaps.append(f"openspec_status_incomplete:{selected}")
    if validate["exit_code"] != 0:
        gaps.extend(validation_failures(validate["json"]))
    for name, result in (
        ("doctor", doctor),
        ("list", list_result),
        ("validate", validate),
    ):
        if result["parse_error"]:
            gaps.append(f"openspec_{name}_json_parse_failed")
    if status and status.get("parse_error"):
        gaps.append("openspec_status_json_parse_failed")
    return gaps


def status_incomplete(status: dict[str, Any], selected: str | None) -> bool:
    """Return true when the selected OpenSpec change is not complete."""
    return bool(
        selected
        and (status.get("exit_code") != 0 or status.get("json", {}).get("isComplete") is False)
    )


def active_claim_openspec_carriers(root: Path) -> set[str]:
    """Return active claim OpenSpec carrier paths."""
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


def claim_binds_change(carriers: set[str], change_name: str) -> bool:
    """Return true when active claim carriers bind one OpenSpec change."""
    accepted = {
        change_name,
        f"openspec/changes/{change_name}",
        f"openspec/changes/{change_name}/proposal.md",
    }
    return bool(carriers & accepted)


def lifecycle_report(
    root: Path,
    *,
    request: OpenSpecRequest,
    list_payload: dict[str, Any],
    protected_branch_residue: dict[str, object] | None = None,
    base_command: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Return OpenSpec change lifecycle obligations for active changes."""
    residue = protected_branch_residue or {
        "ok": True,
        "records": [],
        "advisory_gaps": [],
        "summary": {"residue_count": 0},
    }
    if not request.lifecycle:
        return {
            "required_gaps": [],
            "changes": [],
            "scope_binding": scope.material_change_scope_report(
                root, changed_paths=request.changed_paths, active_change_names=()
            ),
            "protected_branch_residue": residue,
        }
    changes_payload = list_payload.get("changes", [])
    if request.change:
        change_names = [request.change]
    elif isinstance(changes_payload, list):
        change_names = [
            str(item.get("name"))
            for item in changes_payload
            if isinstance(item, dict)
            and item.get("name")
            and str(item.get("status") or "") in {"", "in-progress", "archiving", "complete"}
        ]
    else:
        change_names = []
    active_claim_carriers = active_claim_openspec_carriers(root)
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
            "claim_binding": claim_binds_change(active_claim_carriers, change_name),
        }
        for artifact in ("proposal", "design", "tasks", "delta_specs"):
            if not carriers[artifact]:
                required_gaps.append(f"openspec_{artifact}_missing:{change_name}")
        if not carriers["claim_binding"]:
            required_gaps.append(f"openspec_claim_binding_missing:{change_name}")
        proposal_protocol = proposal_protocol_report(root, change_name)
        required_gaps.extend(str(gap) for gap in proposal_protocol["required_gaps"])
        archive_preflight = (
            openspec_archive_preflight_report(
                root,
                change_name,
                base_command=base_command,
            )
            if base_command is not None
            else {
                "ok": True,
                "state": "not_run",
                "change": change_name,
                "isolated": True,
                "command": [],
                "diagnostics": [],
                "required_gaps": [],
            }
        )
        required_gaps.extend(str(gap) for gap in archive_preflight["required_gaps"])
        changes.append(
            {
                "name": change_name,
                "path": change_root.relative_to(root).as_posix(),
                "carriers": carriers,
                "proposal_protocol": proposal_protocol,
                "archive_preflight": archive_preflight,
                "required_gaps": [
                    gap
                    for gap in required_gaps
                    if gap.endswith(f":{change_name}") or f":{change_name}:" in gap
                ],
            }
        )
    scope_binding = scope.material_change_scope_report(
        root,
        changed_paths=request.changed_paths,
        active_change_names=tuple(change_names),
    )
    required_gaps.extend(str(gap) for gap in scope_binding["required_gaps"])
    return {
        "required_gaps": required_gaps,
        "changes": changes,
        "scope_binding": scope_binding,
        "protected_branch_residue": residue,
    }
