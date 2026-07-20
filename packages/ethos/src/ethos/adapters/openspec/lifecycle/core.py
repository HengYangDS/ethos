from __future__ import annotations

# ruff: noqa: E501 - source-budget closeout keeps equivalent lifecycle envelopes compact.
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

# fmt: off

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
    protected_branch_residue: dict[str, object]

material_change_scope_report = scope.material_change_scope_report


def selected_change(list_payload: dict[str, Any], requested: str | None) -> str | None:
    """Select the highest-priority, latest OpenSpec change."""
    changes = list_payload.get("changes", [])
    if requested is not None or not isinstance(changes, list):
        return requested
    for statuses in ({"in-progress"}, {"archiving"}, {"", "complete"}):
        candidates = [item for item in changes if isinstance(item, dict) and item.get("name") and str(item.get("status") or "") in statuses]
        if candidates:
            return str(max(candidates, key=lambda item: (str(item.get("lastModified") or ""), str(item.get("name") or "")))["name"])
    return str(changes[0].get("name") or "") or None if len(changes) == 1 and isinstance(changes[0], dict) else None


def validation_failures(validate_payload: dict[str, Any]) -> list[str]:
    """Translate OpenSpec validation JSON into ETHOS gaps."""
    items = validate_payload.get("items", [])
    return [f"openspec_validation_failed:{item.get('type')}:{item.get('id')}" for item in items if isinstance(item, dict) and item.get("valid") is False] if isinstance(items, list) else ["openspec_validation_unreadable"]


def openspec_root_gaps(openspec_root: Path, official_config: dict[str, Any]) -> list[str]:
    return [*map(str, official_config["required_gaps"]), *(gap for path, gap in ((openspec_root, "openspec_directory_missing"), (openspec_root / "specs", "openspec_specs_missing")) if not path.exists())]


def openspec_official_cli(*, package: str, base_command: tuple[str, ...] | None) -> dict[str, object]:
    return {"package": package, "available": base_command is not None, "base_command": list(base_command or ())}


def empty_lifecycle(root: Path, request: OpenSpecRequest, protected_branch_residue: dict[str, object]) -> dict[str, Any]:
    return {"enabled": request.lifecycle, "changes": [], "scope_binding": scope.material_change_scope_report(root, changed_paths=request.changed_paths, active_change_names=()), "protected_branch_residue": protected_branch_residue}


def _edge_report(root: Path, context: OpenSpecReportContext, base_command: tuple[str, ...] | None, commands: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False, "official_config": context.official_config,
        "official_cli": openspec_official_cli(package=context.official_package, base_command=base_command),
        "change": context.request.change, "schema_name": "", "summary": {},
        "required_gaps": context.required_gaps, "advisory_gaps": context.advisory_gaps,
        "commands": commands, "lifecycle": empty_lifecycle(root, context.request, context.protected_branch_residue),
    }


def openspec_unavailable_report(root: Path, context: OpenSpecReportContext) -> dict[str, Any]:
    return _edge_report(root, context, None, {})


def openspec_timeout_report(*, root: Path, context: OpenSpecReportContext, base_command: tuple[str, ...], doctor: dict[str, Any]) -> dict[str, Any]:
    return _edge_report(root, context, base_command, {"doctor": doctor, "list": {}, "status": {}, "validate": {}})


def openspec_status_result(root: Path, base_command: tuple[str, ...], selected: str | None, run_json) -> dict[str, Any]:
    return run_json(root, base_command, ("status", "--change", selected, "--json")) if selected else {}


def openspec_command_gaps(*, doctor: dict[str, Any], list_result: dict[str, Any], status: dict[str, Any], validate: dict[str, Any], selected: str | None) -> list[str]:
    gaps = [gap for blocked, gap in (
        (doctor["exit_code"] != 0 or not doctor["json"].get("root", {}).get("healthy", False), "openspec_doctor_unhealthy"),
        (list_result["exit_code"] != 0, "openspec_list_failed"),
        (status_incomplete(status, selected), f"openspec_status_incomplete:{selected}"),
    ) if blocked]
    if validate["exit_code"] != 0:
        gaps.extend(validation_failures(validate["json"]))
    gaps.extend(f"openspec_{name}_json_parse_failed" for name, result in (("doctor", doctor), ("list", list_result), ("validate", validate)) if result["parse_error"])
    if status and status.get("parse_error"):
        gaps.append("openspec_status_json_parse_failed")
    return gaps


