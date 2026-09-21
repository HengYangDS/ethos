"""Render the shared planning operation through Cyclopts."""

from ethos.domain.plan import plan_repository
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@app.command
def plan(
    *,
    changed: bool = False,
    change: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Compile deterministic TransitionPlan."""
    repo = resolve_root(root)
    emit(
        plan_repository(repo, changed=changed, change=change),
        json_output=json_output,
        enforce=False,
        artifact_root=repo,
    )
