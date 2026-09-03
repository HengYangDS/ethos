"""Linked Work Lane retirement commands."""

from __future__ import annotations

from typing import Annotated
from typing import cast

from cyclopts import App
from cyclopts import Parameter

from ethos.adapters.mutation.lane_retirement.abandonment import derive_lane_abandonment
from ethos.adapters.mutation.lane_retirement.abandonment import execute_lane_abandonment
from ethos.adapters.mutation.lane_retirement.absorbed import retire_absorbed_ref
from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.adapters.mutation.lane_retirement.operation import recover_retirement_operation
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import resolve_root

_app = App(name="retire", help="Bounded Work Lane retirement lifecycle.")
lane_app.command(_app)


class _SupersededOptions(AppliedLaneCommandOptions):
    command = "lane retire superseded"
    branch: Annotated[str | None, Parameter(name="--branch")] = None
    path: Annotated[str | None, Parameter(name="--path")] = None
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    absorbed_by: Annotated[str, Parameter(name="--absorbed-by")] = ""
    reason: Annotated[str, Parameter(name="--reason")] = ""
    authorize: bool = False


class _LandedOptions(AppliedLaneCommandOptions):
    command = "lane retire landed"
    branch: Annotated[str | None, Parameter(name="--branch")] = None
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    authorize: bool = False


class _AbsorbedRefOptions(AppliedLaneCommandOptions):
    command = "lane retire absorbed-ref"
    branch: Annotated[str, Parameter(name="--branch")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]
    accepted_head: Annotated[str, Parameter(name="--accepted-head")]
    authorize: bool = False
    confirm_irreversible: Annotated[bool, Parameter(name="--confirm-irreversible")] = False


class _AbandonOptions(AppliedLaneCommandOptions):
    command = "lane retire abandon"
    branch: Annotated[str | None, Parameter(name="--branch")] = None
    reason_code: Annotated[str, Parameter(name="--reason-code")] = ""
    reason: Annotated[str, Parameter(name="--reason")] = ""
    receipt: Annotated[str | None, Parameter(name="--receipt")] = None
    receipt_sha256: Annotated[str | None, Parameter(name="--receipt-sha256")] = None
    authorize: bool = False


class _RecoverOptions(AppliedLaneCommandOptions):
    command = "lane retire recover"
    receipt: Annotated[str, Parameter(name="--receipt")]
    receipt_sha256: Annotated[str, Parameter(name="--receipt-sha256")]
    authorize: bool = False


_DEFAULT_SUPERSEDED = _SupersededOptions()
_DEFAULT_LANDED = _LandedOptions()
_DEFAULT_ABANDON = _AbandonOptions()


@_app.command(name="abandon")
def lane_retire_abandon(
    options: Annotated[_AbandonOptions, Parameter(name="*")] = _DEFAULT_ABANDON,
) -> None:
    """Derive or apply one receipt-bound clean divergent-lane abandonment."""
    repo = resolve_root(options.root)
    if options.receipt or options.receipt_sha256:
        report = execute_lane_abandonment(
            root=repo,
            receipt_path=options.receipt or "",
            receipt_sha256=options.receipt_sha256 or "",
            apply=options.apply,
            authorized=options.authorize,
        )
    elif options.apply:
        report: dict[str, object] = {
            "verdict": "block",
            "state": "blocked",
            "required_gaps": ["lane_retirement_receipt_required"],
            "next_action": "",
            "user_decision_required": False,
        }
    else:
        report = derive_lane_abandonment(
            root=repo,
            branch=options.branch or "",
            reason_code=options.reason_code,
            reason=options.reason,
        )
    project_lane_result(
        options.command,
        report,
        summary={
            "branch": report.get("branch") or options.branch or "",
            "head": report.get("head") or "",
            "completed_effects": report.get("completed_effects") or [],
            "remaining_effects": report.get("remaining_effects") or [],
        },
        enforce=options.apply,
        json_output=options.json_output,
    )


@_app.command(name="recover")
def lane_retire_recover(options: Annotated[_RecoverOptions, Parameter(name="*")]) -> None:
    """Resume one exact partial retirement from its immutable receipt."""
    report = recover_retirement_operation(
        root=resolve_root(options.root),
        receipt_path=options.receipt,
        receipt_sha256=options.receipt_sha256,
        apply=options.apply,
        authorized=options.authorize,
    )
    project_lane_result(
        options.command,
        report,
        summary={
            "branch": report.get("branch") or "",
            "head": report.get("head") or "",
            "completed_effects": report.get("completed_effects") or [],
            "remaining_effects": report.get("remaining_effects") or [],
        },
        enforce=options.apply,
        json_output=options.json_output,
    )


@_app.command(name="absorbed-ref")
def lane_retire_absorbed_ref(
    options: Annotated[_AbsorbedRefOptions, Parameter(name="*")],
) -> None:
    """Retire one exact unbound, unleased Work Lane ref absorbed by accepted truth."""
    report = retire_absorbed_ref(
        root=resolve_root(options.root),
        branch=options.branch,
        expect_head=options.expect_head,
        accepted_head=options.accepted_head,
        authorize=options.authorize,
        confirm_irreversible=options.confirm_irreversible,
        apply=options.apply,
    )
    project_lane_result(
        options.command,
        report,
        summary={
            "branch": options.branch,
            "head": options.expect_head,
            "accepted_head": options.accepted_head,
            "retire_ready": report_verdict(report) == "pass",
        },
        enforce=options.apply,
        json_output=options.json_output,
    )


@_app.command(name="superseded")
def lane_retire_superseded(
    options: Annotated[_SupersededOptions, Parameter(name="*")] = _DEFAULT_SUPERSEDED,
) -> None:
    """Retire a clean lane absorbed by accepted truth or its current leased successor."""
    request = LinkedRetirementRequest(**options.model_dump(exclude={"root", "json_output"}))
    report = retire_linked_work_lane(
        root=resolve_root(options.root),
        mode="superseded",
        request=request,
    )
    lane = cast("dict[str, object]", report["lane"])
    verdict = report_verdict(report)
    project_lane_result(
        options.command,
        report,
        summary={
            "branch": report["branch"],
            "head": lane.get("head") or request.expect_head or "",
            "absorbed_by": request.absorbed_by.strip(),
            "retire_ready": bool(lane.get("retire_ready")) and verdict == "pass",
        },
        enforce=options.apply,
        json_output=options.json_output,
    )


@_app.command(name="landed")
def lane_retire_landed(
    options: Annotated[_LandedOptions, Parameter(name="*")] = _DEFAULT_LANDED,
) -> None:
    """Retire a landed Work Lane after integration into accepted truth."""
    request = LinkedRetirementRequest(
        branch=options.branch,
        expect_head=options.expect_head,
        authorize=options.authorize,
        apply=options.apply,
    )
    report = retire_linked_work_lane(
        root=resolve_root(options.root),
        mode="landed",
        request=request,
    )
    lanes = cast("list[dict[str, object]]", report["lanes"])
    selected = next((lane for lane in lanes if lane["branch"] == options.branch), {})
    verdict = report_verdict(report)
    project_lane_result(
        options.command,
        report,
        summary={
            "landed_lane_count": (
                sum(bool(lane.get("retire_ready")) for lane in lanes) if verdict == "pass" else 0
            ),
            "selected_branch": options.branch or "",
            "selected_retire_ready": bool(selected.get("retire_ready")) and verdict == "pass",
            "selected_blockers": tuple(string_sequence(selected.get("required_gaps"))),
        },
        enforce=options.apply,
        json_output=options.json_output,
    )
