"""Exact one-shot Commitment replacement for one owned Work Lane."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_admission import admit_old_generation
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_admission import admit_rebind_request
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_admission import admit_rebind_state
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_admission import rebind_target_binding
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_derivation import (
    load_commitment_rebind_receipt,
)
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_evidence import (
    issue_rebind_attestation,
)
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_evidence import old_generation
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_evidence import (
    persist_rebind_attestation,
)
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind_evidence import (
    recognized_rebind_attestation,
)
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.repo.commit_identity import commit_trust_setup_action
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import rebind_lease_commitment
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import CommitmentRebindRequest
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation


def execute_commitment_rebind(*, root: Path, request: CommitmentRebindRequest) -> dict[str, object]:
    """Apply, recover, or recognize one exact Commitment/Lease transition."""
    repo = repository_root(root)
    guard = local_state_mutation_guard(repo) if request.apply else {"required_gaps": []}
    if guard["required_gaps"]:
        return {
            "verdict": "block",
            "state": "blocked",
            "branch": request.branch,
            "lease": {},
            "attestation": {},
            "required_gaps": guard["required_gaps"],
            "next_action": guard["next_action"],
        }
    return _execute_commitment_rebind(repo, request)


def execute_commitment_rebind_receipt(
    *,
    root: Path,
    receipt_path: str,
    receipt_sha256: str = "",
    apply: bool,
) -> dict[str, object]:
    """Revalidate and execute the existing request carried by one receipt."""
    repo = repository_root(root)
    try:
        receipt = load_commitment_rebind_receipt(repo, receipt_path, receipt_sha256)
    except (OSError, TypeError, ValueError) as error:
        return {
            "verdict": "block",
            "state": "blocked",
            "branch": "",
            "lease": {},
            "attestation": {},
            "required_gaps": [str(error)],
            "next_action": "",
        }
    request = receipt.request.model_copy(update={"apply": apply})
    report = (
        execute_commitment_rebind(root=repo, request=request)
        if apply
        else _preview_commitment_rebind(repo, request)
    )
    report["request_receipt"] = {
        "path": Path(receipt_path).resolve().as_posix(),
        "sha256": receipt_sha256 or f"sha256:{Path(receipt_path).stem}",
    }
    return report


def _preview_commitment_rebind(
    repo: Path,
    request: CommitmentRebindRequest,
) -> dict[str, object]:
    """Validate the exact receipt without applying its Git or Lease effects."""
    try:
        lease = leases_by_branch(repo).get(request.branch, {})
        admit_rebind_request(repo, request, require_apply=False)
        admit_old_generation(request, lease)
        admit_rebind_state(repo, request, lease)
        old_commitment = load_lease_bound_commitment(repo, lease=lease)
        target = rebind_target_binding(repo, request, old_commitment)
        effect = GitEffect(
            updates={
                f"refs/heads/{request.branch}": GitRefUpdate(
                    expected=request.expect_head,
                    desired=request.target_commit,
                )
            }
        )
        plan = _plan(
            repo,
            request,
            lease,
            effect,
            old_commitment.digest(),
            request.expected_working_overlay_sha256,
        )
    except (OSError, TypeError, ValueError) as error:
        return {
            "verdict": "block",
            "state": "blocked",
            "branch": request.branch,
            "lease": {},
            "attestation": {},
            "required_gaps": [str(error)],
            "next_action": "",
        }
    return {
        "verdict": "pass",
        "state": "ready_to_apply",
        "branch": request.branch,
        "lease": lease,
        "target": target,
        "transition_plan": plan.model_dump(mode="json"),
        "attestation": {},
        "required_gaps": [],
        "next_action": "",
    }


def _execute_commitment_rebind(
    repo: Path,
    request: CommitmentRebindRequest,
) -> dict[str, object]:
    effect = GitEffect(
        updates={
            f"refs/heads/{request.branch}": GitRefUpdate(
                expected=request.expect_head,
                desired=request.target_commit,
            )
        }
    )
    try:
        lease = leases_by_branch(repo).get(request.branch, {})
        admit_rebind_request(repo, request, require_apply=False)
        if _is_head_only_partial_target(repo, request, lease):
            if not request.apply:
                return _project_partial_target_recovery(repo, request, lease)
            return _recover_head_only_partial_target(repo, request, effect, lease)
        admit_rebind_request(repo, request, require_apply=True)
        if integer_value(lease.get("epoch")) == request.expected_epoch:
            admit_old_generation(request, lease)
        terminal_plan = _plan(
            repo,
            request,
            old_generation(request),
            effect,
            request.expected_commitment_digest,
            request.expected_working_overlay_sha256,
        )
        recognized = recognized_rebind_attestation(repo, request, effect, lease, terminal_plan)
        if recognized is not None:
            execute_git_effect(repo, terminal_plan, issuer=request.holder_ref)
            return _report(request, lease, recognized, "recognized")
        if _is_target_generation(request, lease):
            return _attest_recovered(repo, request, effect, lease)
        _require_not_partial_target(request, lease)
        lease = admit_rebind_state(repo, request, lease)
        return _apply(repo, request, effect, lease)
    except (OSError, TypeError, ValueError) as error:
        gap = str(error)
        return {
            "verdict": "block",
            "state": (
                "repair_required"
                if ref_head(repo, request.branch) != request.expect_head
                else "blocked"
            ),
            "branch": request.branch,
            "lease": {},
            "attestation": {},
            "required_gaps": [gap],
            "next_action": (
                commit_trust_setup_action(repo, request.target_commit)
                if gap.startswith("commit_trust_anchor_") or gap == "commit_signature_untrusted"
                else ""
            ),
        }


def _apply(
    repo: Path,
    request: CommitmentRebindRequest,
    effect: GitEffect,
    lease: dict[str, object],
) -> dict[str, object]:
    old_commitment = load_lease_bound_commitment(repo, lease=lease)
    target = rebind_target_binding(repo, request, old_commitment)
    old_overlay = working_overlay_sha256(repo)
    plan = _plan(repo, request, lease, effect, old_commitment.digest(), old_overlay)
    recovering = ref_head(repo, request.branch) == request.target_commit
    git_attestation = execute_git_effect(repo, plan, issuer=request.holder_ref)
    updated = rebind_lease_commitment(
        state_database(repo),
        request=_lease_request(request),
        binding=target,
    )
    new_overlay = working_overlay_sha256(repo)
    if old_overlay != new_overlay:
        msg = "commitment_rebind_overlay_changed"
        raise ValueError(msg)
    attestation = issue_rebind_attestation(
        repo=repo,
        request=request,
        new_lease=updated,
        plan=plan,
        effect=effect,
        git_state=str(git_attestation.statement["result"]["state"]),
        issued_at=datetime.now(UTC),
    )
    persist_rebind_attestation(repo, effect, attestation)
    return _report(
        request,
        updated,
        attestation,
        "recovered" if recovering else "applied",
    )


def _is_head_only_partial_target(
    repo: Path,
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> bool:
    """Detect Git+hook success before the Commitment Lease CAS completed."""
    return (
        integer_value(lease.get("epoch")) == request.expected_epoch
        and str(lease.get("lease_id") or "") == request.lease_id
        and str(lease.get("holder_ref") or "") == request.holder_ref
        and str(lease.get("expected_head") or "") == request.target_commit
        and str(lease.get("expected_tree") or "") == request.expect_index_tree
        and str(lease.get("base_commitment_path") or "") == request.expected_commitment_path
        and str(lease.get("base_commitment_digest") or "") == request.expected_commitment_digest
        and ref_head(repo, request.branch) == request.target_commit
    )


def _recover_head_only_partial_target(
    repo: Path,
    request: CommitmentRebindRequest,
    effect: GitEffect,
    lease: dict[str, object],
) -> dict[str, object]:
    """Finish Lease/Attestation after the ref CAS already succeeded."""
    prior_coordinates = {
        **lease,
        "expected_head": request.expect_head,
        "expected_tree": request.expected_tree,
        "payload_sha256": request.expected_payload_sha256,
    }
    old_commitment = load_lease_bound_commitment(repo, lease=prior_coordinates)
    target = rebind_target_binding(repo, request, old_commitment)
    current_request = request.model_copy(
        update={
            "expect_head": str(lease["expected_head"]),
            "expected_tree": str(lease["expected_tree"]),
            "expected_payload_sha256": str(lease["payload_sha256"]),
        }
    )
    updated = rebind_lease_commitment(
        state_database(repo),
        request=_lease_request(current_request),
        binding=target,
    )
    plan = _plan(
        repo,
        request,
        old_generation(request),
        effect,
        old_commitment.digest(),
        working_overlay_sha256(repo),
    )
    attestation = issue_rebind_attestation(
        repo=repo,
        request=request,
        new_lease=updated,
        plan=plan,
        effect=effect,
        git_state="recovered",
        issued_at=datetime.now(UTC),
    )
    persist_rebind_attestation(repo, effect, attestation)
    return _report(request, updated, attestation, "recovered")


def _project_partial_target_recovery(
    repo: Path,
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> dict[str, object]:
    """Validate an exact partial target without mutating its Lease."""
    prior_coordinates = {
        **lease,
        "expected_head": request.expect_head,
        "expected_tree": request.expected_tree,
        "payload_sha256": request.expected_payload_sha256,
    }
    old_commitment = load_lease_bound_commitment(repo, lease=prior_coordinates)
    rebind_target_binding(repo, request, old_commitment)
    return {
        "verdict": "pass",
        "state": "ready_to_recover",
        "branch": request.branch,
        "lease": lease,
        "attestation": {},
        "required_gaps": [],
    }


def _plan(
    repo: Path,
    request: CommitmentRebindRequest,
    lease: dict[str, object],
    effect: GitEffect,
    old_commitment_digest: str,
    overlay_sha256: str,
):
    commitment = load_lease_bound_commitment(repo, lease=lease)
    return compile_observed_git_effect(
        repo,
        commitment,
        effect,
        head=request.expect_head,
        prior_attestations={},
        policy={
            "operation": (
                "change.identity-repair" if request.repair_change_identity else "commitment.rebind"
            ),
            "old_commitment_digest": old_commitment_digest,
            "new_commitment_digest": request.new_commitment_digest,
        },
        values={
            "lease_generation": lease_generation(lease),
            "lease_successor": _target_generation(request),
            "index_tree": request.expect_index_tree,
            "working_overlay_sha256": overlay_sha256,
            "new_commitment_path": request.new_commitment_path,
            "new_commitment_bytes_sha256": request.new_commitment_bytes_sha256,
            "new_commitment_digest": request.new_commitment_digest,
        },
    )


def _target_generation(request: CommitmentRebindRequest) -> dict[str, object]:
    target = old_generation(request) | {
        "epoch": request.expected_epoch + 1,
        "expected_head": request.target_commit,
        "expected_tree": request.expect_index_tree,
        "base_commitment_path": request.new_commitment_path,
        "base_commitment_bytes_sha256": request.new_commitment_bytes_sha256,
        "base_commitment_digest": request.new_commitment_digest,
    }
    generation = lease_generation(target)
    generation.pop("payload_sha256")
    return generation


def _lease_request(request: CommitmentRebindRequest) -> LeaseOperationRequest:
    return LeaseOperationRequest(
        operation="commitment_rebind",
        branch=request.branch,
        holder_ref=request.holder_ref,
        lease_id=request.lease_id,
        expected_epoch=request.expected_epoch,
        expect_head=request.expect_head,
        expected_expires_at=request.expected_expires_at,
        expected_payload_sha256=request.expected_payload_sha256,
        apply=True,
    )


def _is_target_generation(
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> bool:
    payload = lease.get("payload")
    if not isinstance(payload, dict):
        return False
    if any(lease.get(name) != payload.get(name) for name in LaneLease.model_fields):
        return False
    target = _target_generation(request)
    return lease.get("lease_state") == "valid" and all(
        lease_generation(lease).get(name) == value for name, value in target.items()
    )


def _require_not_partial_target(
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> None:
    if integer_value(lease.get("epoch")) == request.expected_epoch + 1:
        message = "commitment_rebind_state_inconsistent"
        raise ValueError(message)


def _attest_recovered(
    repo: Path,
    request: CommitmentRebindRequest,
    effect: GitEffect,
    lease: dict[str, object],
) -> dict[str, object]:
    if ref_head(repo, request.branch) != request.target_commit:
        message = "commitment_rebind_state_inconsistent"
        raise ValueError(message)
    generation = old_generation(request)
    plan = _plan(
        repo,
        request,
        generation,
        effect,
        request.expected_commitment_digest,
        request.expected_working_overlay_sha256,
    )
    git_attestation = execute_git_effect(repo, plan, issuer=request.holder_ref)
    if working_overlay_sha256(repo) != request.expected_working_overlay_sha256:
        message = "commitment_rebind_overlay_changed"
        raise ValueError(message)
    attestation = issue_rebind_attestation(
        repo=repo,
        request=request,
        new_lease=lease,
        plan=plan,
        effect=effect,
        git_state=str(git_attestation.statement["result"]["state"]),
        issued_at=datetime.now(UTC),
    )
    persist_rebind_attestation(repo, effect, attestation)
    return _report(request, lease, attestation, "attested")


def _report(
    request: CommitmentRebindRequest,
    lease: dict[str, object],
    attestation: Attestation,
    state: str,
) -> dict[str, object]:
    return {
        "verdict": "pass",
        "state": state,
        "branch": request.branch,
        "lease": lease,
        "attestation": attestation.model_dump(mode="json"),
        "required_gaps": [],
    }
