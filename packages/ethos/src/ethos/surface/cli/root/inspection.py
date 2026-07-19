"""Root inspection and scorecard commands."""

from __future__ import annotations

import pathlib
import shlex
import sys
from typing import Annotated

from cyclopts import Parameter

import ethos.domain.orient as orient_domain
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.core import initialize_lease_state
from ethos.adapters.store.state.maintenance import apply_local_state_maintenance
from ethos.adapters.store.state.maintenance import local_state_maintenance_inventory
from ethos.domain.prove import workspace_status_validation
from ethos.domain.prove import workspace_status_validation_gaps
from ethos.domain.report import scorecard_report
from ethos.repository.context import context_for_root
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli.quality.reporting import declared_report_result
from ethos_core.normalization.core import integer
from ethos_core.normalization.core import string_mapping
from ethos_core.normalization.core import string_sequence
from ethos_core.result import EthosResult


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
    repo: pathlib.Path, *, product_root: pathlib.Path | None = None
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
    _reader("status", root, json_output=json_output, compact=compact)


def _compact_status_result(result: EthosResult) -> EthosResult:
    """Project status into bounded decision facts for agent and CI callers."""
    data = result.data
    compact_data = {
        **_project(
            data, "root:v branch:v head:v role:v dirty:b changed_path_count:n:changed_paths"
        ),
        "landing_readiness": _project(
            data.get("landing_readiness"), "state:v required_gaps:l next_action:v"
        ),
        "candidate": _project(data.get("candidate"), "branch:v head:v exists:b worktree_exists:b"),
        "coordination": _project(
            data.get("coordination"),
            "blocking:b foreign_work_lane_count:i unbound_work_lane_count:i "
            "missing_lease_count:i advisory_count:n:advisory_gaps required_count:n:required_gaps",
        ),
        **_project(data, "stage_gates:d"),
    }
    return _compact_result(result, compact_data)


def orient(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Orient a human or agent without minting repository truth."""
    _reader("orient", root, json_output=json_output)


def _project_value(source: dict[str, object], key: str, kind: str) -> object:
    value = source.get(key)
    return {
        "b": bool(value),
        "i": integer(value),
        "l": string_sequence(value),
        "n": len(string_sequence(value)),
        "d": source.get(key, {}),
    }.get(kind, source.get(key, ""))


def _project(value: object, fields: str) -> dict[str, object]:
    source = string_mapping(value)
    return {
        output: _project_value(source, names[0] if names else output, kind)
        for field in fields.split()
        for output, kind, *names in (field.split(":"),)
    }


def _compact_gap_layers(value: object) -> dict[str, dict[str, object]]:
    return {
        str(name): {
            **_project(
                layer,
                "blocking:b ok:b required_count:n:required_gaps "
                "advisory_count:n:advisory_gaps gap_count:i",
            ),
            "invalid_states": _project(layer.get("invalid_states"), "category_count:i gap_count:i"),
        }
        for name, layer in string_mapping(value).items()
        if isinstance(layer, dict)
    }


def _compact_report_result(result: EthosResult) -> EthosResult:
    data, parity = result.data, string_mapping(result.data.get("parity"))
    compact_data = {
        **_project(data, "scores:d score_model:d first_hour:d"),
        "gap_layers": _compact_gap_layers(data.get("gap_layers")),
        "invalid_states": _project(data.get("invalid_states"), "category_count:i gap_count:i"),
        "advisory_signals": _project(
            data.get("advisory_signals"),
            "blocking:b gap_count:i next_action_count:n:next_actions",
        ),
        "parity": {
            **_project(parity, "scope:d"),
            **_project(
                parity.get("gaps"),
                "generic_gap_count:n:required_gaps pending_package_count:n:pending_packages",
            ),
            **_project(parity.get("adopter_gaps"), "adopter_gap_count:n:required_gaps"),
        },
    }
    return _compact_result(result, compact_data)


def _compact_result(result: EthosResult, data: dict[str, object]) -> EthosResult:
    return result.model_copy(
        update={"summary": {**result.summary, "compact": True}, "data": {"compact": True, **data}}
    )


def _reader(
    name: str,
    root: pathlib.Path | None,
    *,
    json_output: bool,
    compact: bool = False,
    product_root: pathlib.Path | None = None,
) -> None:
    repo = resolve_root(root)
    handler, payload, result = declared_report_result(
        module_name=__name__,
        function_name=name,
        target=repo,
        group="root",
        provider_kwargs={"product_root": resolve_root(product_root) if product_root else None}
        if name == "report"
        else None,
    )
    if compact:
        result = (
            _compact_status_result(result) if name == "status" else _compact_report_result(result)
        )
    if json_output or name == "report":
        emit(result, json_output=json_output, enforce=handler.enforce)
        return
    packet = string_mapping(payload.get("orientation"))
    sys.stdout.writelines(f"{line}\n" for line in orient_domain.human_orientation_lines(packet))


def report(
    *,
    root: RootOption | None = None,
    product_root: Annotated[pathlib.Path | None, Parameter(name="--product-root")] = None,
    json_output: JsonFlag = False,
    compact: Annotated[bool, Parameter(name="--compact")] = False,
) -> None:
    """Emit a concise scorecard."""
    _reader(
        "report",
        root,
        json_output=json_output,
        compact=compact,
        product_root=product_root,
    )


def _maintenance(
    repo: pathlib.Path,
    archive_root: pathlib.Path | None,
    observed_at: str,
    *,
    apply: bool,
    expect_digest: str,
    confirm: bool,
) -> tuple[dict[str, object], list[str]]:
    gaps = [
        gap
        for missing, gap in (
            (archive_root is None, "maintenance_archive_root_required"),
            (not observed_at, "maintenance_observed_at_required"),
        )
        if missing
    ]
    if gaps:
        return {}, gaps
    assert archive_root is not None
    try:
        if apply:
            return (
                apply_local_state_maintenance(
                    repo,
                    archive_root,
                    observed_at,
                    expect_inventory_digest=expect_digest,
                    confirm_irreversible=confirm,
                ),
                [],
            )
        return local_state_maintenance_inventory(repo, archive_root, observed_at), []
    except (OSError, RuntimeError, ValueError) as exc:
        return {}, [str(exc) or exc.__class__.__name__]


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
    maintenance_payload, maintenance_gaps = (
        _maintenance(
            repo,
            archive_root,
            observed_at,
            apply=apply_maintenance,
            expect_digest=expect_inventory_digest,
            confirm=confirm_irreversible,
        )
        if maintenance or apply_maintenance
        else ({}, [])
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
