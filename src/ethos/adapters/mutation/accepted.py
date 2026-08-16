"""Accepted-root promotion effects for a proven candidate revision."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.ref_intent import sweep_stale_ref_intents
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.commitment import terminal_v1_binding
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import ref_worktree_paths
from ethos.adapters.repo.git_ref_worktrees import sync_linked_ref_worktree
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.branch.roles import BranchRolePolicy
    from ethos.contracts.semantic import Attestation
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


def promote_candidate(
    *,
    root,
    policy,
    current_head,
    candidate_head,
    status,
    control_replacement_receipt=None,
):
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
        control_replacement_receipt=control_replacement_receipt,
    )


def _apply_candidate_promotion(
    *,
    root,
    policy,
    status,
    current_head,
    candidate_head,
    proof,
    control_replacement_receipt,
):
    worktrees = cast("list[dict[str, object]]", status.get("worktrees", []))
    candidate = cast("dict[str, object]", status.get("candidate", {}))
    candidate_worktree_path = str(candidate.get("worktree_path") or "")
    if not candidate_worktree_path:
        return _accepted_block(
            policy,
            current_head,
            ["candidate_worktree_binding_stale"],
            candidate_head=candidate_head,
        )
    sweep_stale_ref_intents(root)
    try:
        try:
            authority = load_repository_commitment(root, tree_ref=current_head)
            prestate = {}
        except ValueError as error:
            if not str(error).startswith("repository_commitment_missing:"):
                raise
            authority = load_repository_commitment(root, tree_ref=candidate_head)
            prestate = terminal_v1_binding(
                root,
                tree_ref=current_head,
                carrier=".ethos/commitment.toml",
                repository=True,
            )
        prior_attestations = {
            "proof": proof.model_dump(mode="json"),
            **(
                {"control_replacement_receipt": control_replacement_receipt}
                if control_replacement_receipt
                else {}
            ),
        }
        effect, release_old = _promotion_effect(root, policy, current_head, candidate_head)
        preflight_gap = worktree_sync_gap(
            root,
            (root,),
            policy.accepted_branch,
            current_head,
            current_head,
            candidate_head,
        )
        preflight_gap = f"accepted_{preflight_gap}" if preflight_gap else ""
        if (
            not preflight_gap
            and release_old is not None
            and (
                gap := worktree_sync_gap(
                    root,
                    ref_worktree_paths(worktrees, policy.release_branch),
                    policy.release_branch,
                    release_old,
                    release_old,
                    candidate_head,
                )
            )
        ):
            preflight_gap = f"release_mirror_{gap}"
        if preflight_gap:
            return _accepted_block(
                policy,
                current_head,
                [preflight_gap],
                candidate_head=candidate_head,
            )
        plan = _accepted_transition_plan(
            root=root,
            role_policy=policy,
            authority=authority,
            effect=effect,
            head=current_head,
            candidate_worktree_path=candidate_worktree_path,
            prior_attestations=prior_attestations,
            prestate=prestate,
        )
    except (TypeError, ValueError) as error:
        return _accepted_block(
            policy,
            current_head,
            ["accepted_transition_invalid"],
            candidate_head=candidate_head,
            stderr=str(error),
        )
    try:
        attestation = execute_git_effect(
            root,
            plan,
            issuer=os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos",
        )
    except ValueError as error:
        return _accepted_block(
            policy,
            current_head,
            ["accepted_atomic_update_rejected"],
            candidate_head=candidate_head,
            stderr=str(error),
        )
    mirror_result = (
        sync_linked_ref_worktree(
            root,
            worktrees,
            policy.release_branch,
            candidate_head,
            release_old,
        )
        if release_old is not None
        else {"mode": "independent", "worktree_sync": "not_enabled"}
    )
    accepted_sync = cast(
        "list[dict[str, str]]",
        sync_ref_worktrees(
            root,
            (root,),
            policy.accepted_branch,
            candidate_head,
            current_head,
        )["worktrees"],
    )[0]
    gaps = [
        *(
            ["release_mirror_worktree_sync_failed"]
            if mirror_result.get("worktree_sync") == "failed"
            else ["release_mirror_worktree_dirty_after_sync"]
            if mirror_result.get("worktree_sync") == "dirty"
            else []
        ),
        *(
            ["accepted_worktree_sync_failed"]
            if accepted_sync["state"] == "failed"
            else ["accepted_worktree_dirty_after_sync"]
            if accepted_sync["state"] == "dirty"
            else []
        ),
    ]
    if gaps:
        return _accepted_block(
            policy,
            candidate_head,
            gaps,
            candidate_head=candidate_head,
            accepted_advanced=True,
            attestation=attestation.model_dump(mode="json"),
            release_mirror=mirror_result,
            accepted_worktree=accepted_sync,
        )
    return {
        "verdict": "pass",
        "state": "accepted_validated",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": candidate_head,
        "previous_head": current_head,
        "attestation": attestation.model_dump(mode="json"),
        "release_mirror": mirror_result,
        "required_gaps": [],
    }


def _accepted_transition_plan(
    *,
    root: Path,
    role_policy: BranchRolePolicy,
    authority: Commitment,
    effect: GitEffect,
    head: str,
    candidate_worktree_path: str,
    prior_attestations: JsonObject,
    prestate: dict[str, object],
) -> TransitionPlan:
    effect_policy = {
        "operation": "candidate.accept",
        "release_branch": role_policy.release_branch,
        "accepted_branch": role_policy.accepted_branch,
        "candidate_branch": role_policy.candidate_branch,
        "release_mirror": role_policy.release_mirror,
        "repository_commitment_bootstrap": bool(prestate),
        **(
            {
                "prestate_repository_id": str(prestate["id"]),
                "prestate_repository_bytes_sha256": str(prestate["bytes_sha256"]),
            }
            if prestate
            else {}
        ),
    }
    return compile_observed_git_effect(
        root,
        authority,
        effect,
        head=head,
        prior_attestations=prior_attestations,
        policy=effect_policy,
        values={"candidate_worktree_path": candidate_worktree_path},
    )


def _promotion_effect(root, policy, current_head, candidate_head):
    updates = {
        f"refs/heads/{policy.accepted_branch}": GitRefUpdate(
            expected=current_head,
            desired=candidate_head,
        )
    }
    if current_head == candidate_head:
        updates.clear()
    if policy.release_mirror != RELEASE_MIRROR_ACCEPTED_FF:
        return GitEffect(
            updates=updates,
            assertions={f"refs/heads/{policy.candidate_branch}": candidate_head},
        ), None
    release_old = run_git(root, "rev-parse", policy.release_branch, check=False).stdout.strip()
    if not release_old:
        message = "release_mirror_release_branch_missing"
        raise ValueError(message)
    if not is_ancestor(root, release_old, candidate_head):
        message = "release_mirror_diverged"
        raise ValueError(message)
    updates[f"refs/heads/{policy.release_branch}"] = GitRefUpdate(
        expected=release_old,
        desired=candidate_head,
    )
    assertions = {
        f"refs/heads/{
            policy.accepted_branch if current_head == candidate_head else policy.candidate_branch
        }": candidate_head
    }
    return GitEffect(updates=updates, assertions=assertions), release_old


def _promotion_blocker(*, root, policy, current_head, candidate_head):
    if not is_ancestor(root, current_head, candidate_head):
        return (
            _accepted_block(
                policy,
                current_head,
                ["candidate_diverged_from_accepted"],
                candidate_head=candidate_head,
            ),
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
