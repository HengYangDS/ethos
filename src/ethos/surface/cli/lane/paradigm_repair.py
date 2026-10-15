"""Paradigm repair for one Work Lane."""

from __future__ import annotations

from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.paradigm_repair import repair_paradigm
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import resolve_root


class _RepairParadigm(AppliedLaneCommandOptions):
    command = "lane repair-paradigm"


_DEFAULT_OPTIONS = _RepairParadigm()


@lane_app.command(name="repair-paradigm")
def lane_repair_paradigm(
    options: Annotated[_RepairParadigm, Parameter(name="*")] = _DEFAULT_OPTIONS,
) -> None:
    """Preview or apply the deterministic repairs of repository paradigm gaps."""
    report = repair_paradigm(root=resolve_root(options.root), apply=options.apply)
    project_lane_result(
        options.command, report, enforce=options.apply, json_output=options.json_output
    )
