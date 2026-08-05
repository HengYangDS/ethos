from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.lifecycle.archive_transition import lease_bound_archive_scope_report
from ethos.adapters.openspec.lifecycle.report import OpenSpecReportContext
from ethos.adapters.openspec.lifecycle.report import OpenSpecRequest
from ethos.adapters.openspec.lifecycle.report import lifecycle_report
from ethos.adapters.openspec.lifecycle.report import official_change_rows
from ethos.adapters.openspec.lifecycle.report import openspec_command_gaps
from ethos.adapters.openspec.lifecycle.report import openspec_official_cli
from ethos.adapters.openspec.lifecycle.report import openspec_root_gaps
from ethos.adapters.openspec.lifecycle.report import openspec_status_result
from ethos.adapters.openspec.lifecycle.report import openspec_timeout_report
from ethos.adapters.openspec.lifecycle.report import openspec_unavailable_report
from ethos.adapters.openspec.lifecycle.report import selected_change
from ethos.adapters.openspec.lifecycle.report import selection_gaps
from ethos.repository.openspec.audit import official_config_report
from ethos.repository.openspec.audit import protected_branch_active_change_report
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from typing import Any


def openspec_governance_report(
    root: Path,
    *,
    change: str | None = None,
    lifecycle: bool = False,
    changed_paths: tuple[str, ...] = (),
    require_workspace: bool = True,
) -> dict[str, Any]:
    """Return the ETHOS OpenSpec governance report for one repository root."""
    if not openspec_profile_enabled(root):
        request = OpenSpecRequest(change, lifecycle, changed_paths, require_workspace)
        report = lifecycle_report(root, request=request, list_payload={})
        return {
            "verdict": "pass",
            "state": "not_applicable",
            "official_config": {},
            "official_cli": {"available": False, "base_command": []},
            "change": None,
            "schema_name": "",
            "summary": {"change_count": 0, "validation": {}},
            "required_gaps": [],
            "advisory_gaps": [],
            "lifecycle": {
                "enabled": lifecycle,
                "changes": report["changes"],
                "scope_binding": report["scope_binding"],
                "protected_branch_residue": report["protected_branch_residue"],
            },
            "commands": {},
        }
    archive = root / "openspec" / "changes" / "archive" / (change or "")
    active_identifier_gaps = (
        [f"openspec_active_change_identifier_is_archive_directory:{change}"]
        if change and archive.is_dir()
        else [f"openspec_active_change_identifier_invalid:{change}"]
        if change and logical_change_identifier_issue(change)
        else []
    )
    if active_identifier_gaps:
        return _active_identifier_rejected_report(
            root,
            change=change,
            lifecycle=lifecycle,
            required_gaps=active_identifier_gaps,
        )
    request = OpenSpecRequest(change, lifecycle, changed_paths, require_workspace)
    base_command = openspec_cli.openspec_base_command()
    if base_command is None:
        return _openspec_governance_report(
            root,
            request=request,
            base_command=None,
        )
    return _openspec_governance_report(
        root,
        request=request,
        base_command=base_command,
    )


def _active_identifier_rejected_report(
    root: Path,
    *,
    change: str | None,
    lifecycle: bool,
    required_gaps: list[str],
) -> dict[str, Any]:
    """Return an active-selector category error without invoking official status."""
    return {
        "verdict": "block",
        "official_config": official_config_report(root),
        "official_cli": {
            "package": openspec_cli.OFFICIAL_PACKAGE_SPEC,
            "available": False,
            "base_command": [],
        },
        "change": change,
        "schema_name": "",
        "summary": {"change_count": 0, "validation": {}},
        "required_gaps": required_gaps,
        "advisory_gaps": [],
        "lifecycle": {
            "enabled": lifecycle,
            "changes": [],
            "scope_binding": {},
            "protected_branch_residue": {},
        },
        "commands": {"doctor": {}, "list": {}, "status": {}, "validate": {}},
    }


