"""Work Lane repairs: projections, formatting, paradigm gaps, signing, history and redaction.

Each operation takes the resolved root and its catalog request, runs the one owner of its effect
and projects that owner's report through `lane_result`.
"""

import hashlib
import shlex
from pathlib import Path

from ethos.adapters.mutation.accepted.signature import repair_signature
from ethos.adapters.mutation.paradigm_repair import repair_paradigm
from ethos.adapters.mutation.projection import project_repository
from ethos.adapters.mutation.source_format import format_source
from ethos.adapters.repo.trust_anchor.authorization import authorize_configured_commit_signer
from ethos.application.catalog import standard_input
from ethos.application.lane.result import lane_result
from ethos.application.redaction import redact_private_addresses
from ethos.contracts.operations.lane_repair import FormatRequest
from ethos.contracts.operations.lane_repair import ProjectRequest
from ethos.contracts.operations.lane_repair import RedactRequest
from ethos.contracts.operations.lane_repair import RepairParadigmRequest
from ethos.contracts.operations.lane_repair import RepairSignatureRequest
from ethos.contracts.operations.lane_repair import TrustCommitSignerRequest
from ethos.contracts.semantic import parse_semantic_json
from ethos.result import EthosResult

_REDACTED = ("count", "outside_roots", "changed_paths", "generation")


def project_lane(root: Path, request: ProjectRequest) -> EthosResult:
    """Generate every declared native projection without requiring a product checkout."""
    patch = Path(request.patch).read_text(encoding="utf-8") if request.patch is not None else None
    fields = request.model_dump(include={"check", "apply", "authorize"})
    expect_head = request.expect_head or ""
    report = project_repository(root, expect_head=expect_head, preview_patch=patch, **fields)
    return lane_result("lane project", report)


def format_lane(root: Path, request: FormatRequest) -> EthosResult:
    """Prepare all postimages without writes, or apply them after exact native admission."""
    fields = request.model_dump(exclude={"expect_head"})
    report = format_source(root, expect_head=request.expect_head or "", **fields)
    summary = {
        "file_count": report.get("file_count", 0),
        "changed_count": report.get("changed_count", 0),
        "head": report.get("head", ""),
    }
    return lane_result("lane format", report, summary=summary)


def repair_lane_paradigm(root: Path, request: RepairParadigmRequest) -> EthosResult:
    """Preview or apply the deterministic repairs of repository paradigm gaps."""
    return lane_result("lane repair-paradigm", repair_paradigm(root=root, apply=request.apply))


def trust_lane_signer(root: Path, request: TrustCommitSignerRequest) -> EthosResult:
    """Authorize Git's configured signer for one exact signed commit."""
    report = authorize_configured_commit_signer(
        root,
        request.target_commit,
        expected_anchor_sha256=request.expected_anchor_sha256,
        apply=request.apply,
        authorized=request.authorize,
    )
    return lane_result("lane trust-commit-signer", report)


def _corrections(request: RepairSignatureRequest) -> tuple[dict[str, object] | None, str]:
    """Bind the explicit request bytes, and their digest, before the one repair owner runs."""
    if request.corrections is None:
        if request.corrections_sha256 or request.backup or request.reason:
            message = "history_repair_corrections_required"
            raise ValueError(message)
        return None, ""
    payload = request.corrections.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if request.apply and request.corrections_sha256 != digest:
        message = "history_repair_request_digest_required_or_changed"
        raise ValueError(message)
    corrections = parse_semantic_json(payload)
    if not isinstance(corrections, dict):
        message = "history_repair_correction_invalid"
        raise TypeError(message)
    return corrections, digest


def repair_lane_signature(root: Path, request: RepairSignatureRequest) -> EthosResult:
    """Repair accepted signatures or selected historical identities with verified originals.

    A preview that is ready to repair names the corrections, their digest, the reason and the
    backup in the request that applies it.
    """
    digest = ""
    report: dict[str, object]
    try:
        corrections, digest = _corrections(request)
        report = repair_signature(
            root=root,
            expect_head=request.expect_head or "",
            replacement=request.replacement,
            apply=request.apply,
            authorized=request.authorize,
            corrections=corrections,
            reason=request.reason,
            backup=request.backup.absolute() if request.backup else None,
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
        if report.get("state") == "ready_to_repair" and request.corrections and request.backup:
            bound = ("--corrections", str(request.corrections.resolve()), "--corrections-sha256")
            given = (digest, "--reason", request.reason, "--backup", str(request.backup.absolute()))
            report["next_action"] = f"{report['next_action']} {shlex.join((*bound, *given))}"
    return lane_result("lane repair-signature", report)


def redact_lane_peers(root: Path, request: RedactRequest) -> EthosResult:
    """Preview the occurrences without a key; apply or verify with the key on standard input."""
    key = standard_input() if request.key_stdin else ""
    fields = request.model_dump(exclude={"key_stdin", "expect_head"})
    report = redact_private_addresses(
        root, key=key, expect_head=request.expect_head or "", **fields
    )
    summary = {name: report[name] for name in _REDACTED if name in report}
    return lane_result("lane redact private-addresses", report, summary=summary)
