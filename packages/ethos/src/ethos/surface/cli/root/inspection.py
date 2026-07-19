"""Root inspection and scorecard commands."""

from __future__ import annotations

import pathlib
import shlex
import sys
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import cast

from cyclopts import Parameter

import ethos.domain.orient as orient_domain
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.maintenance import apply_local_state_maintenance
from ethos.adapters.store.state.maintenance import local_state_maintenance_inventory
from ethos.adapters.store.state.lease.lifecycle.core import initialize_lease_state
from ethos.domain.prove import workspace_status_validation
from ethos.domain.prove import workspace_status_validation_gaps
from ethos.domain.report import scorecard_report
from ethos.repository.context import context_for_root
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli.quality.reporting import build_declarative_report_result
from ethos.surface.cli.quality.reporting import declared_report_result
from ethos_core.normalization.core import integer
from ethos_core.normalization.core import string_mapping
from ethos_core.normalization.core import string_sequence
from ethos_core.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Mapping


def _orient_report(repo: pathlib.Path) -> dict[str, object]:
    """Supply orient's facts without assembling its CLI envelope."""
    packet = orient_domain.orientation_packet(
        status_payload=workspace_status(repo, include_foreign_path_scope=False),
        report_payload=scorecard_report(repo),
        command_prefix=_checkout_command_prefix(repo),
    )
    return {
        "ok": True,
        "state": "oriented",
        "next_actions": packet["next_actions"],
        "governance_context": context_for_root(repo),
        "orientation": packet,
    }


def _status_report(repo: pathlib.Path) -> dict[str, object]:
    """Supply validated status facts without assembling its CLI envelope."""
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    validation = workspace_status_validation(repo, status_payload)
    orientation = orient_domain.orientation_packet(
        status_payload=status_payload,
        command_prefix=_checkout_command_prefix(repo),
    )
    ok = bool(validation["ok"])
    return {
        "ok": ok,
        "state": "invalid" if not ok else "dirty" if status_payload["dirty"] else "ready",
        "diagnostics": [validation],
        "required_gaps": tuple(string_sequence(status_payload.get("required_gaps")))
        + workspace_status_validation_gaps(validation),
        "next_actions": orientation["next_actions"],
        "governance_context": context_for_root(repo),
        "status": status_payload,
        "orientation": orientation,
    }


def _checkout_command_prefix(repo: pathlib.Path) -> str:
    """Return the source-bound command prefix for actions emitted by this checkout."""
    resolved = pathlib.Path(repo).resolve()
    return f"cd {shlex.quote(resolved.as_posix())} && tools/ci/scripts/run-ethos-lane.sh"


def _scorecard_reader_report(
    repo: pathlib.Path,
    *,
    product_root: pathlib.Path | None = None,
) -> dict[str, object]:
    """Supply scorecard facts for the report reader projection."""
    return scorecard_report(repo, product_root=product_root)


def status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
    compact: Annotated[bool, Parameter(name="--compact")] = False,
) -> None:
    """Inspect repository state."""
    repo = resolve_root(root)
    handler, report_payload, result = declared_report_result(
        module_name=__name__,
        function_name="status",
        target=repo,
        group="root",
    )
    if compact:
        result = _compact_status_result(result)
    if json_output:
        emit(result, json_output=json_output, enforce=handler.enforce)
        return
    orientation = cast("dict[str, object]", report_payload["orientation"])
    for line in orient_domain.human_orientation_lines(orientation):
        sys.stdout.write(f"{line}\n")


def _compact_status_result(result: EthosResult) -> EthosResult:
    """Project status into bounded decision facts for agent and CI callers."""
    data = result.data
    coordination = cast("dict[str, object]", data.get("coordination") or {})
    landing = cast("dict[str, object]", data.get("landing_readiness") or {})
    candidate = cast("dict[str, object]", data.get("candidate") or {})
    compact_data = {
        "compact": True,
        "root": data.get("root", ""),
        "branch": data.get("branch", ""),
        "head": data.get("head", ""),
        "role": data.get("role", ""),
        "dirty": bool(data.get("dirty")),
        "changed_path_count": _count_sequence(data.get("changed_paths")),
        "landing_readiness": {
            "state": landing.get("state", ""),
            "required_gaps": string_sequence(landing.get("required_gaps")),
            "next_action": landing.get("next_action", ""),
        },
        "candidate": {
            "branch": candidate.get("branch", ""),
            "head": candidate.get("head", ""),
            "exists": bool(candidate.get("exists")),
            "worktree_exists": bool(candidate.get("worktree_exists")),
        },
        "coordination": {
            "blocking": bool(coordination.get("blocking")),
            "foreign_work_lane_count": integer(coordination.get("foreign_work_lane_count")),
            "unbound_work_lane_count": integer(coordination.get("unbound_work_lane_count")),
            "missing_lease_count": integer(coordination.get("missing_lease_count")),
            "advisory_count": _count_sequence(coordination.get("advisory_gaps")),
            "required_count": _count_sequence(coordination.get("required_gaps")),
        },
        "stage_gates": cast("dict[str, object]", data.get("stage_gates") or {}),
    }
    return EthosResult(
        command=result.command,
        ok=result.ok,
        state=result.state,
        summary={**result.summary, "compact": True},
        diagnostics=result.diagnostics,
        required_gaps=result.required_gaps,
        next_actions=result.next_actions,
        governance_context=result.governance_context,
        data=compact_data,
    )


