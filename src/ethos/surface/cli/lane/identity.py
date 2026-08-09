"""Public command for exact Git commit identity replacement."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.lane_lifecycle.identity_repair import repair_commit_identity
from ethos.adapters.repo.commit_identity import authorize_configured_commit_signer
from ethos.adapters.repo.commit_identity import commit_trust_setup_action
from ethos.surface.cli.application import lane_app
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import resolve_root

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


class IdentityRepairOptions(AppliedLaneCommandOptions):
    command = "lane repair-identity"
    old_commit: Annotated[str, Parameter(name="--old-commit")]
    new_commit: Annotated[str, Parameter(name="--new-commit")]
    expect_head: Annotated[str, Parameter(name="--expect-head")]
    authorize: bool = False


class CommitSignerTrustOptions(AppliedLaneCommandOptions):
    command = "lane trust-commit-signer"
    target_commit: Annotated[str, Parameter(name="--target-commit")]
    expected_anchor_sha256: Annotated[str, Parameter(name="--expected-anchor-sha256")]
    authorize: bool = False


def _trust_action(
    root: Path, target_commit: str, report: dict[str, object], verdict: Verdict
) -> str:
    if verdict == "pass" and report.get("state") == "signer_authorized":
        return "rerun the exact blocked identity-repair command"
    return commit_trust_setup_action(root, target_commit)


@lane_app.command(name="repair-identity")
def repair_identity(options: Annotated[IdentityRepairOptions, Parameter(name="*")]) -> None:
    """Replace one equivalent commit identity through the protected integration train."""
    report = repair_commit_identity(
        root=resolve_root(options.root),
        old_commit=options.old_commit,
        new_commit=options.new_commit,
        expect_head=options.expect_head,
        apply=options.apply,
        authorized=options.authorize,
    )
    project_lane_result(
        options.command,
        report,
        enforce=options.apply,
        json_output=options.json_output,
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
