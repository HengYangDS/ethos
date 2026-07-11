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
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli.quality.reporting import build_declarative_report_result
from ethos.surface.cli.quality.reporting import declared_report_result
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


def _orient_report(repo: Path) -> dict[str, object]:
    """Supply orient's facts without assembling its CLI envelope."""
    packet = orient_domain.orientation_packet(
        status_payload=workspace_status(repo),
        report_payload=scorecard_report(repo),
    )
    return {
        "ok": True,
        "state": "oriented",
        "next_actions": packet["next_actions"],
        "governance_context": context_for_root(repo),
        "orientation": packet,
    }


def _status_report(repo: Path) -> dict[str, object]:
    """Supply validated status facts without assembling its CLI envelope."""
    status_payload = workspace_status(repo)
    validation = workspace_status_validation(repo, status_payload)
    orientation = orient_domain.orientation_packet(status_payload=status_payload)
    ok = bool(validation["ok"])
    return {
        "ok": ok,
        "state": "invalid" if not ok else "dirty" if status_payload["dirty"] else "ready",
        "diagnostics": [validation],
        "required_gaps": tuple(status_payload.get("required_gaps", ()))
        + workspace_status_validation_gaps(validation),
        "next_actions": orientation["next_actions"],
        "governance_context": context_for_root(repo),
        "status": status_payload,
        "orientation": orientation,
    }


def _scorecard_reader_report(
    repo: Path,
    *,
    product_root: Path | None = None,
) -> dict[str, object]:
    """Supply scorecard facts for the report reader projection."""
    return scorecard_report(repo, product_root=product_root)


def status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Inspect repository state."""
    repo = resolve_root(root)
    handler, report_payload, result = declared_report_result(
        module_name=__name__,
        function_name="status",
        target=repo,
        group="root",
    )
    if json_output:
        emit(result, json_output=json_output, enforce=handler.enforce)
        return
    orientation = cast("dict[str, object]", report_payload["orientation"])
    for line in orient_domain.human_orientation_lines(orientation):
        sys.stdout.write(f"{line}\n")


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
        "governance_context": data["governance_context"],
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


def report(
    *,
    root: RootOption | None = None,
    product_root: Annotated[Path | None, Parameter(name="--product-root")] = None,
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
