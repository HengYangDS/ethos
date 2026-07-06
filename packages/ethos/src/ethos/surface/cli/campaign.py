"""Campaign command group — evolution campaign status, hypotheses, closeout."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Cyclopts resolves CLI annotations at import time.
from typing import Annotated

from cyclopts import Parameter

from ethos.domain import land as _land
from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_ledger
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import campaign_app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


@campaign_app.command(name="status")
def campaign_status(
    *,
    campaign: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report canonical campaign model."""
    repo = resolve_root(root)
    report = campaign_report(repo, campaign_id=campaign)
    result = EthosResult(
        command="campaign status",
        ok=bool(report["ok"]),
        state="active",
        summary={
            "active_campaign_count": report["active_count"],
            "campaign_count": report["campaign_count"],
        },
        required_gaps=tuple(report["required_gaps"]),
        next_actions=("ethos campaign closeout --json",),
        data=report,
    )
    emit(result, json_output, enforce=False)


@campaign_app.command
def hypotheses(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """List active ETHOS evolution hypotheses."""
    repo = resolve_root(root)
    ledger = evolution_ledger(repo)
    result = EthosResult(
        command="campaign hypotheses",
        ok=True,
        state="active",
        summary={"campaign": "ethos-product-maturation"},
        next_actions=("ethos audit --mode shape",),
        data=ledger,
    )
    emit(result, json_output, enforce=False)


@campaign_app.command(name="closeout")
def campaign_closeout(
    *,
    adopter: str = "generic",
    target: Annotated[Path | None, Parameter(name="--target")] = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report the local campaign closeout package without publishing remotely."""
    repo = resolve_root(root)
    report = _land.campaign_closeout_report(
        repo=repo,
        adopter=adopter,
        target=(target or repo).resolve(),
    )
    result = EthosResult(
        command="campaign closeout",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "adopter": adopter,
            "remote_state": report["remote_publication"]["state"],
            "parity_pending_count": len(report["parity"]["pending_packages"]),
            "release_ok": report["release"]["ok"],
        },
        required_gaps=tuple(report["evolution"]["required_gaps"])
        + tuple(report["release"]["required_gaps"]),
        next_actions=("ethos land --apply --authorize --expect-head <git-head>",),
        data=report,
    )
    emit(result, json_output, enforce=False)