def orient(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Orient a human or agent without minting repository truth."""
    repo = resolve_root(root)
    handler, report_payload, result = declared_report_result(
        module_name=__name__,
        function_name="orient",
        target=repo,
        group="root",
    )
    if json_output:
        emit(result, json_output=json_output, enforce=handler.enforce)
        return
    packet = cast("dict[str, object]", report_payload["orientation"])
    for line in orient_domain.human_orientation_lines(packet):
        sys.stdout.write(f"{line}\n")


def _count_sequence(value: object) -> int:
    if isinstance(value, list | tuple):
        return len(value)
    return 0


def _compact_invalid_states(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {"category_count": 0, "gap_count": 0}
    return {
        "category_count": integer(value.get("category_count")),
        "gap_count": integer(value.get("gap_count")),
    }


def _compact_gap_layers(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, dict):
        return {}
    compact_layers: dict[str, dict[str, object]] = {}
    for name, raw_layer in value.items():
        if not isinstance(raw_layer, dict):
            continue
        compact_layers[str(name)] = {
            "blocking": bool(raw_layer.get("blocking")),
            "ok": bool(raw_layer.get("ok")),
            "required_count": _count_sequence(raw_layer.get("required_gaps")),
            "advisory_count": _count_sequence(raw_layer.get("advisory_gaps")),
            "gap_count": integer(raw_layer.get("gap_count")),
            "invalid_states": _compact_invalid_states(raw_layer.get("invalid_states")),
        }
    return compact_layers


def _compact_report_data(data: dict[str, Any]) -> dict[str, object]:
    advisory_signals = cast("dict[str, object]", data.get("advisory_signals") or {})
    parity = cast("dict[str, object]", data.get("parity") or {})
    parity_gaps = cast("dict[str, object]", parity.get("gaps") or {})
    adopter_gaps = cast("dict[str, object]", parity.get("adopter_gaps") or {})
    return {
        "compact": True,
        "scores": data.get("scores", {}),
        "score_model": data.get("score_model", {}),
        "first_hour": data.get("first_hour", {}),
        "gap_layers": _compact_gap_layers(data.get("gap_layers")),
        "invalid_states": _compact_invalid_states(data.get("invalid_states")),
        "advisory_signals": {
            "blocking": bool(advisory_signals.get("blocking")),
            "gap_count": integer(advisory_signals.get("gap_count")),
            "next_action_count": _count_sequence(advisory_signals.get("next_actions")),
        },
        "parity": {
            "scope": parity.get("scope", {}),
            "generic_gap_count": _count_sequence(parity_gaps.get("required_gaps")),
            "adopter_gap_count": _count_sequence(adopter_gaps.get("required_gaps")),
            "pending_package_count": _count_sequence(parity_gaps.get("pending_packages")),
        },
    }


def _compact_report_payload(payload: Mapping[str, object]) -> dict[str, object]:
    data = cast("dict[str, Any]", string_mapping(payload.get("data")))
    return {
        **payload,
        "governance_context": data.get("governance_context", {}),
        "summary": {**string_mapping(payload.get("summary")), "compact": True},
        "data": _compact_report_data(data),
    }


def report(
    *,
    root: RootOption | None = None,
    product_root: Annotated[pathlib.Path | None, Parameter(name="--product-root")] = None,
    json_output: JsonFlag = False,
    compact: Annotated[bool, Parameter(name="--compact")] = False,
) -> None:
    """Emit a concise scorecard."""
    handler, payload, result = declared_report_result(
        module_name=__name__,
        function_name="report",
        target=resolve_root(root),
        group="root",
        provider_kwargs={
            "product_root": resolve_root(product_root) if product_root is not None else None
        },
    )
    if compact:
        payload = _compact_report_payload(payload)
        result = build_declarative_report_result(
            command="report",
            handler=handler,
            report=payload,
        )
    emit(result, json_output=json_output, enforce=handler.enforce)


def doctor(
    *,
    root: RootOption | None = None,
    init_state: bool = False,
    maintenance: Annotated[bool, Parameter(name="--maintenance")] = False,
    apply_maintenance: Annotated[bool, Parameter(name="--apply-maintenance")] = False,
    archive_root: Annotated[pathlib.Path | None, Parameter(name="--archive-root")] = None,
    observed_at: Annotated[str, Parameter(name="--observed-at")] = "",
    expect_inventory_digest: Annotated[str, Parameter(name="--expect-inventory-digest")] = "",
    confirm_irreversible: Annotated[bool, Parameter(name="--confirm-irreversible")] = False,
    json_output: JsonFlag = False,
) -> None:
    """Inspect local host readiness."""
    repo = resolve_root(root)
    db_path = repo / ".ethos" / "state" / "state.sqlite"
    if init_state:
        initialize_lease_state(db_path)
    maintenance_payload: dict[str, Any] = {}
    maintenance_gaps: list[str] = []
    if maintenance or apply_maintenance:
        if archive_root is None:
            maintenance_gaps.append("maintenance_archive_root_required")
        if not observed_at:
            maintenance_gaps.append("maintenance_observed_at_required")
        if not maintenance_gaps:
            try:
                if apply_maintenance:
                    maintenance_payload = apply_local_state_maintenance(
                        repo,
                        cast("pathlib.Path", archive_root),
                        observed_at,
                        expect_inventory_digest=expect_inventory_digest,
                        confirm_irreversible=confirm_irreversible,
                    )
                else:
                    maintenance_payload = local_state_maintenance_inventory(
                        repo,
                        cast("pathlib.Path", archive_root),
                        observed_at,
                    )
            except (OSError, RuntimeError, ValueError) as exc:
                maintenance_gaps.append(str(exc) or exc.__class__.__name__)
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
