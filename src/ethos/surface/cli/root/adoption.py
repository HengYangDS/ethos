"""Render the shared adoption operation through Cyclopts."""

from ethos.domain.adoption import adopt_repository
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@app.command
def adopt(
    *,
    root: RootOption | None = None,
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    expect_plan_digest: str | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan or apply ETHOS adoption for a repository."""
    result = adopt_repository(
        resolve_root(root),
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        expect_plan_digest=expect_plan_digest,
    )
    emit(result, json_output=json_output, enforce=apply)
