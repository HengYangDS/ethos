"""Accepted-root promotion effects for a proven candidate revision."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.closeout_intent.marker import execute_closeout_effect
from ethos.adapters.admission.closeout_intent.marker import sweep_stale_closeout_intents
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_evidence_digest
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effects import sync_current_worktree
from ethos.adapters.repo.git_effects import sync_linked_ref_worktree
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.branch.roles import BranchRolePolicy
    from ethos.contracts.semantic import Attestation
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


def promote_candidate(*, root, policy, current_head, candidate_head, status):
    blocker, proof = _promotion_blocker(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
    )
    if blocker:
        return blocker
    return _apply_candidate_promotion(
        root=root,
        policy=policy,
        status=status,
        current_head=current_head,
        candidate_head=candidate_head,
        proof=cast("Attestation", proof),
    )


def _apply_candidate_promotion(
    *,
    root,
    policy,
    status,
    current_head,
    candidate_head,
    proof,
):
    worktrees = cast("list[dict[str, object]]", status.get("worktrees", []))
    sweep_stale_closeout_intents(root)
    evidence_digest = proof_evidence_digest(root, candidate_head)
    if not evidence_digest:
        return _accepted_block(
            policy,
            current_head,
            ["accepted_effect_binding_invalid"],
            candidate_head=candidate_head,
            stderr="accepted_prior_proof_missing",
        )
    try:
        authority = load_repository_commitment(root, tree_ref=current_head)
        prior_attestations = {
            "proof": proof.model_dump(mode="json"),
            "proof_set": evidence_digest,
        }
        effect = GitEffect(
            updates={
                f"refs/heads/{policy.accepted_branch}": GitRefUpdate(
                    expected=current_head,
                    desired=candidate_head,
                )
            },
            assertions={f"refs/heads/{policy.candidate_branch}": candidate_head},
        )
        plan = _accepted_transition_plan(
            root=root,
            role_policy=policy,
            authority=authority,
            effect=effect,
            operation="candidate.accept",
            head=current_head,
            prior_attestations=prior_attestations,
        )
        attestation = _attempt_closeout_effect(root=root, plan=plan)
    except (TypeError, ValueError) as error:
        return _accepted_block(
            policy,
            current_head,
            ["accepted_effect_binding_invalid"],
            candidate_head=candidate_head,
            stderr=str(error),
        )
    if isinstance(attestation, str):
        return _accepted_block(
            policy,
            current_head,
            ["accepted_atomic_update_rejected"],
            candidate_head=candidate_head,
            stderr=attestation,
        )
    blocker = _accepted_sync_blocker(root, policy, current_head, candidate_head, attestation)
    if blocker:
        return blocker
    next_policy = branch_role_policy_from_text(
        committed_file_text(root, candidate_head, ".ethos/workspace.toml")
    )
    mirror_blocker, mirror_result, attestations = _release_mirror_result(
        root=root,
        policy=next_policy,
        worktrees=worktrees,
        candidate_head=candidate_head,
        accepted_attestation=attestation,
        prior_attestations=prior_attestations,
    )
    if mirror_blocker:
        return mirror_blocker
    return {
        "verdict": "pass",
        "state": "accepted_validated",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": candidate_head,
        "previous_head": current_head,
        "attestation": attestation.model_dump(mode="json"),
        "attestations": [item.model_dump(mode="json") for item in attestations],
        "release_mirror": mirror_result,
        "required_gaps": [],
    }


def _accepted_transition_plan(
    *,
    root: Path,
    role_policy: BranchRolePolicy,
    authority: Commitment,
    effect: GitEffect,
    operation: str,
    head: str,
    prior_attestations: JsonObject,
) -> TransitionPlan:
    policy = {
        "operation": operation,
        "release_branch": role_policy.release_branch,
        "accepted_branch": role_policy.accepted_branch,
        "candidate_branch": role_policy.candidate_branch,
        "release_mirror": role_policy.release_mirror,
    }
    facts = Facts(
        repository=authority.id,
        head=head,
        tree=current_tree(root, head),
        observed_at=datetime.now(UTC),
        values={
            "operation": operation,
            "refs": {ref: update.expected for ref, update in effect.updates.items()},
            "assertions": effect.assertions,
        },
        source_refs=(
            "git:HEAD",
            "git:HEAD^{tree}",
            *(f"git:{ref}" for ref in (*effect.updates, *effect.assertions)),
        ),
    )
    return compile_git_effect_plan(
        authority,
        facts,
        prior_attestations=prior_attestations,
        policy=policy,
        effect=effect,
    )


def _promotion_topology_gaps(root, current_head, candidate_head):
    if not is_ancestor(root, current_head, candidate_head):
        return ["candidate_diverged_from_accepted"]
    return []


def _release_mirror_result(
    *, root, policy, worktrees, candidate_head, accepted_attestation, prior_attestations
):
    attestations = [accepted_attestation]
    if policy.release_mirror != RELEASE_MIRROR_ACCEPTED_FF:
        return None, {"mode": "independent", "worktree_sync": "not_enabled"}, attestations
    release_old = run_git(root, "rev-parse", policy.release_branch, check=False).stdout.strip()
    if not release_old:
        return (
            _accepted_block(
                policy,
                candidate_head,
                ["release_mirror_release_branch_missing"],
                candidate_head=candidate_head,
                accepted_advanced=True,
                attestation=accepted_attestation.model_dump(mode="json"),
            ),
            {},
            attestations,
        )
    if not is_ancestor(root, release_old, candidate_head):
        gap = (
            "release_mirror_ahead_of_accepted"
            if is_ancestor(root, candidate_head, release_old)
            else "release_mirror_diverged"
        )
        return (
            _accepted_block(
                policy,
                candidate_head,
                [gap],
                candidate_head=candidate_head,
                accepted_advanced=True,
                attestation=accepted_attestation.model_dump(mode="json"),
            ),
            {},
            attestations,
        )
    effect = GitEffect(
        updates={
            f"refs/heads/{policy.release_branch}": GitRefUpdate(
                expected=release_old,
                desired=candidate_head,
            )
        },
        assertions={
            f"refs/heads/{policy.accepted_branch}": candidate_head,
        },
    )
    try:
        authority = load_repository_commitment(root, tree_ref=candidate_head)
        plan = _accepted_transition_plan(
            root=root,
            role_policy=policy,
            authority=authority,
            effect=effect,
            operation="release.mirror",
            head=candidate_head,
            prior_attestations=prior_attestations
            | {"accepted_effect": accepted_attestation.model_dump(mode="json")},
        )
        mirror_attestation = _attempt_closeout_effect(root=root, plan=plan)
    except (TypeError, ValueError) as error:
        mirror_attestation = str(error)
    if isinstance(mirror_attestation, str):
        return (
            _accepted_block(
                policy,
                candidate_head,
                ["release_mirror_bootstrap_incomplete"],
                candidate_head=candidate_head,
                accepted_advanced=True,
                stderr=mirror_attestation,
                attestation=accepted_attestation.model_dump(mode="json"),
            ),
            {},
            attestations,
        )
    attestations.append(mirror_attestation)
    mirror_result = sync_linked_ref_worktree(
        worktrees,
        policy.release_branch,
        candidate_head,
        release_old,
    )
    return _mirror_sync_blocker(policy, candidate_head, mirror_result), mirror_result, attestations


def _mirror_sync_blocker(policy, candidate_head, mirror_result):
    if mirror_result.get("worktree_sync") not in {"failed", "dirty"}:
        return None
    gap = (
        "release_mirror_worktree_sync_failed"
        if mirror_result["worktree_sync"] == "failed"
        else "release_mirror_worktree_dirty_after_sync"
    )
    return _accepted_block(
        policy,
        candidate_head,
        [gap],
        candidate_head=candidate_head,
        release_mirror=mirror_result,
    )


def _promotion_blocker(*, root, policy, current_head, candidate_head):
    topology_gaps = _promotion_topology_gaps(root, current_head, candidate_head)
    if topology_gaps:
        return (
            _accepted_block(policy, current_head, topology_gaps, candidate_head=candidate_head),
            None,
        )
    proof = proof_attestation(root, candidate_head)
    if proof is None:
        return (
            _accepted_block(
                policy,
                current_head,
                proof_gaps(root, candidate_head),
            ),
            None,
        )
    return None, proof


def _accepted_sync_blocker(root, policy, current_head, candidate_head, attestation):
    synced = sync_current_worktree(root, candidate_head)
    if synced["state"] == "synced":
        return None
    gap = (
        "accepted_worktree_sync_failed"
        if synced["state"] == "failed"
        else "accepted_worktree_dirty_after_sync"
    )
    return _accepted_block(
        policy,
        current_head,
        [gap],
        candidate_head=candidate_head,
        accepted_advanced=True,
        status=synced.get("status", ""),
        stderr=synced.get("stderr", ""),
        attestation=attestation.model_dump(mode="json"),
    )


def _attempt_closeout_effect(
    *,
    root: Path,
    plan: TransitionPlan,
) -> Attestation | str:
    try:
        return execute_closeout_effect(root=root, plan=plan)
    except ValueError as error:
        return str(error)


def _accepted_block(policy, current, gaps, **extra):
    return {
        **accepted_payload(policy, current),
        "candidate_head": extra.pop("candidate_head", ""),
        "required_gaps": gaps,
        **extra,
    }


def accepted_payload(policy, head):
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": head,
        "candidate_head": "",
        "previous_head": head,
        "required_gaps": [],
    }
