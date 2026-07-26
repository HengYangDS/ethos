"""Exceptional Work Lane resolution commands."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import Annotated
from typing import cast

from cyclopts import Parameter

from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.records.clear.core import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.records.clear.core import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.result import EthosResult
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import lane_resolution_app
from ethos.surface.cli._base import resolve_root


@dataclass(frozen=True, slots=True)
class _ClearOptions:
    """CLI request fields for the explicit recovery-package clear transition."""

    decision_id: Annotated[str, Parameter(name="--decision-id")]
    expect_manifest_sha256: Annotated[str, Parameter(name="--expect-manifest-sha256")]
    chronicle_ref: Annotated[str, Parameter(name="--chronicle-ref")]
    reason: Annotated[str, Parameter(name="--reason")]
    break_glass: Annotated[bool, Parameter(name="--break-glass")] = False
    confirm_irreversible: Annotated[bool, Parameter(name="--confirm-irreversible")] = False
    apply: bool = False


_DEFAULT_CLEAR_OPTIONS = _ClearOptions(
    decision_id="",
    expect_manifest_sha256="",
    chronicle_ref="",
    reason="",
)


def _default_decision_path(root: Path, branch: str) -> Path:
    """Return the generated-artifact home for one lane-resolution decision."""
    token = branch.strip().replace("/", "-") or "lane-resolution"
    branch_digest = hashlib.sha256(branch.encode()).hexdigest()[:12]
    name = f"{token}-{branch_digest}-{uuid.uuid4()}.json"
    return current_record_root(root) / "decisions" / name


def _emit(command: str, report: dict[str, object], *, json_output: bool) -> None:
    result = EthosResult(
        command=command,
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={"branch": report["branch"]},
        required_gaps=tuple(str(gap) for gap in cast("list[object]", report["required_gaps"])),
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
    decision_path: Annotated[Path | None, Parameter(name="--decision-path")] = None,
    break_glass: Annotated[bool, Parameter(name="--break-glass")] = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Record a first-phase exceptional judgment bound to an exact observation."""
    repo = resolve_root(root)
    report = plan_lane_resolution(
        root=repo,
        branch=branch,
        disposition=disposition,
        reason=reason,
        evidence_refs=evidence_ref,
        chronicle_ref=chronicle_ref,
        recovery_plan=recovery_plan,
        decision_path=decision_path or _default_decision_path(repo, branch),
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


@lane_resolution_app.command(name="inventory")
def lane_resolution_inventory_command(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Inspect durable local receipts, retained packages, and clear records."""
    report = lane_resolution_inventory(root=resolve_root(root))
    result = EthosResult(
        command="lane resolution inventory",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(cast("dict[str, object]", report["summary"])),
        required_gaps=tuple(str(gap) for gap in cast("list[object]", report["required_gaps"])),
        next_actions=(),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@lane_resolution_app.command(name="clear")
def lane_resolution_clear(
    options: Annotated[_ClearOptions, Parameter(name="*")] = _DEFAULT_CLEAR_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Clear one retained package only after a bounded retention decision."""
    report = clear_lane_resolution_package(
        root=resolve_root(root),
        request=LaneResolutionClearRequest(
            decision_id=options.decision_id,
            expect_manifest_sha256=options.expect_manifest_sha256,
            chronicle_ref=options.chronicle_ref,
            reason=options.reason,
            break_glass=options.break_glass,
            confirm_irreversible=options.confirm_irreversible,
            apply=options.apply,
        ),
    )
    result = EthosResult(
        command="lane resolution clear",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={"decision_id": options.decision_id},
        required_gaps=tuple(str(gap) for gap in cast("list[object]", report["required_gaps"])),
        next_actions=("ethos lane resolution inventory --json",) if report["ok"] else (),
        data=report,
    )
    emit(result, json_output=json_output, enforce=options.apply)
