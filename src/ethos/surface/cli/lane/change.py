"""Cyclopts declaration for starting the next Change in an owned Work Lane."""

from __future__ import annotations

from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.change_rollover import start_change
from ethos.surface.cli.application import lane_app
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import resolve_root


class _StartChange(AppliedLaneCommandOptions):
    command = "lane start-change"
    intent: Annotated[str, Parameter(name="--intent")]
    scope: Annotated[tuple[str, ...], Parameter(name="--scope")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]
    expected_overlay_digest: Annotated[str, Parameter(name="--expected-overlay-digest")] = ""


@lane_app.command(name="start-change")
def lane_start_change(
    change: str,
    options: Annotated[_StartChange, Parameter(name="*")],
) -> None:
    """Start the next OpenSpec Change inside the current owned Work Lane."""
    report = start_change(
        root=resolve_root(options.root),
        change=change,
        intent=options.intent,
        scope=options.scope,
        expect_head=options.expect_head,
        expected_overlay_digest=options.expected_overlay_digest,
        apply=options.apply,
    )
    project_lane_result(
        options.command,
        report,
        summary={key: report.get(key, "") for key in ("branch", "change", "head", "previous_head")},
        enforce=options.apply,
        json_output=options.json_output,
    )
