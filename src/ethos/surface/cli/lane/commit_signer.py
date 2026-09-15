"""Public commands for signer authorization and bounded accepted-history repair."""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.mutation.accepted.signature import repair_signature
from ethos.adapters.repo.git_object import authorize_configured_commit_signer
from ethos.contracts.semantic import parse_semantic_json
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


class SignatureRepairOptions(AppliedLaneCommandOptions):
    command = "lane repair-signature"
    expect_head: Annotated[str, Parameter(name="--expect-head")]
    replacement: str = ""
    corrections: Path | None = None
    corrections_sha256: str = ""
    reason: str = ""
    backup: Path | None = None
    authorize: bool = False


def _correction_request(options: SignatureRepairOptions) -> tuple[dict[str, object] | None, str]:
    """Bind explicit request bytes before dispatching the single repair owner."""
    if options.corrections is None:
        if options.corrections_sha256 or options.backup or options.reason:
            message = "history_repair_corrections_required"
            raise ValueError(message)
        return None, ""
    payload = Path(options.corrections).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if options.apply and options.corrections_sha256 != digest:
        message = "history_repair_request_digest_required_or_changed"
        raise ValueError(message)
    request = parse_semantic_json(payload)
    if not isinstance(request, dict):
        message = "history_repair_correction_invalid"
        raise TypeError(message)
    return request, digest


@lane_app.command(name="repair-signature")
def repair_commit_signature(
    options: Annotated[SignatureRepairOptions, Parameter(name="*")],
) -> None:
    """Repair accepted signatures or selected historical identities with verified originals."""
    digest = ""
    report: dict[str, object]
    try:
        request, digest = _correction_request(options)
        report = repair_signature(
            root=resolve_root(options.root),
            expect_head=options.expect_head,
            replacement=options.replacement,
            apply=options.apply,
            authorized=options.authorize,
            corrections=request,
            reason=options.reason,
            backup=options.backup.absolute() if options.backup else None,
        )
    except (OSError, ValueError, TypeError) as error:
        report = {
            "verdict": "block",
            "state": "blocked",
            "required_gaps": [str(error)],
            "next_action": "",
            "boundary": "historical-repair-request",
        }
    if digest:
        report["corrections_sha256"] = digest
        if report.get("state") == "ready_to_repair" and options.corrections and options.backup:
            report["next_action"] = (
                str(report["next_action"])
                + " "
                + shlex.join(
                    (
                        "--corrections",
                        str(options.corrections.resolve()),
                        "--corrections-sha256",
                        digest,
                        "--reason",
                        options.reason,
                        "--backup",
                        str(options.backup.absolute()),
                    )
                )
            )
    project_lane_result(
        options.command,
        report,
        enforce=options.apply,
        json_output=options.json_output,
    )
