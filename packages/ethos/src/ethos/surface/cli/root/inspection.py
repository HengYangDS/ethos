"""Root inspection and scorecard commands."""

from __future__ import annotations

import os
import shutil
import sys
from contextlib import suppress
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import cast

from cyclopts import Parameter

import ethos.domain.orient as orient_domain
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.events import initialize_state
from ethos.domain.prove import workspace_status_validation
from ethos.domain.prove import workspace_status_validation_gaps
from ethos.domain.report import scorecard_report
from ethos.repository.context import context_for_root
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


def host_wrapper_report(repo: Path) -> dict[str, object]:
    """Report whether PATH resolves `ethos` to a host wrapper with fixed root drift."""
    command_path = shutil.which("ethos") or ""
    if not command_path:
        return {
            "kind": "host_wrapper",
            "state": "not_found",
            "path": "",
            "repository_root": repo.as_posix(),
            "advisory_gaps": ["host_wrapper_not_found"],
            "next_action": "run via `uv run --package ethos ethos ...` from the target checkout",
        }
    path = Path(command_path).resolve()
    text = ""
    with suppress(OSError):
        text = path.read_text(encoding="utf-8", errors="replace")
    fixed_root = (
        "ETHOS_ROOT" in text
        and "$HOME/projects/ethos" in text
        and "git rev-parse" not in text
        and "findSourceRoot" not in text
    )
    env_root = os.environ.get("ETHOS_ROOT", "")
    advisory_gaps: list[str] = []
    if fixed_root and not env_root:
        advisory_gaps.append("host_wrapper_fixed_root")
    state = "fixed_root_wrapper" if fixed_root and not env_root else "ok"
    next_action = (
        "set ETHOS_ROOT explicitly or run `uv run --package ethos ethos ...` "
        "from the target checkout"
        if advisory_gaps
        else "host wrapper does not force a different repository root"
    )
    return {
        "kind": "host_wrapper",
        "state": state,
        "path": path.as_posix(),
        "repository_root": repo.as_posix(),
        "env_ethos_root": env_root,
        "advisory_gaps": advisory_gaps,
        "next_action": next_action,
    }


