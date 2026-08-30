"""Public authorization command for the configured Git commit signer."""

from __future__ import annotations

from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.repo.git_object import authorize_configured_commit_signer
from ethos.surface.cli.lane.lifecycle import AppliedLaneCommandOptions
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.root_binding import resolve_root


class CommitSignerTrustOptions(AppliedLaneCommandOptions):
    command = "lane trust-commit-signer"
    target_commit: Annotated[str, Parameter(name="--target-commit")]
    expected_anchor_sha256: Annotated[str, Parameter(name="--expected-anchor-sha256")]
    authorize: bool = False


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
        enforce=options.apply,
        json_output=options.json_output,
    )
