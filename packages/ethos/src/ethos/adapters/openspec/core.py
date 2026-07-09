from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.lifecycle.core import OpenSpecReportContext
from ethos.adapters.openspec.lifecycle.core import OpenSpecRequest
from ethos.adapters.openspec.lifecycle.core import lifecycle_report
from ethos.adapters.openspec.lifecycle.core import openspec_command_gaps
from ethos.adapters.openspec.lifecycle.core import openspec_root_gaps
from ethos.adapters.openspec.lifecycle.core import openspec_status_result
from ethos.adapters.openspec.lifecycle.core import openspec_timeout_report
from ethos.adapters.openspec.lifecycle.core import openspec_unavailable_report
from ethos.adapters.openspec.lifecycle.core import selected_change
from ethos.adapters.openspec.workspace.core import openspec_workspace_signature
from ethos.repository.openspec.audit import official_config_report
from ethos.repository.openspec.audit import protected_branch_active_change_report

if TYPE_CHECKING:
    from typing import Any


def openspec_governance_report(
    root: Path,
    *,
    change: str | None = None,
    lifecycle: bool = False,
) -> dict[str, Any]:
    """Return the ETHOS OpenSpec governance report for one repository root."""
    request = OpenSpecRequest(change, lifecycle)
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
    required_gaps = openspec_root_gaps(openspec_root, official_config)
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
        return openspec_unavailable_report(context)

    doctor = openspec_cli.run_json(root, base_command, ("doctor", "--json"))
    if doctor["parse_error"] == "openspec_command_timeout":
        required_gaps.extend(["openspec_doctor_unhealthy", "openspec_doctor_json_parse_failed"])
        return openspec_timeout_report(
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
        selected=request.change,
        list_payload=list_result["json"],
        enabled=request.lifecycle,
        protected_branch_residue=protected_branch_residue,
    )
    required_gaps.extend(str(gap) for gap in lifecycle_payload["required_gaps"])

    return {
        "ok": not required_gaps,
        "official_config": official_config,
        "official_cli": {
            "package": openspec_cli.OFFICIAL_NPX_PACKAGE,
            "available": True,
            "base_command": list(base_command),
        },
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
            "protected_branch_residue": lifecycle_payload["protected_branch_residue"],
        },
        "commands": {
            "doctor": doctor,
            "list": list_result,
            "status": status,
            "validate": validate,
        },
    }
