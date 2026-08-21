"""Public Commitment rebind derivation and receipt execution commands."""

from __future__ import annotations

from typing import Annotated

from cyclopts import App
from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.commitment_rebind import (
    execute_commitment_rebind_receipt,
)
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_derivation import (
    derive_commitment_rebind,
)
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


@_app.command(name="derive")
def lane_rebind_commitment_derive(
    target_commit: Annotated[str, Parameter(name="--target-commit")] = "",
    *,
    root: RootOption | None = None,
    repair_change_identity: Annotated[bool, Parameter(name="--repair-change-identity")] = False,
    json_output: Annotated[bool, Parameter(name="--json")] = False,
) -> None:
    """Derive and persist one exact request receipt without mutation."""
    report = derive_commitment_rebind(
        root=resolve_root(root),
        target_commit=target_commit,
        repair_change_identity=repair_change_identity,
    )
    project_lane_result(
        "lane rebind-commitment derive",
        report,
        json_output=json_output,
    )
