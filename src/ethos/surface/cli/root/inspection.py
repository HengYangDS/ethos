"""Render the shared repository observation through Cyclopts."""

from ethos.domain.inspection import inspect_repository
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@app.command
def status(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Inspect bounded truth, authority, gaps, coordination, and next action."""
    repo = resolve_root(root)
    emit(inspect_repository(repo), json_output=json_output, enforce=False, artifact_root=repo)
