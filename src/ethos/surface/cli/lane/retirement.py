"""Linked Work Lane retirement commands."""

from __future__ import annotations

from typing import Annotated
from typing import cast

from cyclopts import Parameter

from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.surface.cli.application import lane_retire_app
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import resolve_root


class _SupersededOptions(AppliedLaneCommandOptions):
    command = "lane retire superseded"
    branch: Annotated[str | None, Parameter(name="--branch")] = None
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    absorbed_by: Annotated[str, Parameter(name="--absorbed-by")] = ""
    reason: Annotated[str, Parameter(name="--reason")] = ""
    authorize: bool = False


class _LandedOptions(AppliedLaneCommandOptions):
    command = "lane retire landed"
    branch: Annotated[str | None, Parameter(name="--branch")] = None
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None


_DEFAULT_SUPERSEDED = _SupersededOptions()
_DEFAULT_LANDED = _LandedOptions()


@lane_retire_app.command(name="superseded")
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


@lane_retire_app.command(name="landed")
def lane_retire_landed(
    options: Annotated[_LandedOptions, Parameter(name="*")] = _DEFAULT_LANDED,
) -> None:
    """Retire a landed Work Lane after integration into accepted truth."""
    request = LinkedRetirementRequest(
        branch=options.branch, expect_head=options.expect_head, apply=options.apply
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
