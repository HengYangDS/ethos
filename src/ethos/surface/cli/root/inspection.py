"""Root repository inspection commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import cast

from cyclopts import Parameter

from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.maintenance import apply_local_state_maintenance
from ethos.adapters.store.state.maintenance import local_state_maintenance_inventory
from ethos.adapters.store.state.schema import initialize_state
from ethos.domain.campaign.closeout import campaign_publication_report
from ethos.domain.prove import workspace_status_validation
from ethos.domain.prove import workspace_status_validation_gaps
from ethos.normalization.core import integer
from ethos.normalization.core import string_sequence
from ethos.repository.context import context_for_root
from ethos.repository.context import is_product_root
from ethos.result import EthosResult
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli.quality.reporting import declared_report_result

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class DoctorMaintenanceOptions:
    """Explicit local-state maintenance options for ``ethos doctor``."""

    maintenance: Annotated[bool, Parameter(name="--maintenance")] = False
    apply_maintenance: Annotated[bool, Parameter(name="--apply-maintenance")] = False
    archive_root: Annotated[Path | None, Parameter(name="--archive-root")] = None
    observed_at: Annotated[str, Parameter(name="--observed-at")] = ""
    expect_inventory_digest: Annotated[str, Parameter(name="--expect-inventory-digest")] = ""
    confirm_irreversible: Annotated[bool, Parameter(name="--confirm-irreversible")] = False


_DEFAULT_DOCTOR_MAINTENANCE_OPTIONS = DoctorMaintenanceOptions()


def _status_report(repo: Path) -> dict[str, object]:
    """Return the singular bounded reader over current repository truth."""
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    validation = workspace_status_validation(repo, status_payload)
    terminal_gaps = (
        tuple(string_sequence(campaign_publication_report(repo).get("required_gaps")))
        if is_product_root(repo)
        else ()
    )
    required_gaps = tuple(
        dict.fromkeys(
            tuple(string_sequence(status_payload.get("required_gaps")))
            + workspace_status_validation_gaps(validation)
            + terminal_gaps
        )
    )
    coordination = cast("dict[str, object]", status_payload.get("coordination") or {})
    landing = cast("dict[str, object]", status_payload.get("landing_readiness") or {})
    return {
        "ok": bool(validation["ok"]) and not required_gaps,
        "state": "blocked" if required_gaps else "dirty" if status_payload["dirty"] else "ready",
        "diagnostics": [validation],
        "required_gaps": required_gaps,
        "next_actions": (
            ("ethos campaign status --json",)
            if terminal_gaps
            else _status_next_actions(status_payload, required_gaps)
        ),
        "governance_context": context_for_root(repo),
        "status": {
            "root": status_payload.get("root", ""),
            "branch": status_payload.get("branch", ""),
            "head": status_payload.get("head", ""),
            "role": status_payload.get("role", ""),
            "dirty": bool(status_payload.get("dirty")),
            "changed_path_count": _count_sequence(status_payload.get("changed_paths")),
            "authority": cast("dict[str, object]", status_payload.get("stage_gates") or {}),
            "landing_readiness": {
                "state": landing.get("state", ""),
                "required_gaps": string_sequence(landing.get("required_gaps")),
                "next_action": landing.get("next_action", ""),
            },
            "coordination": {
                "detail_state": coordination.get("detail_state", "exact"),
                "blocking": bool(coordination.get("blocking")),
                "foreign_work_lane_count": integer(coordination.get("foreign_work_lane_count")),
                "unbound_work_lane_count": integer(coordination.get("unbound_work_lane_count")),
                "missing_lease_count": integer(coordination.get("missing_lease_count")),
                "advisory_count": _count_sequence(coordination.get("advisory_gaps")),
                "required_count": _count_sequence(coordination.get("required_gaps")),
            },
        },
    }


def _status_next_actions(
    status_payload: dict[str, object], required_gaps: tuple[str, ...]
) -> tuple[str, ...]:
    """Select the shortest truthful next action without another reader projection."""
    if required_gaps:
        return (f"ethos explain {required_gaps[0]} --json",)
    if status_payload.get("dirty"):
        return ("git status --short",)
    role = str(status_payload.get("role") or "")
    if role == "work_lane":
        return ("ethos plan --changed --json",)
    if role == "accepted_root":
        return (
            "ethos lane start <name> --path <path> "
            "--holder-ref <kind:namespace:instance-kind:id> --apply --json",
        )
    if role == "candidate":
        return ("ethos land --closeout --json",)
    coordination = cast("dict[str, object]", status_payload.get("coordination") or {})
    action = str(coordination.get("next_action") or "")
    return (action,) if action else ()


def status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Inspect bounded truth, authority, gaps, coordination, and next action."""
    handler, _report_payload, result = declared_report_result(
        module_name=__name__, function_name="status", target=resolve_root(root), group="root"
    )
    emit(result, json_output=json_output, enforce=handler.enforce)


def _count_sequence(value: object) -> int:
    return len(value) if isinstance(value, list | tuple) else 0


def doctor(
    *,
    root: RootOption | None = None,
    init_state: bool = False,
    options: Annotated[
        DoctorMaintenanceOptions, Parameter(name="*")
    ] = _DEFAULT_DOCTOR_MAINTENANCE_OPTIONS,
    json_output: JsonFlag = False,
) -> None:
    """Inspect local host readiness."""
    repo = resolve_root(root)
    db_path = repo / ".ethos" / "state" / "state.sqlite"
    if init_state:
        initialize_state(db_path)
    maintenance_payload: dict[str, Any] = {}
    maintenance_gaps: list[str] = []
    if options.maintenance or options.apply_maintenance:
        if options.archive_root is None:
            maintenance_gaps.append("maintenance_archive_root_required")
        if not options.observed_at:
            maintenance_gaps.append("maintenance_observed_at_required")
        if not maintenance_gaps:
            try:
                if options.apply_maintenance:
                    maintenance_payload = apply_local_state_maintenance(
                        repo,
                        cast("Path", options.archive_root),
                        options.observed_at,
                        expect_inventory_digest=options.expect_inventory_digest,
                        confirm_irreversible=options.confirm_irreversible,
                    )
                else:
                    maintenance_payload = local_state_maintenance_inventory(
                        repo, cast("Path", options.archive_root), options.observed_at
                    )
            except (OSError, RuntimeError, ValueError) as exc:
                message = str(exc).strip()
                maintenance_gaps.append(
                    message
                    if message.startswith("maintenance_")
                    else "maintenance_operation_failed"
                )
    status_payload = workspace_status(repo)
    runtime = status_payload.get("runtime_binding", {})
    ok = not maintenance_gaps
    result = EthosResult(
        command="doctor",
        ok=ok,
        state="ready" if ok else "blocked",
        summary={
            "state_db_exists": db_path.exists(),
            "maintenance_state": str(maintenance_payload.get("state") or "read_only"),
        },
        required_gaps=tuple(maintenance_gaps),
        next_actions=("ethos status",),
        data={
            "state_db": str(db_path),
            "initialized": init_state,
            "maintenance": maintenance_payload,
            "runtime_binding": runtime,
        },
    )
    emit(result, json_output=json_output, enforce=False)
