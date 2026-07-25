"""Campaign command group — evolution campaign status, hypotheses, closeout."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Cyclopts resolves CLI annotations at import time.
from typing import Annotated
from typing import Any
from typing import cast

from cyclopts import Parameter

from ethos.domain.campaign.closeout import campaign_closeout_report
from ethos.domain.campaign.closeout import campaign_status_report
from ethos.repository.adoption.evolution import evolution_ledger
from ethos.result import EthosResult
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import campaign_app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root


@campaign_app.command(name="status")
def campaign_status(
    *,
    campaign: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report canonical campaign model."""
    repo = resolve_root(root)
    report = campaign_status_report(repo, campaign_id=campaign)
    result = EthosResult(
        command="campaign status",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "active_campaign_count": report["active_count"],
            "campaign_count": report["campaign_count"],
        },
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=("ethos campaign closeout --json",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


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
    emit(result, json_output=json_output, enforce=False)


@campaign_app.command(name="closeout")
def campaign_closeout(
    *,
    campaign: str | None = None,
    adopter: str = "generic",
    target: Annotated[Path | None, Parameter(name="--target")] = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report the local campaign closeout package without publishing remotely."""
    repo = resolve_root(root)
    report = campaign_closeout_report(
        repo=repo,
        adopter=adopter,
        target=(target or repo).resolve(),
        campaign_id=campaign,
    )
    remote_publication = cast("dict[str, Any]", report.get("remote_publication", {}))
    parity = cast("dict[str, Any]", report.get("parity", {}))
    release = cast("dict[str, Any]", report.get("release", {}))
    parity_pending = cast("tuple[object, ...]", parity.get("pending_packages", ()))
    result = EthosResult(
        command="campaign closeout",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "adopter": adopter,
            "campaign": campaign or "",
            "remote_state": remote_publication.get("state", ""),
            "parity_pending_count": len(parity_pending),
            "release_ok": release.get("ok", False),
        },
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=("ethos land --apply --authorize --expect-head <git-head>",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)
