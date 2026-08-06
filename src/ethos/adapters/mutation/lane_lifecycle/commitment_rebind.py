"""Exact one-shot Commitment replacement for one owned Work Lane."""

from __future__ import annotations

import os
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

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
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.store.state.lease.lifecycle.transitions import rebind_lease_commitment
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import CommitmentRebindRequest
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def execute_commitment_rebind(*, root: Path, request: CommitmentRebindRequest) -> dict[str, object]:
    """Apply, recover, or recognize one exact Commitment/Lease transition."""
    repo = repository_root(root)
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
        _admit_request(repo, request)
        if _is_head_only_partial_target(repo, request, lease):
            return _recover_head_only_partial_target(repo, request, effect, lease)
        if integer_value(lease.get("epoch")) == request.expected_epoch:
            _admit_old_generation(request, lease)
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
        lease = _admit(repo, request, lease)
        return _apply(repo, request, effect, lease)
    except (OSError, TypeError, ValueError) as error:
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
            "required_gaps": [str(error)],
        }


def _apply(
    repo: Path,
    request: CommitmentRebindRequest,
    effect: GitEffect,
    lease: dict[str, object],
) -> dict[str, object]:
    old_commitment = load_lease_bound_commitment(repo, lease=lease)
    target = _target_binding(repo, request, old_commitment.id, old_commitment.digest())
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
        raise ValueError("commitment_rebind_overlay_changed")
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
    target = _target_binding(repo, request, old_commitment.id, old_commitment.digest())
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


def _admit(
    repo: Path,
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> dict[str, object]:
    checks = (
        (lease.get("lease_state") == "valid", f"work_lane_lease_invalid:{request.branch}"),
        (str(lease.get("lease_id") or "") == request.lease_id, "lease_id_stale"),
        (
            str(lease.get("lane_incarnation_id") or "") == request.expected_lane_incarnation_id,
            "lease_lane_incarnation_id_stale",
        ),
        (integer_value(lease.get("epoch")) == request.expected_epoch, "lease_epoch_stale"),
        (str(lease.get("holder_ref") or "") == request.holder_ref, "lease_holder_mismatch"),
        (
            str(lease.get("expires_at") or "") == request.expected_expires_at,
            "lease_expires_at_stale",
        ),
        (str(lease.get("expected_head") or "") == request.expect_head, "lease_head_stale"),
        (
            str(lease.get("expected_tree") or "") == request.expected_tree,
            "lease_expected_tree_stale",
        ),
        (
            str(lease.get("base_commitment_path") or "") == request.expected_commitment_path,
            "lease_commitment_path_stale",
        ),
        (
            str(lease.get("base_commitment_bytes_sha256") or "")
            == request.expected_commitment_bytes_sha256,
            "lease_commitment_bytes_stale",
        ),
        (
            str(lease.get("base_commitment_digest") or "") == request.expected_commitment_digest,
            "lease_commitment_digest_stale",
        ),
        (lease.get("commitment_binding") == "bound", "lease_commitment_binding_mismatch"),
        (
            str(lease.get("payload_sha256") or "") == request.expected_payload_sha256,
            "lease_payload_sha256_stale",
        ),
        (not lease.get("handoff"), "lease_handoff_pending"),
        (
            ref_head(repo, request.branch) in {request.expect_head, request.target_commit},
            "commitment_rebind_ref_state_invalid",
        ),
        (
            current_tracked_head(repo) in {request.expect_head, request.target_commit},
            "commitment_rebind_head_state_invalid",
        ),
        (
            not run_git(repo, "ls-files", "-u", "-z", check=False, text=False).stdout,
            "commitment_rebind_index_conflict",
        ),
        (
            run_git(repo, "write-tree").stdout.strip() == request.expect_index_tree,
            "commitment_rebind_index_tree_mismatch",
        ),
    )
    if gap := next((gap for valid, gap in checks if not valid), ""):
        raise ValueError(gap)
    return lease


def _admit_old_generation(
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> None:
    raw_scope = lease.get("path_scope")
    path_scope = (
        tuple(str(item) for item in raw_scope) if isinstance(raw_scope, list | tuple) else ()
    )
    checks = (
        (str(lease.get("issued_at") or "") == request.expected_issued_at, "lease_issued_at_stale"),
        (
            str(lease.get("renewed_at") or "") == request.expected_renewed_at,
            "lease_renewed_at_stale",
        ),
        (
            path_scope == request.expected_path_scope,
            "lease_path_scope_stale",
        ),
    )
    if gap := next((gap for valid, gap in checks if not valid), ""):
        raise ValueError(gap)


def _admit_request(repo: Path, request: CommitmentRebindRequest) -> None:
    checks = (
        (request.apply, "commitment_rebind_apply_required"),
        (
            load_branch_role_policy(repo).role_for_branch(request.branch) == ROLE_WORK_LANE,
            "work_lane_required",
        ),
        (
            run_git(repo, "branch", "--show-current").stdout.strip() == request.branch,
            "lane_branch_mismatch",
        ),
        (
            os.environ.get("ETHOS_ACTOR", "").strip() == request.holder_ref,
            "lease_actor_mismatch",
        ),
        (
            working_overlay_sha256(repo) == request.expected_working_overlay_sha256,
            "commitment_rebind_overlay_changed",
        ),
    )
    if gap := next((gap for valid, gap in checks if not valid), ""):
        raise ValueError(gap)


def _target_binding(
    repo: Path,
    request: CommitmentRebindRequest,
    old_commitment_id: str,
    old_commitment_digest: str,
) -> dict[str, str]:
    target_type = run_git(repo, "cat-file", "-t", request.target_commit, check=False).stdout.strip()
    parents = run_git(
        repo, "rev-list", "--parents", "-n", "1", request.target_commit
    ).stdout.split()
    target = exact_commitment_fields(
        repo,
        head=request.target_commit,
        carrier=request.new_commitment_path,
    )
    declared = {
        "base_commitment_path": request.new_commitment_path,
        "base_commitment_bytes_sha256": request.new_commitment_bytes_sha256,
        "base_commitment_digest": request.new_commitment_digest,
    }
    new_commitment = load_commitment(
        repo,
        carrier=request.new_commitment_path,
        tree_ref=request.target_commit,
        expected_digest=request.new_commitment_digest,
    )
    checks = (
        (target_type == "commit", "commitment_rebind_target_not_commit"),
        (
            parents == [request.target_commit, request.expect_head],
            "commitment_rebind_target_parent_mismatch",
        ),
        (
            current_tree(repo, request.target_commit) == request.expect_index_tree,
            "commitment_rebind_target_tree_mismatch",
        ),
        (
            all(target[name] == value for name, value in declared.items()),
            "commitment_rebind_target_binding_mismatch",
        ),
        (new_commitment.id == old_commitment_id, "commitment_rebind_identity_mismatch"),
        (new_commitment.digest() != old_commitment_digest, "commitment_rebind_semantics_unchanged"),
        (
            load_repository_commitment(repo, tree_ref=request.expect_head).id
            == load_repository_commitment(repo, tree_ref=request.target_commit).id,
            "commitment_rebind_repository_identity_mismatch",
        ),
    )
    if gap := next((gap for valid, gap in checks if not valid), ""):
        raise ValueError(gap)
    return target


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
            "operation": "commitment.rebind",
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
