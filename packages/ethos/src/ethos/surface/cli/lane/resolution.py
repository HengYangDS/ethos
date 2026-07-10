"""Exceptional Work Lane resolution commands."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import lane_resolution_app
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


def _emit(command: str, report: dict[str, object], *, json_output: bool) -> None:
    result = EthosResult(
        command=command,
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={"branch": report["branch"]},
        required_gaps=tuple(str(gap) for gap in report["required_gaps"]),
        next_actions=(),
        data=report,
    )
    emit(result, json_output=json_output)


@lane_resolution_app.command(name="decide")
def lane_resolution_decide(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    disposition: Annotated[str, Parameter(name="--disposition")],
    reason: Annotated[str, Parameter(name="--reason")],
    evidence_ref: Annotated[tuple[str, ...], Parameter(name="--evidence-ref")] = (),
    chronicle_ref: Annotated[str, Parameter(name="--chronicle-ref")],
    recovery_plan: Annotated[str, Parameter(name="--recovery-plan")],
    decision_path: Annotated[Path, Parameter(name="--decision-path")],
    break_glass: Annotated[bool, Parameter(name="--break-glass")] = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Record a first-phase exceptional judgment bound to an exact observation."""
    report = plan_lane_resolution(
        root=resolve_root(root),
        branch=branch,
        disposition=disposition,
        reason=reason,
        evidence_refs=evidence_ref,
        chronicle_ref=chronicle_ref,
        recovery_plan=recovery_plan,
        decision_path=decision_path,
        break_glass=break_glass,
        apply=apply,
    )
    _emit("lane resolution decide", report, json_output=json_output)


@lane_resolution_app.command(name="apply")
def lane_resolution_apply(
    *,
    decision_path: Annotated[Path, Parameter(name="--decision-path")],
    confirm_irreversible: Annotated[bool, Parameter(name="--confirm-irreversible")] = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Recompute the target observation and apply the accepted disposition."""
    report = apply_lane_resolution(
        root=resolve_root(root),
        decision_path=decision_path,
        confirm_irreversible=confirm_irreversible,
        apply=apply,
    )
    _emit("lane resolution apply", report, json_output=json_output)
