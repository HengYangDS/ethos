"""Public Commitment rebind derivation and receipt execution commands."""

from __future__ import annotations

from typing import Annotated
from typing import cast

from cyclopts import App
from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.commitment_rebind import execute_commitment_rebind
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind import (
    execute_commitment_rebind_receipt,
)
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_derivation import (
    derive_commitment_rebind,
)
from ethos.contracts.coordination import CommitmentRebindRequest
from ethos.normalization.coercion import integer
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_app = App(
    name="rebind-commitment",
    help="Derive or apply one exact Commitment replacement.",
)
lane_app.command(_app)


class _CommitmentRebind(AppliedLaneCommandOptions):
    command = "lane rebind-commitment"
    operation: Annotated[str, Parameter(name="--operation")] = "commitment-rebind"
    branch: Annotated[str, Parameter(name="--branch")]
    holder_ref: Annotated[str, Parameter(name="--holder-ref")]
    lease_id: Annotated[str, Parameter(name="--lease-id")]
    expected_lane_incarnation_id: Annotated[str, Parameter(name="--expected-lane-incarnation-id")]
    expected_epoch: Annotated[int, Parameter(name="--expected-epoch")]
    expected_issued_at: Annotated[str, Parameter(name="--expected-issued-at")]
    expected_renewed_at: Annotated[str, Parameter(name="--expected-renewed-at")]
    expected_expires_at: Annotated[str, Parameter(name="--expected-expires-at")]
    expected_payload_sha256: Annotated[str, Parameter(name="--expected-payload-sha256")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]
    expected_tree: Annotated[str, Parameter(name="--expected-tree")]
    expected_commitment_path: Annotated[str, Parameter(name="--expected-commitment-path")]
    expected_commitment_bytes_sha256: Annotated[
        str, Parameter(name="--expected-commitment-bytes-sha256")
    ]
    expected_commitment_digest: Annotated[str, Parameter(name="--expected-commitment-digest")]
    expect_index_tree: Annotated[str, Parameter(name="--expect-index-tree")]
    expected_working_overlay_sha256: Annotated[
        str, Parameter(name="--expected-working-overlay-sha256")
    ]
    target_commit: Annotated[str, Parameter(name="--target-commit")]
    new_commitment_path: Annotated[str, Parameter(name="--new-commitment-path")]
    new_commitment_bytes_sha256: Annotated[str, Parameter(name="--new-commitment-bytes-sha256")]
    new_commitment_digest: Annotated[str, Parameter(name="--new-commitment-digest")]
    old_repository_commitment_path: Annotated[
        str, Parameter(name="--old-repository-commitment-path")
    ] = ".ethos/commitment.toml"
    old_repository_commitment_bytes_sha256: Annotated[
        str, Parameter(name="--old-repository-commitment-bytes-sha256")
    ] = "0" * 64
    old_repository_id: Annotated[str, Parameter(name="--old-repository-id")] = ""
    new_repository_commitment_path: Annotated[
        str, Parameter(name="--new-repository-commitment-path")
    ] = ".ethos/commitment.toml"
    new_repository_commitment_bytes_sha256: Annotated[
        str, Parameter(name="--new-repository-commitment-bytes-sha256")
    ] = "0" * 64
    new_repository_commitment_digest: Annotated[
        str, Parameter(name="--new-repository-commitment-digest")
    ] = "0" * 64
    repair_change_identity: Annotated[bool, Parameter(name="--repair-change-identity")] = False
    expected_path_scope: Annotated[tuple[str, ...], Parameter(name="--expected-path-scope")] = ()


class _CommitmentRebindReceipt(AppliedLaneCommandOptions):
    command = "lane rebind-commitment"
    receipt: Annotated[str, Parameter(name="--receipt")]
    receipt_sha256: Annotated[str, Parameter(name="--receipt-sha256")] = ""


@_app.default
def lane_rebind_commitment(
    options: Annotated[_CommitmentRebindReceipt, Parameter(name="*")],
) -> None:
    """Revalidate and apply one derived Commitment request receipt."""
    report = execute_commitment_rebind_receipt(
        root=resolve_root(options.root),
        receipt_path=options.receipt,
        receipt_sha256=options.receipt_sha256,
        apply=options.apply,
    )
    project_lane_result(
        options.command,
        report,
        enforce=options.apply,
        json_output=options.json_output,
    )


@_app.command(name="exact")
def lane_rebind_commitment_exact(
    options: Annotated[_CommitmentRebind, Parameter(name="*")],
) -> None:
    """Execute one fully specified internal exact-CAS request."""
    values = options.model_dump(exclude={"root", "json_output"})
    report = execute_commitment_rebind(
        root=resolve_root(options.root),
        request=CommitmentRebindRequest.model_validate(values),
    )
    project_lane_result(
        options.command,
        report,
        summary={
            "branch": report["branch"],
            "epoch": integer(cast("dict[str, object]", report.get("lease") or {}).get("epoch")),
        },
        enforce=options.apply,
        json_output=options.json_output,
    )


@_app.command(name="derive")
def lane_rebind_commitment_derive(
    target_commit: Annotated[str, Parameter(name="--target-commit")] = "",
    *,
    root: RootOption | None = None,
    repair_change_identity: Annotated[bool, Parameter(name="--repair-change-identity")] = False,
    operation: Annotated[
        str, Parameter(name="--operation", help="Exact rebind operation discriminator.")
    ] = "commitment-rebind",
    json_output: Annotated[bool, Parameter(name="--json")] = False,
) -> None:
    """Derive and persist one exact request receipt without mutation."""
    report = derive_commitment_rebind(
        root=resolve_root(root),
        target_commit=target_commit,
        repair_change_identity=repair_change_identity,
        operation=operation,
    )
    project_lane_result(
        "lane rebind-commitment derive",
        report,
        json_output=json_output,
    )
