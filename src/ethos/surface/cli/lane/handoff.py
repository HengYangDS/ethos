"""Local and cross-host Work Lane handoff commands."""

import pathlib
from typing import Annotated
from typing import ClassVar

from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import export_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import import_cross_host_handoff
from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import revoke_cross_host_source
from ethos.surface.cli.application import lane_handoff_app
from ethos.surface.cli.lane.lease import LeaseCommandOptions
from ethos.surface.cli.lane.lease import LeaseHolderOperationOptions
from ethos.surface.cli.lane.lease import LeaseProofOptions
from ethos.surface.cli.lane.lease import emit_lease_result
from ethos.surface.cli.lane.lease import execute_declared_lease_operation
from ethos.surface.cli.root_binding import resolve_root


class _OfferOptions(LeaseHolderOperationOptions):
    command = "lane handoff offer"
    operation = "handoff_offer"

    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")]


class _AcceptOptions(LeaseHolderOperationOptions):
    command = "lane handoff accept"
    operation = "handoff_accept"

    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")]
    offer_id: Annotated[str, Parameter(name="--offer-id")]
    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400
    holder_quiesced: Annotated[bool, Parameter(name="--confirm-holder-quiesced")] = False


class _ExportOptions(_OfferOptions):
    command = "lane handoff export"

    context_text: Annotated[str, Parameter(name="--context-text")] = ""
    context_file: Annotated[pathlib.Path | None, Parameter(name="--context-file")] = None
    output_root: Annotated[pathlib.Path | None, Parameter(name="--output-root")] = None


class _ImportOptions(LeaseCommandOptions):
    command: ClassVar[str] = "lane handoff import"

    package: Annotated[pathlib.Path, Parameter(name="--package")]
    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")]


class _RevokeOptions(LeaseProofOptions):
    command: ClassVar[str] = "lane handoff revoke-source"

    package: Annotated[pathlib.Path, Parameter(name="--package")]
    acknowledgement: Annotated[pathlib.Path, Parameter(name="--acknowledgement")]
    holder_ref: Annotated[str, Parameter(name="--holder-ref")]


@lane_handoff_app.command(name="offer")
def lane_handoff_offer(options: Annotated[_OfferOptions, Parameter(name="*")]) -> None:
    """Offer one same-common-directory holder handoff."""
    execute_declared_lease_operation(options)


@lane_handoff_app.command(name="accept")
def lane_handoff_accept(options: Annotated[_AcceptOptions, Parameter(name="*")]) -> None:
    """Accept one exact handoff offer after explicit quiescence confirmation."""
    execute_declared_lease_operation(options)


@lane_handoff_app.command(name="export")
def lane_handoff_export(options: Annotated[_ExportOptions, Parameter(name="*")]) -> None:
    """Export content-addressed Git/context state for another common directory."""
    values = options.model_dump(exclude={"root", "json_output"})
    report = export_cross_host_handoff(root=resolve_root(options.root), **values)
    emit_lease_result(options.command, report, json_output=options.json_output)


@lane_handoff_app.command(name="import")
def lane_handoff_import(options: Annotated[_ImportOptions, Parameter(name="*")]) -> None:
    """Import a verified package and create destination-local coordination."""
    values = options.model_dump(exclude={"root", "json_output"})
    report = import_cross_host_handoff(root=resolve_root(options.root), **values)
    emit_lease_result(options.command, report, json_output=options.json_output)


@lane_handoff_app.command(name="revoke-source")
def lane_handoff_revoke_source(options: Annotated[_RevokeOptions, Parameter(name="*")]) -> None:
    """Revoke the exact source lease after destination acknowledgement."""
    values = options.model_dump(exclude={"root", "json_output"})
    report = revoke_cross_host_source(root=resolve_root(options.root), **values)
    emit_lease_result(options.command, report, json_output=options.json_output)