def status_incomplete(status: dict[str, Any], selected: str | None) -> bool:
    return bool(selected and (status.get("exit_code") != 0 or status.get("json", {}).get("isComplete") is False))


def active_claim_openspec_carriers(root: Path) -> set[str]:
    claims = profile_root(root, "claims")
    carriers = set()
    for path in sorted(claims.rglob("*.toml")) if claims.exists() else []:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        if payload.get("claim", {}).get("state") == "active" and (carrier := payload.get("carriers", {}).get("openspec", "")):
            carriers.add(str(carrier))
    return carriers


def claim_binds_change(carriers: set[str], change_name: str) -> bool:
    return bool(carriers & {change_name, f"openspec/changes/{change_name}", f"openspec/changes/{change_name}/proposal.md"})


def _lifecycle_names(payload: object, requested: str | None) -> tuple[list[str], tuple[str, ...]]:
    if requested:
        return [requested], (requested,)
    names = [str(item.get("name")) for item in payload if isinstance(item, dict) and item.get("name") and str(item.get("status") or "") in {"", "in-progress", "archiving", "complete"}] if isinstance(payload, list) else []
    return names, tuple(names)


def _change_report(root: Path, name: str, claim_carriers: set[str], base_command: tuple[str, ...] | None) -> tuple[dict[str, object], list[str]]:
    change_root = root / "openspec" / "changes" / name
    carriers = {
        "proposal": (change_root / "proposal.md").exists(), "design": (change_root / "design.md").exists(),
        "tasks": (change_root / "tasks.md").exists(),
        "delta_specs": (change_root / "specs").exists() and any((change_root / "specs").glob("**/*.md")),
        "claim_binding": claim_binds_change(claim_carriers, name),
    }
    gaps = [f"openspec_{artifact}_missing:{name}" for artifact, present in carriers.items() if not present]
    protocol = proposal_protocol_report(root, name)
    gaps.extend(map(str, protocol["required_gaps"]))
    preflight = openspec_archive_preflight_report(root, name, base_command=base_command) if base_command is not None else {"ok": True, "state": "not_run", "change": name, "isolated": True, "command": [], "diagnostics": [], "required_gaps": []}
    gaps.extend(map(str, preflight["required_gaps"]))
    return {"name": name, "path": change_root.relative_to(root).as_posix(), "carriers": carriers, "proposal_protocol": protocol, "archive_preflight": preflight, "required_gaps": gaps}, gaps


def lifecycle_report(root: Path, *, request: OpenSpecRequest, list_payload: dict[str, Any], protected_branch_residue: dict[str, object] | None = None, base_command: tuple[str, ...] | None = None) -> dict[str, Any]:
    residue = protected_branch_residue or {"ok": True, "records": [], "advisory_gaps": [], "summary": {"residue_count": 0}}
    if not request.lifecycle:
        lifecycle = empty_lifecycle(root, request, residue)
        lifecycle.pop("enabled")
        return {"required_gaps": [], **lifecycle}
    names, active_names = _lifecycle_names(list_payload.get("changes", []), request.change)
    claim_carriers = active_claim_openspec_carriers(root)
    changes, required_gaps = [], []
    for name in names:
        change, gaps = _change_report(root, name, claim_carriers, base_command)
        changes.append(change)
        required_gaps.extend(gaps)
    binding = scope.material_change_scope_report(root, changed_paths=request.changed_paths, active_change_names=active_names)
    required_gaps.extend(map(str, binding["required_gaps"]))
    return {"required_gaps": required_gaps, "changes": changes, "scope_binding": binding, "protected_branch_residue": residue}
