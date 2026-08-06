"""Generation-bound Lane Lease commands and request projection."""

import pathlib
from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import Literal
from typing import cast

from cyclopts import Parameter
from pydantic import BaseModel
from pydantic import ConfigDict

from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_operation
from ethos.adapters.mutation.lane_lifecycle.lease import execute_lease_takeover
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import LeaseTakeoverRequest
from ethos.contracts.semantic import Attestation
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult
from ethos.surface.cli.application import lane_lease_app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


class LeaseCommandOptions(BaseModel):
    """Fields shared by lease-backed Cyclopts commands."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    apply: bool = False
    root: RootOption | None = None
    json_output: JsonFlag = False


class LeaseProofOptions(LeaseCommandOptions):
    """Exact generation proof required by lease transitions."""

    lease_id: Annotated[str, Parameter(name="--lease-id")]
    epoch: Annotated[int, Parameter(name="--epoch")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]
    expected_expires_at: Annotated[str, Parameter(name="--expires-at")]
    expected_payload_sha256: Annotated[str, Parameter(name="--payload-sha256")]


class DeclaredLeaseOperationOptions(LeaseProofOptions):
    """A named lease operation bound to one branch."""

    command: ClassVar[str] = ""
    operation: ClassVar[str] = ""

    branch: Annotated[str, Parameter(name="--branch")]


class LeaseHolderOperationOptions(DeclaredLeaseOperationOptions):
    """A branch lease operation bound to its current holder."""

    holder_ref: Annotated[str, Parameter(name="--holder-ref")]


class _RenewOptions(LeaseHolderOperationOptions):
    command = "lane lease renew"
    operation = "renew"

    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400


class _ResumeOptions(_RenewOptions):
    command = "lane lease resume"
    operation = "resume"

    contrary_decision: Annotated[bool, Parameter(name="--contrary-decision-present")] = False


class TakeoverOptions(LeaseProofOptions):
    """Exact accepted authorization for one exceptional holder change."""

    branch: Annotated[str, Parameter(name="--branch")]
    source_holder_ref: Annotated[str, Parameter(name="--source-holder-ref")]
    target_holder_ref: Annotated[str, Parameter(name="--target-holder-ref")]
    expected_lane_incarnation_id: Annotated[str, Parameter(name="--lane-incarnation-id")]
    expected_tree: Annotated[str, Parameter(name="--expect-tree")]
    expected_dirty_content_sha256: Annotated[str, Parameter(name="--dirty-content-sha256")]
    source_state: Annotated[Literal["quiesced", "source_lost"], Parameter(name="--source-state")]
    authorization: Annotated[pathlib.Path, Parameter(name="--authorization")]
    ttl_seconds: Annotated[int, Parameter(name="--ttl-seconds")] = 86_400


def emit_lease_result(command: str, report: dict[str, object], *, json_output: bool) -> None:
    """Project one lease transition through the command result contract."""
    lease = report.get("lease")
    offer = report.get("handoff_offer")
    summary_source = lease if isinstance(lease, dict) and lease else offer
    summary_payload = summary_source if isinstance(summary_source, dict) else {}
    emit(
        EthosResult(
            command=command,
            verdict=cast("Any", report["verdict"]),
            state=str(report["state"]),
            summary={
                "branch": report["branch"],
                "lease_id": str(summary_payload.get("lease_id") or ""),
                "epoch": integer(summary_payload.get("epoch")),
                "holder_ref": str(summary_payload.get("holder_ref") or ""),
            },
            diagnostics=tuple(
                cast("dict[str, Any]", item)
                for item in object_sequence(report.get("diagnostics"))
                if isinstance(item, dict)
            ),
            required_gaps=tuple(string_sequence(report.get("required_gaps"))),
            next_action="ethos lane status --json" if report["verdict"] == "pass" else "",
            data=report,
        ),
        json_output=json_output,
    )


def execute_declared_lease_operation(options: DeclaredLeaseOperationOptions) -> None:
    """Compile declared options into the strict lease request contract."""
    values = options.model_dump(exclude={"root", "json_output"})
    values["expected_epoch"] = values.pop("epoch")
    report = execute_lease_operation(
        root=resolve_root(options.root),
        request=LeaseOperationRequest(operation=options.operation, **values),
    )
    emit_lease_result(options.command, report, json_output=options.json_output)


@lane_lease_app.command(name="renew")
def lane_lease_renew(options: Annotated[_RenewOptions, Parameter(name="*")]) -> None:
    """Renew one exact unexpired local lease generation."""
    execute_declared_lease_operation(options)


@lane_lease_app.command(name="resume")
def lane_lease_resume(options: Annotated[_ResumeOptions, Parameter(name="*")]) -> None:
    """Resume an expired lease for the same holder and generation."""
    execute_declared_lease_operation(options)


@lane_lease_app.command(name="takeover")
def lane_lease_takeover(options: Annotated[TakeoverOptions, Parameter(name="*")]) -> None:
    """Apply one accepted exact-CAS Lease takeover without transcript authority."""
    report = execute_lease_takeover(
        root=resolve_root(options.root),
        request=LeaseTakeoverRequest(
            branch=options.branch,
            source_holder_ref=options.source_holder_ref,
            target_holder_ref=options.target_holder_ref,
            lease_id=options.lease_id,
            expected_lane_incarnation_id=options.expected_lane_incarnation_id,
            expected_epoch=options.epoch,
            expect_head=options.expect_head,
            expected_tree=options.expected_tree,
            expected_expires_at=options.expected_expires_at,
            expected_payload_sha256=options.expected_payload_sha256,
            expected_dirty_content_sha256=options.expected_dirty_content_sha256,
            source_state=options.source_state,
            authorization=Attestation.model_validate_json(
                options.authorization.read_text(encoding="utf-8")
            ),
            ttl_seconds=options.ttl_seconds,
            apply=options.apply,
        ),
    )
    emit_lease_result("lane lease takeover", report, json_output=options.json_output)
