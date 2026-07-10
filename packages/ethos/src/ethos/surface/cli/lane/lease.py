"""Generation-bound Lane Lease lifecycle commands."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.handoff.core import export_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.core import import_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.core import revoke_cross_host_source
from ethos.adapters.mutation.lane_lifecycle.lease import accept_work_lane_handoff
from ethos.adapters.mutation.lane_lifecycle.lease import normalize_work_lane_lease
from ethos.adapters.mutation.lane_lifecycle.lease import offer_work_lane_handoff
from ethos.adapters.mutation.lane_lifecycle.lease import renew_work_lane_lease
from ethos.adapters.mutation.lane_lifecycle.lease import resume_work_lane_lease
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import lane_handoff_app
from ethos.surface.cli._base import lane_lease_app
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


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
            "epoch": int(summary_payload.get("epoch") or 0),
            "holder_ref": str(summary_payload.get("holder_ref") or ""),
        },
        required_gaps=tuple(str(gap) for gap in report["required_gaps"]),
        next_actions=("ethos lane status --json",) if report["ok"] else (),
        data=report,
    )
    emit(result, json_output=json_output)


@lane_lease_app.command(name="normalize")
def lane_lease_normalize(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    holder_ref: Annotated[str, Parameter(name="--holder-ref")],
    lease_id: Annotated[str, Parameter(name="--lease-id")],
    expect_head: Annotated[str, Parameter(name="--expect-head")],
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Normalize one exact unambiguous legacy lease observation."""
    report = normalize_work_lane_lease(
        root=resolve_root(root),
        branch=branch,
        holder_ref=holder_ref,
        lease_id=lease_id,
        expect_head=expect_head,
        apply=apply,
    )
    _emit_lease_result("lane lease normalize", report, json_output=json_output)


@lane_lease_app.command(name="renew")
def lane_lease_renew(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    holder_ref: Annotated[str, Parameter(name="--holder-ref")],
    lease_id: Annotated[str, Parameter(name="--lease-id")],
    epoch: Annotated[int, Parameter(name="--epoch")],
    expect_head: Annotated[str, Parameter(name="--expect-head")],
    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Renew one exact unexpired local lease generation."""
    report = renew_work_lane_lease(
        root=resolve_root(root),
        branch=branch,
        holder_ref=holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        ttl_seconds=ttl_seconds,
        apply=apply,
    )
    _emit_lease_result("lane lease renew", report, json_output=json_output)


@lane_lease_app.command(name="resume")
def lane_lease_resume(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    holder_ref: Annotated[str, Parameter(name="--holder-ref")],
    lease_id: Annotated[str, Parameter(name="--lease-id")],
    epoch: Annotated[int, Parameter(name="--epoch")],
    expect_head: Annotated[str, Parameter(name="--expect-head")],
    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400,
    contrary_decision: Annotated[bool, Parameter(name="--contrary-decision-present")] = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Resume an expired lease for the same holder and generation."""
    report = resume_work_lane_lease(
        root=resolve_root(root),
        branch=branch,
        holder_ref=holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        ttl_seconds=ttl_seconds,
        contrary_decision=contrary_decision,
        apply=apply,
    )
    _emit_lease_result("lane lease resume", report, json_output=json_output)


@lane_handoff_app.command(name="offer")
def lane_handoff_offer(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    holder_ref: Annotated[str, Parameter(name="--holder-ref")],
    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")],
    lease_id: Annotated[str, Parameter(name="--lease-id")],
    epoch: Annotated[int, Parameter(name="--epoch")],
    expect_head: Annotated[str, Parameter(name="--expect-head")],
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Offer one same-common-directory holder handoff."""
    report = offer_work_lane_handoff(
        root=resolve_root(root),
        branch=branch,
        holder_ref=holder_ref,
        target_holder_ref=target_holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        apply=apply,
    )
    _emit_lease_result("lane handoff offer", report, json_output=json_output)


@lane_handoff_app.command(name="accept")
def lane_handoff_accept(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")],
    offer_id: Annotated[str, Parameter(name="--offer-id")],
    lease_id: Annotated[str, Parameter(name="--lease-id")],
    epoch: Annotated[int, Parameter(name="--epoch")],
    expect_head: Annotated[str, Parameter(name="--expect-head")],
    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400,
    confirm_holder_quiesced: Annotated[bool, Parameter(name="--confirm-holder-quiesced")] = False,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Accept one exact handoff offer after explicit quiescence confirmation."""
    report = accept_work_lane_handoff(
        root=resolve_root(root),
        branch=branch,
        target_holder_ref=target_holder_ref,
        offer_id=offer_id,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        holder_quiesced=confirm_holder_quiesced,
        ttl_seconds=ttl_seconds,
        apply=apply,
    )
    _emit_lease_result("lane handoff accept", report, json_output=json_output)


@lane_handoff_app.command(name="export")
def lane_handoff_export(
    *,
    branch: Annotated[str, Parameter(name="--branch")],
    holder_ref: Annotated[str, Parameter(name="--holder-ref")],
    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")],
    lease_id: Annotated[str, Parameter(name="--lease-id")],
    epoch: Annotated[int, Parameter(name="--epoch")],
    expect_head: Annotated[str, Parameter(name="--expect-head")],
    context_text: Annotated[str, Parameter(name="--context-text")] = "",
    context_file: Annotated[Path | None, Parameter(name="--context-file")] = None,
    output_root: Annotated[Path | None, Parameter(name="--output-root")] = None,
    dirty_disposition: Annotated[str | None, Parameter(name="--dirty-disposition")] = None,
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Export content-addressed Git/context state for another common directory."""
    report = export_cross_host_handoff(
        root=resolve_root(root),
        branch=branch,
        holder_ref=holder_ref,
        target_holder_ref=target_holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        context_text=context_text,
        context_file=context_file,
        output_root=output_root,
        dirty_disposition=dirty_disposition,
        apply=apply,
    )
    _emit_lease_result("lane handoff export", report, json_output=json_output)


@lane_handoff_app.command(name="import")
def lane_handoff_import(
    *,
    package: Annotated[Path, Parameter(name="--package")],
    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")],
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Import a verified package and create destination-local coordination."""
    report = import_cross_host_handoff(
        root=resolve_root(root),
        package=package,
        target_holder_ref=target_holder_ref,
        apply=apply,
    )
    _emit_lease_result("lane handoff import", report, json_output=json_output)


@lane_handoff_app.command(name="revoke-source")
def lane_handoff_revoke_source(
    *,
    package: Annotated[Path, Parameter(name="--package")],
    acknowledgement: Annotated[Path, Parameter(name="--acknowledgement")],
    holder_ref: Annotated[str, Parameter(name="--holder-ref")],
    lease_id: Annotated[str, Parameter(name="--lease-id")],
    epoch: Annotated[int, Parameter(name="--epoch")],
    expect_head: Annotated[str, Parameter(name="--expect-head")],
    apply: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Revoke the exact source lease after destination acknowledgement."""
    report = revoke_cross_host_source(
        root=resolve_root(root),
        package=package,
        acknowledgement=acknowledgement,
        holder_ref=holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        expect_head=expect_head,
        apply=apply,
    )
    _emit_lease_result("lane handoff revoke-source", report, json_output=json_output)
