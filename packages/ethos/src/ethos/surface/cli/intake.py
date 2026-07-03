"""Intake command group — adopter intake-ledger readiness.

A surface command module: binds args, calls the land-stage projection, emits.
Registers onto the shared intake_app from _base; cli.py imports this module so the
decorator runs. Imports only what this group needs.
"""

from __future__ import annotations

from ethos.domain import land as _land
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import intake_app
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


@intake_app.command(name="status")
def intake_status(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report adopter intake ledger readiness."""
    repo = resolve_root(root)
    projection = _land.intake_projection_report(repo)
    gaps = tuple(str(gap) for gap in projection["required_gaps"])
    data = {
        "truth_boundary": "adopter-ledger",
        "provider": projection["provider"],
        "configured": projection["configured"],
        "expected_config": ".ethos/intake.toml",
        "adapters": ["backlog", "github", "gitlab"],
        "projection": projection,
    }
    result = EthosResult(
        command="intake status",
        ok=not gaps,
        state=str(projection["state"]),
        summary={
            "provider": data["provider"],
            "truth_boundary": data["truth_boundary"],
        },
        required_gaps=gaps,
        next_actions=(
            ("ethos adopt --dry-run",)
            if not projection["configured"]
            else ("ethos plan --changed",)
        ),
        data=data,
    )
    emit(result, json_output, enforce=False)
