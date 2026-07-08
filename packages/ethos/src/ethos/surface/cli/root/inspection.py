"""Root inspection and scorecard commands."""

from __future__ import annotations

import os
import shutil
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any
from typing import cast

import ethos.domain.orient as orient_domain
from ethos.adapters.repo.status import workspace_status
from ethos.adapters.store.state import initialize_state
from ethos.domain.prove import workspace_status_validation
from ethos.domain.prove import workspace_status_validation_gaps
from ethos.domain.report import scorecard_report
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
) -> None:
    """Inspect repository state."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
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
        data=status_payload,
    )
    if json_output:
        emit(result, json_output=json_output, enforce=False)
        return
    for line in orient_domain.human_orientation_lines(orientation):
        sys.stdout.write(f"{line}\n")


@app.command
def orient(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Orient a human or agent without minting repository truth."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
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
            "capability": capability["current_actor_capability"],
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
        data={"orientation": packet},
    )
    if json_output:
        emit(result, json_output=json_output, enforce=False)
        return
    for line in orient_domain.human_orientation_lines(packet):
        sys.stdout.write(f"{line}\n")


@app.command
def report(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Emit a concise scorecard."""
    payload = scorecard_report(resolve_root(root))
    result = EthosResult(
        command="report",
        ok=bool(payload["ok"]),
        state="ready" if payload["ok"] else "gapped",
        summary=payload["summary"],
        required_gaps=tuple(payload["required_gaps"]),
        next_actions=tuple(payload["next_actions"]),
        data=payload["data"],
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
