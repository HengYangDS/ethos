"""Installed native projection preview, drift check and exact patch admission."""

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.projection import project_repository
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@lane_app.command(name="project")
def lane_project(
    *,
    check: bool = False,
    apply: bool = False,
    authorize: bool = False,
    expect_head: Annotated[str, Parameter(name="--expect-head")] = "",
    patch: Path | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Generate every declared native projection without requiring a product checkout."""
    report = project_repository(
        resolve_root(root),
        check=check,
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        preview_patch=patch.read_text(encoding="utf-8") if patch is not None else None,
    )
    project_lane_result("lane project", report, enforce=True, json_output=json_output)
