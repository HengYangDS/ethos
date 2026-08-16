"""Public receipt-bound command for exact Git commit identity replacement."""

from __future__ import annotations

from typing import Annotated

from cyclopts import App
from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.identity_repair import derive_identity_repair_suffix
from ethos.adapters.mutation.lane_lifecycle.identity_repair import execute_identity_repair_suffix
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_identity_app = App(
    name="repair-identity",
    help="Derive or apply one exact commit-identity replacement.",
)
lane_app.command(_identity_app)


class IdentityRepairOptions(AppliedLaneCommandOptions):
    command = "lane repair-identity"
    receipt: Annotated[str, Parameter(name="--receipt")] = ""
    receipt_sha256: Annotated[str, Parameter(name="--receipt-sha256")] = ""
    authorize: bool = False


_DEFAULT_IDENTITY_REPAIR_OPTIONS = IdentityRepairOptions()


@_identity_app.default
def repair_identity(
    options: Annotated[IdentityRepairOptions, Parameter(name="*")] = (
        _DEFAULT_IDENTITY_REPAIR_OPTIONS
    ),
) -> None:
    """Apply one immutable exact-CAS identity-repair receipt."""
    root = resolve_root(options.root)
    report = execute_identity_repair_suffix(
        root=root,
        receipt_path=options.receipt,
        receipt_sha256=options.receipt_sha256,
        apply=options.apply,
        authorized=options.authorize,
    )
    project_lane_result(
        options.command,
        report,
        enforce=options.apply,
        json_output=options.json_output,
    )


@_identity_app.command(name="derive")
def repair_identity_derive(
    base_commit: Annotated[str, Parameter(name="--base-commit")],
    *,
    root: RootOption | None = None,
    json_output: Annotated[bool, Parameter(name="--json")] = False,
) -> None:
    """Derive one immutable exact-CAS receipt for a linear suffix."""
    report = derive_identity_repair_suffix(
        root=resolve_root(root),
        base_commit=base_commit,
    )
    project_lane_result(
        "lane repair-identity derive",
        report,
        json_output=json_output,
    )
