"""Native format preview, check and admitted fix within the existing Work Lane surface."""

from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.source_format import format_source
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@lane_app.command(name="format")
def lane_format(
    *paths: str,
    check: bool = False,
    apply: bool = False,
    authorize: bool = False,
    expect_head: Annotated[str, Parameter(name="--expect-head")] = "",
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Prepare all postimages without writes, or apply them after exact native admission."""
    report = format_source(
        resolve_root(root),
        paths=paths,
        check=check,
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
    )
    project_lane_result(
        "lane format",
        report,
        enforce=True,
        json_output=json_output,
        summary={
            "file_count": report.get("file_count", 0),
            "changed_count": report.get("changed_count", 0),
            "head": report.get("head", ""),
        },
    )