@app.command
def status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
    compact: Annotated[bool, Parameter(name="--compact")] = False,
) -> None:
    """Inspect repository state."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
    governance = context_for_root(repo)
    orientation = orient_domain.orientation_packet(status_payload=status_payload)
    orientation_actions = cast("list[str]", orientation["next_actions"])
    coordination = cast("dict[str, object]", status_payload.get("coordination", {}))
    validation = workspace_status_validation(repo, status_payload)
    validation_gaps = workspace_status_validation_gaps(validation)
    ok = bool(validation["ok"])
    result = EthosResult(
        command="status",
        ok=ok,
        state="invalid" if not ok else "dirty" if status_payload["dirty"] else "ready",
        summary={
            "root": str(repo),
            "branch": status_payload["branch"],
            "role": status_payload.get("role", ""),
            "dirty": status_payload["dirty"],
            "changed_path_count": len(cast("list[object]", status_payload["changed_paths"])),
            "foreign_work_lane_count": coordination.get("foreign_work_lane_count", 0),
            "unbound_work_lane_count": coordination.get("unbound_work_lane_count", 0),
            "missing_lease_count": coordination.get("missing_lease_count", 0),
            "dirty_foreign_work_lane_count": sum(
                1
                for lane in cast("list[object]", status_payload.get("foreign_work_lanes") or [])
                if isinstance(lane, dict) and bool(lane.get("dirty"))
            ),
            "coordination_advisory_count": len(
                cast("list[object]", coordination.get("advisory_gaps") or [])
            ),
            "coordination_blocking": bool(coordination.get("blocking")),
        },
        diagnostics=(validation,),
        required_gaps=tuple(status_payload.get("required_gaps", ())) + validation_gaps,
        next_actions=tuple(orientation_actions),
        governance_context=governance,
        data=status_payload,
    )
    if compact:
        result = _compact_status_result(result)
    if json_output:
        emit(result, json_output=json_output, enforce=False)
        return
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
            "required_gaps": _string_list(landing.get("required_gaps")),
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
            "foreign_work_lane_count": int(coordination.get("foreign_work_lane_count") or 0),
            "unbound_work_lane_count": int(coordination.get("unbound_work_lane_count") or 0),
            "missing_lease_count": int(coordination.get("missing_lease_count") or 0),
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


@app.command
def orient(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Orient a human or agent without minting repository truth."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
    governance = context_for_root(repo)
    report_payload = scorecard_report(repo)
    packet = orient_domain.orientation_packet(
        status_payload=status_payload,
        report_payload=report_payload,
    )
    where = cast("dict[str, Any]", packet["where"])
    capability = cast("dict[str, Any]", packet["capability"])
    coordination = cast("dict[str, Any]", packet["coordination"])
    readiness = cast("dict[str, Any]", packet["readiness"])
    packet_actions = cast("list[str]", packet["next_actions"])
    result = EthosResult(
        command="orient",
        ok=True,
        state="oriented",
        summary={
            "role": where["role"],
            "candidate_action": capability["candidate_action"],
            "foreign_work_lane_count": coordination["foreign_work_lane_count"],
            "unbound_work_lane_count": coordination["unbound_work_lane_count"],
            "missing_lease_count": coordination.get("missing_lease_count", 0),
            "dirty_foreign_work_lane_count": coordination.get("dirty_foreign_work_lane_count", 0),
            "coordination_advisory_count": len(coordination.get("advisory_items", [])),
            "coordination_blocking": coordination["blocking"],
            "governance_gap_count": readiness["governance_gap_count"],
            "parity_pending_count": readiness["parity_pending_count"],
            "advisory_gap_count": readiness["advisory_gap_count"],
        },
        next_actions=tuple(packet_actions),
        governance_context=governance,
        data={"orientation": packet},
    )
    if json_output:
        emit(result, json_output=json_output, enforce=False)
        return
    for line in orient_domain.human_orientation_lines(packet):
        sys.stdout.write(f"{line}\n")


def _count_sequence(value: object) -> int:
    if isinstance(value, list | tuple):
        return len(value)
    return 0


def _string_list(value: object) -> list[str]:
    """Return a string-list projection without passing through arbitrary values."""
    return [str(item) for item in value] if isinstance(value, list | tuple) else []


def _compact_invalid_states(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {"category_count": 0, "gap_count": 0}
    return {
        "category_count": int(value.get("category_count") or 0),
        "gap_count": int(value.get("gap_count") or 0),
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
            "gap_count": int(raw_layer.get("gap_count") or 0),
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
            "gap_count": int(advisory_signals.get("gap_count") or 0),
            "next_action_count": _count_sequence(advisory_signals.get("next_actions")),
        },
        "parity": {
            "scope": parity.get("scope", {}),
            "generic_gap_count": _count_sequence(parity_gaps.get("required_gaps")),
            "adopter_gap_count": _count_sequence(adopter_gaps.get("required_gaps")),
            "pending_package_count": _count_sequence(parity_gaps.get("pending_packages")),
        },
    }


def _compact_report_payload(payload: dict[str, object]) -> dict[str, object]:
    data = cast("dict[str, Any]", payload["data"])
    return {
        **payload,
        "summary": {**cast("dict[str, object]", payload["summary"]), "compact": True},
        "data": _compact_report_data(data),
    }


@app.command
def report(
    *,
    root: RootOption | None = None,
    product_root: Annotated[Path | None, Parameter(name="--product-root")] = None,
    json_output: JsonFlag = False,
    compact: Annotated[bool, Parameter(name="--compact")] = False,
) -> None:
    """Emit a concise scorecard."""
    payload = scorecard_report(
        resolve_root(root),
        product_root=resolve_root(product_root) if product_root is not None else None,
    )
    governance_context = cast("dict[str, Any]", payload["data"])["governance_context"]
    if compact:
        payload = _compact_report_payload(payload)
    result = EthosResult(
        command="report",
        ok=bool(payload["ok"]),
        state=str(payload.get("state") or ("ready" if payload["ok"] else "gapped")),
        summary=cast("dict[str, Any]", payload["summary"]),
        required_gaps=tuple(cast("tuple[str, ...] | list[str]", payload["required_gaps"])),
        next_actions=tuple(cast("tuple[str, ...] | list[str]", payload["next_actions"])),
        governance_context=cast("dict[str, Any]", governance_context),
        data=cast("dict[str, Any]", payload["data"]),
    )
    emit(result, json_output=json_output, enforce=False)


@app.command(show=False)
def doctor(
    *,
    root: RootOption | None = None,
    init_state: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Inspect local host readiness."""
    repo = resolve_root(root)
    db_path = repo / ".ethos" / "state" / "state.sqlite"
    if init_state:
        initialize_state(db_path)
    status_payload = workspace_status(repo)
    runtime = status_payload.get("runtime_binding", {})
    wrapper_report = host_wrapper_report(repo)
    result = EthosResult(
        command="doctor",
        ok=True,
        state="ready",
        summary={
            "state_db_exists": db_path.exists(),
            "host_wrapper_state": wrapper_report["state"],
        },
        next_actions=("ethos status",),
        data={
            "state_db": str(db_path),
            "initialized": init_state,
            "runtime_binding": runtime,
            "host_wrapper": wrapper_report,
        },
    )
    emit(result, json_output=json_output, enforce=False)
