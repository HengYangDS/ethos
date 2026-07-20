"""Generation-bound Lane Lease lifecycle commands."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - Cyclopts needs runtime types in signatures
from typing import Annotated
from typing import ClassVar

from cyclopts import Parameter
from pydantic import BaseModel
from pydantic import ConfigDict

from ethos.adapters.mutation.lane_lifecycle.handoff.core import export_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.core import import_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.core import revoke_cross_host_source
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_operation
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import lane_handoff_app
from ethos.surface.cli._base import lane_lease_app
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.lifecycle.core import LeaseOperationRequest
from ethos_core.normalization.core import integer
from ethos_core.normalization.core import string_sequence
from ethos_core.result import EthosResult


class _CommandOptions(BaseModel):
    """Shared Cyclopts boundary fields compiled before strict lifecycle validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    apply: bool = False
    root: RootOption | None = None
    json_output: JsonFlag = False


class _GenerationOptions(_CommandOptions):
    command: ClassVar[str] = ""
    operation: ClassVar[str] = ""

    branch: Annotated[str, Parameter(name="--branch")]
    lease_id: Annotated[str, Parameter(name="--lease-id")]
    epoch: Annotated[int, Parameter(name="--epoch")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]


class _HolderOptions(_GenerationOptions):
    holder_ref: Annotated[str, Parameter(name="--holder-ref")]


class _RenewOptions(_HolderOptions):
    command = "lane lease renew"
    operation = "renew"

    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400


class _ResumeOptions(_RenewOptions):
    command = "lane lease resume"
    operation = "resume"

    contrary_decision: Annotated[bool, Parameter(name="--contrary-decision-present")] = False


class _OfferOptions(_HolderOptions):
    command = "lane handoff offer"
    operation = "handoff_offer"

    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")]


class _AcceptOptions(_GenerationOptions):
    command = "lane handoff accept"
    operation = "handoff_accept"

    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")]
    offer_id: Annotated[str, Parameter(name="--offer-id")]
    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400
    holder_quiesced: Annotated[bool, Parameter(name="--confirm-holder-quiesced")] = False


class _ExportOptions(_OfferOptions):
    command = "lane handoff export"

    context_text: Annotated[str, Parameter(name="--context-text")] = ""
    context_file: Annotated[Path | None, Parameter(name="--context-file")] = None
    output_root: Annotated[Path | None, Parameter(name="--output-root")] = None
    dirty_disposition: Annotated[str | None, Parameter(name="--dirty-disposition")] = None


class _ImportOptions(_CommandOptions):
    command: ClassVar[str] = "lane handoff import"

    package: Annotated[Path, Parameter(name="--package")]
    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")]


class _RevokeOptions(_CommandOptions):
    command: ClassVar[str] = "lane handoff revoke-source"

    package: Annotated[Path, Parameter(name="--package")]
    acknowledgement: Annotated[Path, Parameter(name="--acknowledgement")]
    holder_ref: Annotated[str, Parameter(name="--holder-ref")]
    lease_id: Annotated[str, Parameter(name="--lease-id")]
    epoch: Annotated[int, Parameter(name="--epoch")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]


def _emit_lease_result(command: str, report: dict[str, object], *, json_output: bool) -> None:
    """Project one lease operation through the shared command result contract."""
    lease = report.get("lease")
    offer = report.get("handoff_offer")
    summary_source = lease if isinstance(lease, dict) and lease else offer
    summary_payload = summary_source if isinstance(summary_source, dict) else {}
    result = EthosResult(
        command=command,
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "branch": report["branch"],
            "lease_id": str(summary_payload.get("lease_id") or ""),
            "epoch": integer(summary_payload.get("epoch")),
            "holder_ref": str(summary_payload.get("holder_ref") or ""),
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=("ethos lane status --json",) if report["ok"] else (),
        data=report,
    )
    emit(result, json_output=json_output)


def _run_lease(options: _GenerationOptions) -> None:
    """Compile one Cyclopts model into the strict declaration-owned request."""
    values = options.model_dump(exclude={"root", "json_output"})
    values["expected_epoch"] = values.pop("epoch")
    values.setdefault("holder_ref", str(values.get("target_holder_ref") or ""))
    report = execute_lease_operation(
        root=resolve_root(options.root),
        request=LeaseOperationRequest(operation=options.operation, **values),
    )
    _emit_lease_result(options.command, report, json_output=options.json_output)


@lane_lease_app.command(name="renew")
def lane_lease_renew(options: Annotated[_RenewOptions, Parameter(name="*")]) -> None:
    """Renew one exact unexpired local lease generation."""
    _run_lease(options)


@lane_lease_app.command(name="resume")
def lane_lease_resume(options: Annotated[_ResumeOptions, Parameter(name="*")]) -> None:
    """Resume an expired lease for the same holder and generation."""
    _run_lease(options)


@lane_handoff_app.command(name="offer")
def lane_handoff_offer(options: Annotated[_OfferOptions, Parameter(name="*")]) -> None:
    """Offer one same-common-directory holder handoff."""
    _run_lease(options)


@lane_handoff_app.command(name="accept")
def lane_handoff_accept(options: Annotated[_AcceptOptions, Parameter(name="*")]) -> None:
    """Accept one exact handoff offer after explicit quiescence confirmation."""
    _run_lease(options)


@lane_handoff_app.command(name="export")
def lane_handoff_export(options: Annotated[_ExportOptions, Parameter(name="*")]) -> None:
    """Export content-addressed Git/context state for another common directory."""
    values = options.model_dump(exclude={"root", "json_output"})
    report = export_cross_host_handoff(root=resolve_root(options.root), **values)
    _emit_lease_result(options.command, report, json_output=options.json_output)


@lane_handoff_app.command(name="import")
def lane_handoff_import(options: Annotated[_ImportOptions, Parameter(name="*")]) -> None:
    """Import a verified package and create destination-local coordination."""
    values = options.model_dump(exclude={"root", "json_output"})
    report = import_cross_host_handoff(root=resolve_root(options.root), **values)
    _emit_lease_result(options.command, report, json_output=options.json_output)


@lane_handoff_app.command(name="revoke-source")
def lane_handoff_revoke_source(options: Annotated[_RevokeOptions, Parameter(name="*")]) -> None:
    """Revoke the exact source lease after destination acknowledgement."""
    values = options.model_dump(exclude={"root", "json_output"})
    report = revoke_cross_host_source(root=resolve_root(options.root), **values)
    _emit_lease_result(options.command, report, json_output=options.json_output)
