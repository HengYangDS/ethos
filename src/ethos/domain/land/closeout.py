"""Land and accepted-root closeout reducers.

This module owns land-stage lifecycle decisions, runner binding, and repository
audit handoff. Publication, evidence freshness, intake projection, and trust
closeout live in sibling semantic modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict

import ethos
import ethos.adapters.repo.git as git_adapter
import ethos.domain.status
from ethos.adapters.mutation.proof import proof_admission_report
from ethos.adapters.repo.runtime.binding import runner_source_root
from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import JsonObject
from ethos.contracts.verdict import Verdict
from ethos.normalization.coercion import string_mapping
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.contracts.admission import AdmissionDecision


class CloseoutCoordinates(BaseModel):
    """Exact repository coordinates for one transient accepted closeout."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    root: str
    accepted_ref: str
    accepted_head: str
    candidate_ref: str
    candidate_head: str
    candidate_tree: str


class CloseoutProof(BaseModel):
    """The exact proof plane selected for one closeout subject."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    plane: str
    attestation_id: str
    repository_attestation_id: str
    external_receipt: JsonObject


class CloseoutEffect(BaseModel):
    """The applied exact-effect identity, absent before mutation."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    attestation_id: str


class CloseoutResolution(BaseModel):
    """One immutable read model shared by closeout and its projections."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    coordinates: CloseoutCoordinates
    proof: CloseoutProof
    effect: CloseoutEffect
    repository_audit: JsonObject
    openspec_lifecycle: JsonObject
    control_replacement: JsonObject
    accepted_update: JsonObject
    verdict: Verdict
    required_gaps: tuple[str, ...]
    next_action: str
    user_decision_required: bool


def closeout_apply_command(
    root: Path,
    *,
    accepted_head: str,
    candidate_head: str,
    receipt_path: Path | None = None,
    status: dict[str, object] | None = None,
) -> str:
    """Render the sole exact public accepted-closeout command."""
    observed = status or workspace_status(root, include_foreign_path_scope=False)
    accepted_root = accepted_worktree_root(observed.get("worktrees"), root).resolve()
    receipt = (
        f" --independent-verification-receipt {receipt_path.resolve().as_posix()}"
        if receipt_path is not None
        else ""
    )
    return (
        "ethos land --closeout --apply --authorize "
        f"--expect-head {accepted_head} --candidate-head {candidate_head}{receipt} "
        f"--root {accepted_root.as_posix()} --json"
    )


def closeout_command_from_status(root: Path, status: dict[str, object]) -> str:
    """Return the exact closeout command when an accepted candidate is pending."""
    policy = load_branch_role_policy(root)
    if status.get("role") != policy.role_for_branch(policy.accepted_branch):
        return ""
    accepted_head = str(status.get("head") or "")
    candidate_head = str(string_mapping(status.get("candidate")).get("head") or "")
    if (
        not accepted_head
        or not candidate_head
        or accepted_head == candidate_head
        or not git_adapter.is_ancestor(root, accepted_head, candidate_head)
    ):
        return ""
    return closeout_apply_command(
        root,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        status=status,
    )


def closeout_receipt_path(repo: Path, control_replacement: dict[str, object]) -> Path | None:
    """Derive the content-addressed external receipt location for one request."""
    verification = string_mapping(control_replacement.get("independent_verification"))
    if verification.get("receipt"):
        return None
    request = string_mapping(control_replacement.get("verification_request"))
    if not request or "independent_verification_receipt_required" not in string_sequence(
        control_replacement.get("required_gaps")
    ):
        return None
    common_dir = git_adapter.git_common_dir(repo)
    if not common_dir:
        return None
    return (
        Path(common_dir)
        / "ethos"
        / "receipts"
        / "independent-verification"
        / f"{canonical_json_digest(request)}.json"
    )


def closeout_resolution(
    *,
    repo: Path,
    accepted_head: str,
    candidate_head: str,
    audit_root: Path,
    audit: dict[str, object],
    lifecycle: dict[str, object],
    control_replacement: dict[str, object],
    update: dict[str, object],
    verdict: Verdict,
    gaps: tuple[str, ...],
    apply: bool,
    receipt_path: Path | None = None,
) -> CloseoutResolution:
    """Resolve one exact closeout subject, proof, effect, and continuation."""
    policy = load_branch_role_policy(repo)
    proof_report = proof_admission_report(
        audit_root,
        candidate_head,
        repository_transition=True,
    )
    proof = string_mapping(proof_report.get("attestation"))
    verification = string_mapping(control_replacement.get("independent_verification"))
    receipt = string_mapping(verification.get("receipt"))
    external_plane = bool(receipt)
    attestation = string_mapping(update.get("attestation"))
    coordinates = CloseoutCoordinates(
        root=repo.resolve().as_posix(),
        accepted_ref=f"refs/heads/{policy.accepted_branch}",
        accepted_head=accepted_head,
        candidate_ref=f"refs/heads/{policy.candidate_branch}",
        candidate_head=candidate_head,
        candidate_tree=git_adapter.current_tree(audit_root, candidate_head),
    )
    expected_receipt = receipt_path or closeout_receipt_path(repo, control_replacement)
    if verdict == "pass" and apply and candidate_head == accepted_head:
        next_action = "ethos publish"
    elif verdict == "pass" and apply:
        next_action = (
            f"ethos publish --expect-head {candidate_head} "
            f"--root {repo.resolve().as_posix()} --json"
        )
    elif "candidate_diverged_from_accepted" in gaps:
        next_action = (
            "ethos lane candidate --refresh-from-accepted --apply --authorize "
            f"--expect-head {accepted_head} --root {repo.resolve().as_posix()} --json"
        )
    else:
        next_action = closeout_apply_command(
            repo,
            accepted_head=accepted_head,
            candidate_head=candidate_head,
            receipt_path=expected_receipt,
        )
    return CloseoutResolution(
        coordinates=coordinates,
        proof=CloseoutProof(
            plane="external" if external_plane else "local",
            attestation_id=(
                str(receipt.get("payload_digest") or "")
                if external_plane
                else str(proof.get("id") or "")
            ),
            repository_attestation_id=str(proof.get("id") or ""),
            external_receipt=receipt,
        ),
        effect=CloseoutEffect(attestation_id=str(attestation.get("id") or "")),
        repository_audit=audit,
        openspec_lifecycle=lifecycle,
        control_replacement=control_replacement,
        accepted_update=update,
        verdict=verdict,
        required_gaps=gaps,
        next_action=next_action,
        user_decision_required=(
            "candidate_diverged_from_accepted" in gaps
            or "authorization_required" in gaps
            or "independent_verification_receipt_required" in gaps
        ),
    )


def closeout_audit_root(repo: Path, decision: AdmissionDecision) -> Path:
    """Resolve closeout audit root, preserving land.workspace_status patchability."""
    if decision.verdict != "pass":
        return repo
    candidate = workspace_status(repo, include_foreign_path_scope=False).get("candidate", {})
    if not isinstance(candidate, dict):
        return repo
    candidate_path = str(candidate.get("worktree_path") or "")
    return Path(candidate_path) if candidate_path else repo


def runner_binding_report(*, accepted_root: Path, audit_root: Path) -> dict[str, object]:
    """Expose which ETHOS source tree provides the current closeout runner."""
    runner_module_path = Path(ethos.__file__).resolve()
    runner_package_root = runner_module_path.parent
    source_root = runner_source_root(runner_module_path)
    accepted_root_resolved = accepted_root.resolve()
    audit_root_resolved = audit_root.resolve()
    runner_matches_accepted_root = source_root == accepted_root_resolved
    runner_matches_audit_root = source_root == audit_root_resolved
    state = "bound_to_accepted_root" if runner_matches_accepted_root else "external_current_runner"
    return {
        "kind": "closeout_runner_binding",
        "state": state,
        "runner_module_path": runner_module_path.as_posix(),
        "runner_package_root": runner_package_root.as_posix(),
        "runner_source_root": source_root.as_posix(),
        "accepted_root": accepted_root_resolved.as_posix(),
        "audit_root": audit_root_resolved.as_posix(),
        "runner_matches_accepted_root": runner_matches_accepted_root,
        "runner_matches_audit_root": runner_matches_audit_root,
        "advisory_gaps": []
        if runner_matches_accepted_root
        else ["closeout_runner_source_differs_from_accepted_root"],
    }


def closeout_bootstrap_package(
    *,
    repo: Path,
    audit_root: Path,
    required_gaps: tuple[str, ...],
    accepted_head: str,
    candidate_head: str,
    receipt_path: Path | None = None,
) -> dict[str, object]:
    """Build the closeout bootstrap package (command to run against accepted_root)."""
    status = workspace_status(repo, include_foreign_path_scope=False)
    accepted_root = accepted_worktree_root(status.get("worktrees"), repo).resolve()
    policy = load_branch_role_policy(accepted_root)
    candidate = status.get("candidate") if isinstance(status.get("candidate"), dict) else {}
    command = closeout_apply_command(
        accepted_root,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        receipt_path=receipt_path,
    )
    runner_binding = runner_binding_report(accepted_root=accepted_root, audit_root=audit_root)
    candidate_data = cast("dict[str, object]", candidate)
    candidate_path = str(candidate_data.get("worktree_path") or "")
    already_current = bool(accepted_head and candidate_head == accepted_head)
    proof_target_root = Path(candidate_path).resolve() if candidate_path else audit_root.resolve()
    proof_target = {
        "kind": "closeout_proof_target",
        "role": "candidate",
        "root": proof_target_root.as_posix(),
        "head": candidate_head,
        "reason": "accepted-root closeout promotes the candidate head",
    }
    return {
        "kind": "closeout_bootstrap",
        "mode": "maintainer_break_glass_local",
        "runner_mode": "current_runner_with_explicit_accepted_root",
        "remote_state": "deferred",
        "remote_push": "not_performed",
        "uses_current_runner": True,
        "runner_binding": runner_binding,
        "runner_module_path": runner_binding["runner_module_path"],
        "runner_package_root": runner_binding["runner_package_root"],
        "runner_source_root": runner_binding["runner_source_root"],
        "runner_matches_accepted_root": runner_binding["runner_matches_accepted_root"],
        "runner_matches_audit_root": runner_binding["runner_matches_audit_root"],
        "runner_advisories": runner_binding["advisory_gaps"],
        "state": "blocked" if required_gaps else "current" if already_current else "ready",
        "accepted_root": accepted_root.as_posix(),
        "audit_root": audit_root.resolve().as_posix(),
        "accepted_branch": policy.accepted_branch,
        "candidate_branch": policy.candidate_branch,
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "proof_target": proof_target,
        "independent_verification": {
            "required": "independent_verification_receipt_required" in required_gaps,
            "proof_floor_id": "ethos:control-replacement:v1",
            "receipt_option": (
                f"--independent-verification-receipt {receipt_path.resolve().as_posix()}"
                if receipt_path is not None
                else ""
            ),
            "trust_boundary": "protected-provider",
            "mints_authority": False,
        },
        "blocking": bool(required_gaps),
        "required_gaps": list(required_gaps),
        "command": command,
        "required_order": [
            "run closeout command with a current ETHOS runner",
            "bind --root to the clean accepted_root checkout",
            "audit the configured candidate worktree before accepted-root movement",
            "prove the configured candidate head before accepted-root movement",
            "for a control replacement, obtain the exact protected-provider signed receipt",
            "fast-forward accepted_root from candidate only after proof and lifecycle gates pass",
            "defer remote push until remote publication is available",
        ],
        "next_action": "ethos publish"
        if already_current and not required_gaps
        else "run closeout with a current ETHOS runner against accepted_root",
    }


def land_next_action(
    *,
    verdict: Verdict,
    gaps: tuple[str, ...],
    current_head: str,
) -> str:
    """Derive the recommended next command after a land attempt."""
    if verdict == "pass":
        return "ethos publish"
    if "protected_root_mutation" in gaps:
        return "ethos land --closeout --json"
    if "candidate_base_stale" in gaps:
        return f"ethos lane refresh-base --apply --authorize --expect-head {current_head} --json"
    active_carriers = tuple(
        gap
        for gap in gaps
        if gap.startswith("openspec_active_change_unarchived:") and gap.endswith(":work_lane")
    )
    if active_carriers:
        change = active_carriers[0].split(":", 2)[1]
        return (
            f"ethos lane archive-change --change {change} "
            f"--expect-head {current_head} --apply --json"
        )
    if "proof_not_proven" in gaps:
        return f"ethos prove --execute --expect-head {current_head} --json"
    return "ethos prove --json"


def repository_audit_after_admission(repo: Path, decision: AdmissionDecision) -> dict[str, object]:
    """Run the shape audit after admission, or skip when mutation was blocked."""
    if decision.verdict != "pass":
        return {
            "verdict": "block",
            "state": "skipped",
            "reason": "mutation_admission_blocked",
            "required_gaps": [],
            "root": repo.as_posix(),
        }
    return ethos.domain.status.audit_for_root(repo, openspec_mode="shape")
