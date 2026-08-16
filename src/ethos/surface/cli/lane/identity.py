"""Public command for exact Git commit identity replacement."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated

from cyclopts import App
from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.identity_repair import derive_identity_repair_suffix
from ethos.adapters.mutation.lane_lifecycle.identity_repair import execute_identity_repair_suffix
from ethos.adapters.mutation.lane_lifecycle.identity_repair import repair_commit_identity
from ethos.adapters.repo.commit_identity import authorize_configured_commit_signer
from ethos.adapters.repo.commit_identity import commit_trust_setup_action
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


_identity_app = App(
    name="repair-identity",
    help="Derive or apply one exact commit-identity replacement.",
)
lane_app.command(_identity_app)


class IdentityRepairOptions(AppliedLaneCommandOptions):
    command = "lane repair-identity"
    old_commit: Annotated[str, Parameter(name="--old-commit")] = ""
    new_commit: Annotated[str, Parameter(name="--new-commit")] = ""
    expect_head: Annotated[str, Parameter(name="--expect-head")] = ""
    receipt: Annotated[str, Parameter(name="--receipt")] = ""
    receipt_sha256: Annotated[str, Parameter(name="--receipt-sha256")] = ""
    authorize: bool = False


class CommitSignerTrustOptions(AppliedLaneCommandOptions):
    command = "lane trust-commit-signer"
    target_commit: Annotated[str, Parameter(name="--target-commit")]
    expected_anchor_sha256: Annotated[str, Parameter(name="--expected-anchor-sha256")]
    authorize: bool = False


_DEFAULT_IDENTITY_REPAIR_OPTIONS = IdentityRepairOptions()


def _trust_action(
    root: Path, target_commit: str, report: dict[str, object], verdict: Verdict
) -> str:
    if verdict == "pass" and report.get("state") == "signer_authorized":
        return "rerun the exact blocked identity-repair command"
    return commit_trust_setup_action(root, target_commit)


@_identity_app.default
def repair_identity(
    options: Annotated[IdentityRepairOptions, Parameter(name="*")] = (
        _DEFAULT_IDENTITY_REPAIR_OPTIONS
    ),
) -> None:
    """Apply one single-commit or receipt-bound suffix identity replacement."""
    root = resolve_root(options.root)
    report = (
        execute_identity_repair_suffix(
            root=root,
            receipt_path=options.receipt,
            receipt_sha256=options.receipt_sha256,
            apply=options.apply,
            authorized=options.authorize,
        )
        if options.receipt
        else repair_commit_identity(
            root=root,
            old_commit=options.old_commit,
            new_commit=options.new_commit,
            expect_head=options.expect_head,
            apply=options.apply,
            authorized=options.authorize,
        )
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


@lane_app.command(name="trust-commit-signer")
def trust_commit_signer(options: Annotated[CommitSignerTrustOptions, Parameter(name="*")]) -> None:
    """Authorize Git's configured signer for one exact signed commit."""
    root = resolve_root(options.root)
    report = authorize_configured_commit_signer(
        root,
        options.target_commit,
        expected_anchor_sha256=options.expected_anchor_sha256,
        apply=options.apply,
        authorized=options.authorize,
    )
    project_lane_result(
        options.command,
        report,
        actions=lambda current, verdict: _trust_action(
            root, options.target_commit, current, verdict
        ),
        enforce=options.apply,
        json_output=options.json_output,
    )
