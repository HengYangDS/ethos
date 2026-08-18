"""Read-only admission for one exact Commitment rebind request."""

from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING

from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.repo.commit_identity import verify_commit_trust
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.commitment import terminal_v1_binding
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.git import committed_file_bytes
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.openspec.identifiers import malformed_change_identity_repair_valid

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.coordination import CommitmentRebindRequest
    from ethos.contracts.plan import GitEffect
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Commitment


def admit_rebind_state(
    repo: Path,
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> dict[str, object]:
    """Admit the exact current Lease, ref, HEAD, index, and overlay state."""
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
        (
            request.operation == "v1-to-v2-bootstrap" or lease.get("commitment_binding") == "bound",
            "lease_commitment_binding_mismatch",
        ),
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
    _require(checks)
    return lease


def admit_old_generation(request: CommitmentRebindRequest, lease: dict[str, object]) -> None:
    """Admit immutable fields omitted from the common live Lease projection."""
    raw_scope = lease.get("path_scope")
    path_scope = (
        tuple(str(item) for item in raw_scope) if isinstance(raw_scope, list | tuple) else ()
    )
    _require(
        (
            (
                str(lease.get("issued_at") or "") == request.expected_issued_at,
                "lease_issued_at_stale",
            ),
            (
                str(lease.get("renewed_at") or "") == request.expected_renewed_at,
                "lease_renewed_at_stale",
            ),
            (path_scope == request.expected_path_scope, "lease_path_scope_stale"),
        )
    )


def admit_rebind_request(
    repo: Path,
    request: CommitmentRebindRequest,
    *,
    require_apply: bool,
) -> None:
    """Admit command, role, actor, branch, trust, and overlay bindings."""
    if request.repair_change_identity:
        gaps = verify_commit_trust(repo, request.target_commit).get("required_gaps")
        if isinstance(gaps, list) and gaps:
            raise ValueError(str(gaps[0]))
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    _require(
        (
            (request.apply or not require_apply, "commitment_rebind_apply_required"),
            (
                load_branch_role_policy(repo).role_for_branch(request.branch) == ROLE_WORK_LANE,
                "work_lane_required",
            ),
            (
                run_git(repo, "branch", "--show-current").stdout.strip() == request.branch,
                "lane_branch_mismatch",
            ),
            (bool(actor), "invocation_actor_missing"),
            (actor == request.holder_ref, "lease_actor_mismatch"),
            (
                working_overlay_sha256(repo) == request.expected_working_overlay_sha256,
                "commitment_rebind_overlay_changed",
            ),
        )
    )


def rebind_target_binding(
    repo: Path,
    request: CommitmentRebindRequest,
    old_commitment: Commitment,
) -> dict[str, str]:
    """Admit the exact target commit, tree, carrier, identity, and repository."""
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
    _require(
        (
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
            (
                _identity_transition_valid(request, old_commitment, new_commitment),
                (
                    "change_identity_repair_invalid"
                    if request.repair_change_identity
                    else "commitment_rebind_identity_mismatch"
                ),
            ),
            (
                request.repair_change_identity
                or new_commitment.digest() != old_commitment.digest(),
                "commitment_rebind_semantics_unchanged",
            ),
            (
                load_repository_commitment(repo, tree_ref=request.expect_head).id
                == load_repository_commitment(repo, tree_ref=request.target_commit).id,
                "commitment_rebind_repository_identity_mismatch",
            ),
        )
    )
    return target


def bootstrap_v1_binding(
    repo: Path,
    *,
    tree_ref: str,
    carrier: str,
    repository: bool,
) -> dict[str, object]:
    """Read only the identity and exact bytes of one terminal v1 carrier."""
    return terminal_v1_binding(
        repo,
        tree_ref=tree_ref,
        carrier=carrier,
        repository=repository,
    )


def bootstrap_v2_binding(
    repo: Path,
    *,
    tree_ref: str,
    carrier: str,
    repository: bool,
) -> dict[str, str]:
    """Read one exact target v2 carrier through the terminal reader."""
    raw = committed_file_bytes(repo, tree_ref, carrier)
    commitment = (
        load_repository_commitment(repo, tree_ref=tree_ref)
        if repository
        else load_commitment(repo, carrier=carrier, tree_ref=tree_ref)
    )
    return {
        "id": commitment.id,
        "bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "digest": commitment.digest(),
    }


def bootstrap_target_binding(
    repo: Path,
    request: CommitmentRebindRequest,
) -> dict[str, str]:
    """Admit one exact opaque-v1 to strict-v2 target without a compatibility read."""
    old_repository = bootstrap_v1_binding(
        repo,
        tree_ref=request.expect_head,
        carrier=request.old_repository_commitment_path,
        repository=True,
    )
    old_lane = bootstrap_v1_binding(
        repo,
        tree_ref=request.expect_head,
        carrier=request.expected_commitment_path,
        repository=False,
    )
    new_repository = bootstrap_v2_binding(
        repo,
        tree_ref=request.target_commit,
        carrier=request.new_repository_commitment_path,
        repository=True,
    )
    target = exact_commitment_fields(
        repo,
        head=request.target_commit,
        carrier=request.new_commitment_path,
    )
    new_lane = load_commitment(
        repo,
        carrier=request.new_commitment_path,
        tree_ref=request.target_commit,
        expected_digest=request.new_commitment_digest,
    )
    parents = run_git(
        repo, "rev-list", "--parents", "-n", "1", request.target_commit
    ).stdout.split()
    declared_target = {
        "base_commitment_path": request.new_commitment_path,
        "base_commitment_bytes_sha256": request.new_commitment_bytes_sha256,
        "base_commitment_digest": request.new_commitment_digest,
    }
    _require(
        (
            (
                old_repository["id"] == request.old_repository_id,
                "commitment_rebind_repository_identity_mismatch",
            ),
            (
                old_repository["bytes_sha256"] == request.old_repository_commitment_bytes_sha256,
                "commitment_rebind_repository_bytes_stale",
            ),
            (
                old_lane["bytes_sha256"] == request.expected_commitment_bytes_sha256,
                "lease_commitment_bytes_stale",
            ),
            (
                old_lane["subjects"] == (request.old_repository_id,),
                "commitment_rebind_repository_identity_mismatch",
            ),
            (
                new_repository
                == {
                    "id": request.old_repository_id,
                    "bytes_sha256": request.new_repository_commitment_bytes_sha256,
                    "digest": request.new_repository_commitment_digest,
                },
                "commitment_rebind_repository_binding_mismatch",
            ),
            (new_lane.id == old_lane["id"], "commitment_rebind_identity_mismatch"),
            (
                new_lane.subjects == (request.old_repository_id,),
                "commitment_rebind_repository_identity_mismatch",
            ),
            (
                parents == [request.target_commit, request.expect_head],
                "commitment_rebind_target_parent_mismatch",
            ),
            (
                current_tree(repo, request.target_commit) == request.expect_index_tree,
                "commitment_rebind_target_tree_mismatch",
            ),
            (
                all(target[name] == value for name, value in declared_target.items()),
                "commitment_rebind_target_binding_mismatch",
            ),
        )
    )
    return target


def is_old_generation_lease(
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> bool:
    """Return whether every live Lease coordinate matches the receipt prestate."""
    fields = {
        "lease_state": "valid",
        "lease_id": request.lease_id,
        "lane_incarnation_id": request.expected_lane_incarnation_id,
        "holder_ref": request.holder_ref,
        "expected_head": request.expect_head,
        "expected_tree": request.expected_tree,
        "base_commitment_path": request.expected_commitment_path,
        "base_commitment_bytes_sha256": request.expected_commitment_bytes_sha256,
        "base_commitment_digest": request.expected_commitment_digest,
        "payload_sha256": request.expected_payload_sha256,
    }
    return integer_value(lease.get("epoch")) == request.expected_epoch and all(
        str(lease.get(name) or "") == value for name, value in fields.items()
    )


def is_partial_target(
    repo: Path,
    request: CommitmentRebindRequest,
    lease: dict[str, object],
) -> bool:
    """Detect exact Git success before the Commitment Lease CAS completed."""
    hook_projected = (
        str(lease.get("expected_head") or "") == request.target_commit
        and str(lease.get("expected_tree") or "") == request.expect_index_tree
    )
    stable = {
        "lease_id": request.lease_id,
        "lane_incarnation_id": request.expected_lane_incarnation_id,
        "holder_ref": request.holder_ref,
        "base_commitment_path": request.expected_commitment_path,
        "base_commitment_bytes_sha256": request.expected_commitment_bytes_sha256,
        "base_commitment_digest": request.expected_commitment_digest,
    }
    return bool(
        ref_head(repo, request.branch) == request.target_commit
        and integer_value(lease.get("epoch")) == request.expected_epoch
        and all(str(lease.get(name) or "") == value for name, value in stable.items())
        and (is_old_generation_lease(request, lease) or hook_projected)
    )


def prepare_partial_recovery_intent(
    repo: Path,
    plan: TransitionPlan,
    effect: GitEffect,
) -> None:
    """Reconstruct the sole exact plan-bound intent for a proven partial target."""
    if len(effect.updates) != 1:
        message = "commitment_rebind_effect_invalid"
        raise ValueError(message)
    ref_name, update = next(iter(effect.updates.items()))
    operation = str(plan.policy.get("transition") or plan.policy.get("operation") or "")
    intent = write_ref_intent(
        root=repo,
        ref_name=ref_name,
        update=update,
        operation=operation,
        plan_digest=plan.digest,
    )
    if intent["phase"] in {"prepared", "committed"}:
        return
    claimed = claim_ref_intent(
        root=repo,
        ref_name=ref_name,
        update=update,
        operation=operation,
        phase="prepared",
        plan_digest=plan.digest,
    )
    if gap := str(claimed["gap"] or ""):
        message = f"git_effect_ref_intent_prepared_{gap}"
        raise ValueError(message)


def _identity_transition_valid(
    request: CommitmentRebindRequest,
    old: Commitment,
    new: Commitment,
) -> bool:
    return (
        malformed_change_identity_repair_valid(
            carrier=request.new_commitment_path,
            old_id=old.id,
            old_digest=old.digest(),
            new=new,
        )
        if request.repair_change_identity
        else new.id == old.id
    )


def _require(checks: tuple[tuple[bool, str], ...]) -> None:
    if gap := next((gap for valid, gap in checks if not valid), ""):
        raise ValueError(gap)
