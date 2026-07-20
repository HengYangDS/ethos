"""Intake command group — adopter intake-ledger readiness.

A surface command module: binds args, calls the land-stage projection, emits.
Registers onto the shared intake_app from _base; cli.py imports this module so the
decorator runs. Imports only what this group needs.
"""

from __future__ import annotations

from ethos.domain.land.intake.core import intake_mine_report
from ethos.domain.land.intake.core import intake_projection_report
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
    projection = intake_projection_report(repo)
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
            ("ethos adopt --json",) if not projection["configured"] else ("ethos plan --changed",)
        ),
        data=data,
    )
    emit(result, json_output=json_output, enforce=False)


@intake_app.command(name="mine")
def intake_mine(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Mine repository signals into governed issue candidates without mutation."""
    repo = resolve_root(root)
    report = intake_mine_report(repo)
    summary = report["summary"]
    result = EthosResult(
        command="intake mine",
        ok=True,
        state=str(report["state"]),
        summary=summary if isinstance(summary, dict) else {},
        required_gaps=tuple(str(gap) for gap in report["required_gaps"]),
        next_actions=("ethos intake status --json",),
        data={
            "truth_boundary": report["truth_boundary"],
            "repository_truth": report["repository_truth"],
            "writes": report["writes"],
            "intake_envelopes": report["intake_envelopes"],
            "issue_candidates": report["issue_candidates"],
        },
    )
    emit(result, json_output=json_output, enforce=False)