def _openspec_governance_report(
    root: Path,
    *,
    request: OpenSpecRequest,
    base_command: tuple[str, ...] | None,
) -> dict[str, Any]:
    openspec_root = root / "openspec"
    official_config = official_config_report(root)
    current_branch = openspec_cli.current_branch(root)
    protected_branch_residue = protected_branch_active_change_report(
        root,
        current_branch=current_branch,
    )
    advisory_gaps = [
        str(gap) for gap in cast("list[object]", protected_branch_residue["advisory_gaps"])
    ]
    scope_binding = lifecycle_report(
        root,
        request=request._replace(lifecycle=False),
        list_payload={},
        protected_branch_residue=protected_branch_residue,
    )["scope_binding"]
    if (
        not request.require_workspace
        and request.change is None
        and not openspec_root.exists()
        and scope_binding["state"] == "no_material_paths"
    ):
        return {
            "verdict": "pass",
            "state": "not_applicable",
            "official_config": official_config,
            "official_cli": openspec_official_cli(
                package=openspec_cli.OFFICIAL_PACKAGE_SPEC,
                base_command=base_command,
            ),
            "change": None,
            "schema_name": "",
            "summary": {"change_count": 0, "validation": {}},
            "required_gaps": [],
            "advisory_gaps": advisory_gaps,
            "lifecycle": {
                "enabled": request.lifecycle,
                "changes": [],
                "scope_binding": scope_binding,
                "protected_branch_residue": protected_branch_residue,
            },
            "commands": {},
        }
    required_gaps = openspec_root_gaps(openspec_root, official_config)
    context = OpenSpecReportContext(
        request=request,
        official_config=official_config,
        official_package=openspec_cli.OFFICIAL_PACKAGE_SPEC,
        required_gaps=required_gaps,
        advisory_gaps=advisory_gaps,
        protected_branch_residue=protected_branch_residue,
    )

    if base_command is None:
        required_gaps.append("openspec_official_cli_missing")
        return openspec_unavailable_report(root, context)

    config = openspec_cli.run_json(root, base_command, ("config", "list", "--json"))
    required_gaps.extend(["openspec_config_json_parse_failed"] if config["parse_error"] else [])
    required_gaps.extend(openspec_cli.config_contract_gaps(config["json"]))
    doctor = openspec_cli.run_json(root, base_command, ("doctor", "--json"))
    if doctor["parse_error"] == "openspec_command_timeout":
        required_gaps.extend(["openspec_doctor_unhealthy", "openspec_doctor_json_parse_failed"])
        return openspec_timeout_report(
            root=root,
            context=context,
            base_command=base_command,
            doctor=doctor,
        )
    list_result = openspec_cli.run_json(root, base_command, ("list", "--json"))
    rows = official_change_rows(list_result["json"])
    official_selected = selected_change(rows, request.change) if rows is not None else None
    completed_change = (
        rows[0]["name"]
        if rows is not None and len(rows) == 1 and rows[0]["status"] == "complete"
        else None
    )
    status = openspec_status_result(
        root,
        base_command,
        official_selected or completed_change,
        openspec_cli.run_json,
    )
    archive_scope = (
        lease_bound_archive_scope_report(
            root,
            changed_paths=request.changed_paths,
            requested_change=request.change,
            official_change_complete=completed_change is not None,
            completion_artifacts=_artifact_output_paths(root, status.get("json", {})),
        )
        if official_selected is None
        and rows is not None
        and (not rows or (len(rows) == 1 and rows[0]["status"] == "complete"))
        else None
    )
    archived_change = (
        str(archive_scope["changes"][0]["name"])
        if archive_scope and archive_scope.get("changes")
        else None
    )
    selected = official_selected or archived_change
    apply = (
        openspec_cli.run_json(
            root,
            base_command,
            ("instructions", "apply", "--change", official_selected, "--json"),
        )
        if official_selected
        else {}
    )
    archive = (
        openspec_cli.run_json(
            root,
            base_command,
            ("instructions", "archive", "--change", official_selected, "--json"),
        )
        if official_selected
        else {}
    )
    validate = openspec_cli.run_json(
        root,
        base_command,
        ("validate", "--all", "--strict", "--json"),
    )

    required_gaps.extend(
        openspec_command_gaps(
            doctor=doctor,
            list_result=list_result,
            status=status,
            validate=validate,
            selected=official_selected,
        )
    )
    if official_selected:
        required_gaps.extend(openspec_cli.status_contract_gaps(status["json"]))
        required_gaps.extend(openspec_cli.instructions_contract_gaps("apply", apply["json"]))
        required_gaps.extend(openspec_cli.instructions_contract_gaps("archive", archive["json"]))
    if archive_scope is None:
        required_gaps.extend(
            ["openspec_list_unreadable"] if rows is None else selection_gaps(rows, request.change)
        )
    lifecycle_payload = (
        {
            "required_gaps": archive_scope["required_gaps"],
            "changes": [],
            "scope_binding": archive_scope,
            "protected_branch_residue": protected_branch_residue,
        }
        if archive_scope is not None
        else lifecycle_report(
            root,
            request=request,
            list_payload=list_result["json"],
            status_payload=status["json"],
            apply_payload=apply["json"],
            protected_branch_residue=protected_branch_residue,
        )
        if official_selected is not None or not request.lifecycle
        else lifecycle_report(
            root,
            request=request._replace(lifecycle=False),
            list_payload={},
            protected_branch_residue=protected_branch_residue,
        )
    )
    required_gaps.extend(str(gap) for gap in lifecycle_payload["required_gaps"])

    return {
        "verdict": "block" if required_gaps else "pass",
        "official_config": official_config,
        "official_cli": openspec_official_cli(
            package=openspec_cli.OFFICIAL_PACKAGE_SPEC,
            base_command=base_command,
        ),
        "change": selected,
        "schema_name": status.get("json", {}).get("schemaName") if status else "",
        "summary": {
            "change_count": len(rows or ()),
            "validation": validate["json"].get("summary", {}),
        },
        "required_gaps": required_gaps,
        "advisory_gaps": advisory_gaps,
        "lifecycle": {
            "enabled": request.lifecycle,
            "changes": lifecycle_payload["changes"],
            "scope_binding": lifecycle_payload["scope_binding"],
            "protected_branch_residue": lifecycle_payload["protected_branch_residue"],
        },
        "commands": {
            "config": config,
            "doctor": doctor,
            "list": list_result,
            "status": status,
            "apply": apply,
            "archive": archive,
            "validate": validate,
        },
    }


def _artifact_output_paths(root: Path, status: dict[str, Any]) -> tuple[str, ...]:
    paths: list[str] = []
    artifact_paths = status.get("artifactPaths")
    if not isinstance(artifact_paths, dict):
        return ()
    for artifact in artifact_paths.values():
        if not isinstance(artifact, dict):
            continue
        outputs = artifact.get("existingOutputPaths")
        for output in outputs if isinstance(outputs, list) else ():
            try:
                paths.append(Path(str(output)).resolve().relative_to(root.resolve()).as_posix())
            except ValueError:
                continue
    return tuple(dict.fromkeys(paths))
