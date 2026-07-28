from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.archive.query import active_change_identifier_gaps
from ethos.adapters.openspec.lifecycle.report import OpenSpecReportContext
from ethos.adapters.openspec.lifecycle.report import OpenSpecRequest
from ethos.adapters.openspec.lifecycle.report import lifecycle_report
from ethos.adapters.openspec.lifecycle.report import openspec_command_gaps
from ethos.adapters.openspec.lifecycle.report import openspec_official_cli
from ethos.adapters.openspec.lifecycle.report import openspec_root_gaps
from ethos.adapters.openspec.lifecycle.report import openspec_status_result
from ethos.adapters.openspec.lifecycle.report import openspec_timeout_report
from ethos.adapters.openspec.lifecycle.report import openspec_unavailable_report
from ethos.adapters.openspec.lifecycle.report import selected_change
from ethos.adapters.openspec.workspace.signature import openspec_workspace_signature
from ethos.repository.context import is_product_root
from ethos.repository.openspec.audit import archive_identity_violations
from ethos.repository.openspec.audit import official_config_report
from ethos.repository.openspec.audit import protected_branch_active_change_report
from ethos.repository.profile import load_repository_profile

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
    profile = load_repository_profile(root)
    if not is_product_root(root) and (
        profile.declaration is None or profile.declaration.openspec is None
    ):
        request = OpenSpecRequest(change, lifecycle, changed_paths, require_workspace)
        report = lifecycle_report(root, request=request, list_payload={})
        return {
            "ok": True,
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
    active_identifier_gaps = active_change_identifier_gaps(root, change)
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
    signature = openspec_workspace_signature(root)
    return deepcopy(
        _cached_openspec_governance_report(
            root.resolve().as_posix(),
            request,
            base_command,
            signature,
        )
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
        "ok": False,
        "official_config": official_config_report(root),
        "official_cli": {
            "package": openspec_cli.OFFICIAL_NPX_PACKAGE,
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


@lru_cache(maxsize=32)
def _cached_openspec_governance_report(
    root_posix: str,
    request: OpenSpecRequest,
    base_command: tuple[str, ...],
    _signature: tuple[tuple[str, int, int], ...],
) -> dict[str, Any]:
    return _openspec_governance_report(
        Path(root_posix),
        request=request,
        base_command=base_command,
    )


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
            "ok": True,
            "state": "not_applicable",
            "official_config": official_config,
            "official_cli": openspec_official_cli(
                package=openspec_cli.OFFICIAL_NPX_PACKAGE,
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
    required_gaps.extend(archive_identity_violations(openspec_root))
    context = OpenSpecReportContext(
        request=request,
        official_config=official_config,
        official_package=openspec_cli.OFFICIAL_NPX_PACKAGE,
        required_gaps=required_gaps,
        advisory_gaps=advisory_gaps,
        protected_branch_residue=protected_branch_residue,
    )

    if base_command is None:
        required_gaps.append("openspec_official_cli_missing")
        return openspec_unavailable_report(root, context)

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
    selected = selected_change(list_result["json"], request.change)
    status = openspec_status_result(root, base_command, selected, openspec_cli.run_json)
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
            selected=selected,
        )
    )
    lifecycle_payload = lifecycle_report(
        root,
        request=request,
        list_payload=list_result["json"],
        protected_branch_residue=protected_branch_residue,
        base_command=base_command,
    )
    required_gaps.extend(str(gap) for gap in lifecycle_payload["required_gaps"])

    return {
        "ok": not required_gaps,
        "official_config": official_config,
        "official_cli": openspec_official_cli(
            package=openspec_cli.OFFICIAL_NPX_PACKAGE,
            base_command=base_command,
        ),
        "change": selected,
        "schema_name": status.get("json", {}).get("schemaName") if status else "",
        "summary": {
            "change_count": len(list_result["json"].get("changes", [])),
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
            "doctor": doctor,
            "list": list_result,
            "status": status,
            "validate": validate,
        },
    }
