"""Generation-bound Lane Lease lifecycle commands."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from functools import wraps
from inspect import signature
from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import Annotated
from typing import Any

from cyclopts import Parameter

import ethos.adapters.mutation.lane_lifecycle.handoff.core as handoff
import ethos.adapters.mutation.lane_lifecycle.lease as leases
import ethos.surface.cli._base as cli
import ethos_core.normalization.core as normalization
from ethos_core.result import EthosResult

ContraryFlag = Annotated[bool, Parameter(name="--contrary-decision-present")]


@Parameter(name="*")
@dataclass(frozen=True, slots=True, kw_only=True)
class _CommandOptions:
    apply: bool = False
    root: cli.RootOption | None = None
    json_output: cli.JsonFlag = False


@dataclass(frozen=True, slots=True, kw_only=True)
class _GenerationOptions(_CommandOptions):
    lease_id: str
    epoch: int
    expect_head: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _LaneOptions(_GenerationOptions):
    branch: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _HolderLaneOptions(_LaneOptions):
    holder_ref: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _RenewOptions(_HolderLaneOptions):
    ttl_seconds: int = 86_400


@dataclass(frozen=True, slots=True, kw_only=True)
class _ResumeOptions(_RenewOptions):
    contrary_decision: ContraryFlag = False


@dataclass(frozen=True, slots=True, kw_only=True)
class _OfferOptions(_HolderLaneOptions):
    target_holder_ref: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _AcceptOptions(_LaneOptions):
    target_holder_ref: str
    offer_id: str
    ttl_seconds: int = 86_400
    confirm_holder_quiesced: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class _ExportOptions(_OfferOptions):
    context_text: str = ""
    context_file: Path | None = None
    output_root: Path | None = None
    dirty_disposition: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class _ImportOptions(_CommandOptions):
    package: Path
    target_holder_ref: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _RevokeOptions(_GenerationOptions):
    package: Path
    acknowledgement: Path
    holder_ref: str


def _emit_lease_result(command: str, report: dict[str, object], *, json_output: bool) -> None:
    lease = report.get("lease")
    source = lease if isinstance(lease, dict) and lease else report.get("handoff_offer")
    summary = source if isinstance(source, dict) else {}
    result = EthosResult(
        command=command,
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "lease_id": str(summary.get("lease_id") or ""),
            "epoch": normalization.integer(summary.get("epoch")),
            "holder_ref": str(summary.get("holder_ref") or ""),
        },
        required_gaps=tuple(normalization.string_sequence(report.get("required_gaps"))),
        next_actions=("ethos lane status --json",) if report["ok"] else (),
        data=report,
    )
    cli.emit(result, json_output=json_output)


def _invoke(command: str, operation: Any, options: _CommandOptions) -> None:
    payload = asdict(options)
    json_output = bool(payload.pop("json_output"))
    payload["root"] = cli.resolve_root(payload["root"])
    if "confirm_holder_quiesced" in payload:
        payload["holder_quiesced"] = payload.pop("confirm_holder_quiesced")
    _emit_lease_result(command, operation(**payload), json_output=json_output)


def _command(app: Any, name: str, options: Any) -> Any:
    def decorate(handler: Any) -> Any:
        app.command(name=name)(handler)
        wrapped = wraps(handler)(lambda **kwargs: handler(options(**kwargs)))
        vars(wrapped)["__signature__"] = signature(options)
        return wrapped

    return decorate


@_command(cli.lane_lease_app, "renew", _RenewOptions)
def lane_lease_renew(options: _RenewOptions) -> None:
    """Renew one exact unexpired local lease generation."""
    _invoke("lane lease renew", leases.renew_work_lane_lease, options)


@_command(cli.lane_lease_app, "resume", _ResumeOptions)
def lane_lease_resume(options: _ResumeOptions) -> None:
    """Resume an expired lease for the same holder and generation."""
    _invoke("lane lease resume", leases.resume_work_lane_lease, options)


@_command(cli.lane_handoff_app, "offer", _OfferOptions)
def lane_handoff_offer(options: _OfferOptions) -> None:
    """Offer one same-common-directory holder handoff."""
    _invoke("lane handoff offer", leases.offer_work_lane_handoff, options)


@_command(cli.lane_handoff_app, "accept", _AcceptOptions)
def lane_handoff_accept(options: _AcceptOptions) -> None:
    """Accept one exact handoff offer after explicit quiescence confirmation."""
    _invoke("lane handoff accept", leases.accept_work_lane_handoff, options)


@_command(cli.lane_handoff_app, "export", _ExportOptions)
def lane_handoff_export(options: _ExportOptions) -> None:
    """Export content-addressed Git/context state for another common directory."""
    _invoke("lane handoff export", handoff.export_cross_host_handoff, options)


@_command(cli.lane_handoff_app, "import", _ImportOptions)
def lane_handoff_import(options: _ImportOptions) -> None:
    """Import a verified package and create destination-local coordination."""
    _invoke("lane handoff import", handoff.import_cross_host_handoff, options)


@_command(cli.lane_handoff_app, "revoke-source", _RevokeOptions)
def lane_handoff_revoke_source(options: _RevokeOptions) -> None:
    """Revoke the exact source lease after destination acknowledgement."""
    _invoke("lane handoff revoke-source", handoff.revoke_cross_host_source, options)
