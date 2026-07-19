"""Campaign command group — evolution campaign status, hypotheses, closeout."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Cyclopts resolves CLI annotations at import time.
from typing import Annotated
from typing import Any
from typing import cast

from cyclopts import Parameter

from ethos.domain.campaign.closeout import campaign_closeout_report
from ethos.domain.campaign.closeout import campaign_publication_report
from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_ledger
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import campaign_app
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.commands import load_command_registry_declaration
from ethos_core.result import EthosResult

_ACTIONS = load_command_registry_declaration().actions


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
    publication = campaign_publication_report(repo)
    report["publication"] = publication
    required_gap_values = cast("tuple[object, ...]", report.get("required_gaps", ()))
    required_gaps = tuple(str(gap) for gap in required_gap_values)
    result = EthosResult(
        command="campaign status",
        ok=bool(report["ok"]),
        state="active",
        summary={
            "active_campaign_count": report["active_count"],
            "campaign_count": report["campaign_count"],
            "remote_publication_admission": publication["remote_publication_admission"],
        },
        required_gaps=required_gaps,
        next_actions=_ACTIONS.get(str(publication["next_action_id"]), ()),
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
        next_actions=_ACTIONS["campaign_hypotheses"],
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
    packages = cast("dict[str, Any]", report["packages"])
    campaign_package = cast("dict[str, Any]", packages["campaign"])
    campaign_publication = cast("dict[str, Any]", campaign_package["publication"])
    parity = cast("dict[str, Any]", report.get("parity", {}))
    release = cast("dict[str, Any]", report.get("release", {}))
    evolution = cast("dict[str, Any]", report.get("evolution", {}))
    parity_pending = cast("tuple[object, ...]", parity.get("pending_packages", ()))
    evolution_gap_values = cast("tuple[object, ...]", evolution.get("required_gaps", ()))
    release_gap_values = cast("tuple[object, ...]", release.get("required_gaps", ()))
    campaign_data = cast("dict[str, Any]", report.get("campaigns", {}))
    campaign_gap_values = cast("tuple[object, ...]", campaign_data.get("required_gaps", ()))
    evolution_gaps = tuple(str(gap) for gap in evolution_gap_values)
    release_gaps = tuple(str(gap) for gap in release_gap_values)
    campaign_gaps = tuple(str(gap) for gap in campaign_gap_values)
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
            "campaign_publication": campaign_publication["remote_publication_admission"],
        },
        required_gaps=evolution_gaps + release_gaps,
        next_actions=_ACTIONS.get(str(campaign_publication["next_action_id"]), ()),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)
