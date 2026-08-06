"""Public command for exact Git commit identity replacement."""

from __future__ import annotations

from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.identity_repair import repair_commit_identity
from ethos.surface.cli.application import lane_app
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import resolve_root


class IdentityRepairOptions(AppliedLaneCommandOptions):
    command = "lane repair-identity"
    old_commit: Annotated[str, Parameter(name="--old-commit")]
    new_commit: Annotated[str, Parameter(name="--new-commit")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]
    authorize: bool = False


@lane_app.command(name="repair-identity")
def repair_identity(options: Annotated[IdentityRepairOptions, Parameter(name="*")]) -> None:
    """Replace one equivalent commit identity through the protected integration train."""
    report = repair_commit_identity(
        root=resolve_root(options.root),
        old_commit=options.old_commit,
        new_commit=options.new_commit,
        expect_head=options.expect_head,
        apply=options.apply,
        authorized=options.authorize,
    )
    project_lane_result(
        options.command,
        report,
        enforce=options.apply,
        json_output=options.json_output,
    )
