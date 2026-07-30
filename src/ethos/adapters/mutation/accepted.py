"""Accepted-root promotion effects for a proven candidate revision."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.closeout_intent.marker import CloseoutTransition
from ethos.adapters.admission.closeout_intent.marker import MarkerExpectation
from ethos.adapters.admission.closeout_intent.marker import execute_closeout_effect
from ethos.adapters.admission.closeout_intent.marker import sweep_stale_closeout_intents
from ethos.adapters.mutation.attestation_projection import attestation_payload
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_plan_for_attestation
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effects import git_ref_effect
from ethos.adapters.repo.git_effects import reference_transaction_hook_changed
from ethos.adapters.repo.git_effects import sync_current_worktree
from ethos.adapters.repo.git_effects import sync_linked_ref_worktree
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import GitEffect
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Attestation


def promote_candidate(*, root, policy, current_head, candidate_head, status):
    mirror = policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    release_old = (
        run_git(root, "rev-parse", policy.release_branch, check=False).stdout.strip()
        if mirror
        else ""
    )
    blocker, proof = _promotion_blocker(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
        release_old=release_old if mirror else None,
    )
    if blocker:
        return blocker
    proof = cast("Attestation", proof)
    return _apply_candidate_promotion(
        root=root,
        policy=policy,
        status=status,
        heads=(current_head, candidate_head),
        context=(mirror, release_old, proof),
    )


def _apply_candidate_promotion(*, root, policy, status, heads, context):
    current_head, candidate_head = heads
    mirror, release_old, proof = context
    worktrees = cast("list[dict[str, object]]", status.get("worktrees", []))
    sweep_stale_closeout_intents(root)
    transitions = (
        CloseoutTransition(
            f"refs/heads/{policy.accepted_branch}",
            current_head,
            candidate_head,
            candidate_head,
        ),
        *(
            (
                CloseoutTransition(
                    f"refs/heads/{policy.release_branch}",
                    release_old,
                    candidate_head,
                    candidate_head,
                ),
            )
            if mirror
            else ()
        ),
    )
    evidence_digest = proof.id
    result = None
    try:
        plan, commitment_digest, facts_digest = proof_attestation_bindings(root, proof)
        policy_digest = proof.policy_digest
    except (TypeError, ValueError) as error:
        result = _accepted_block(
            policy,
            current_head,
            ["accepted_effect_binding_invalid"],
            candidate_head=candidate_head,
            stderr=str(error),
        )
    if result is None:
        bootstrap, bootstrap_gap = _release_bootstrap(root, current_head, candidate_head, mirror)
        if bootstrap_gap:
            result = _accepted_block(
                policy, current_head, [bootstrap_gap], candidate_head=candidate_head
            )
    if result is None:
        first_leg = transitions[:1] if bootstrap else transitions
        effect = git_ref_effect(
            f"git-effect:closeout:{policy.accepted_branch}:{candidate_head}",
            proof.plan_digest,
            first_leg,
            {f"refs/heads/{policy.candidate_branch}": candidate_head},
        )
        permissions = plan.permissions
        expectation = MarkerExpectation(
            evidence_digest=evidence_digest,
            gate_policy_digest=policy_digest,
            commitment_digest=commitment_digest,
            facts_digest=facts_digest,
        )
        attestation = _attempt_closeout_effect(
            root=root,
            effect=effect,
            transitions=first_leg,
            expectation=expectation,
            permissions=permissions,
        )
        if isinstance(attestation, str):
            result = _accepted_block(
                policy,
                current_head,
                ["accepted_atomic_update_rejected"],
                candidate_head=candidate_head,
                stderr=attestation,
            )
    if result is None:
        result = _accepted_sync_blocker(root, policy, current_head, candidate_head, attestation)
    if result is None:
        mirror_blocker, attestations = _mirror_bootstrap_result(
            root=root,
            policy=policy,
            candidate_head=candidate_head,
            transitions=transitions,
            context=(bootstrap, attestation, effect, expectation, permissions),
        )
        result = mirror_blocker
    if result is None:
        mirror_result = sync_linked_ref_worktree(
            worktrees, policy.release_branch if mirror else "", candidate_head, release_old
        )
        result = _mirror_sync_blocker(policy, candidate_head, mirror_result)
    if result is None:
        result = {
            "ok": True,
            "state": "accepted_validated",
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": candidate_head,
            "previous_head": current_head,
            "attestation": attestation_payload(cast("Attestation", attestation), kind="effect"),
            "attestations": [attestation_payload(item, kind="effect") for item in attestations],
            "release_mirror": mirror_result,
            "required_gaps": [],
        }
    return result


def _promotion_topology_gaps(root, current_head, candidate_head, release_old):
    if not is_ancestor(root, current_head, candidate_head):
        return ["candidate_diverged_from_accepted"]
    if release_old is None or (release_old and is_ancestor(root, release_old, current_head)):
        return []
    if not release_old:
        return ["release_mirror_release_branch_missing"]
    gap = (
        "release_mirror_ahead_of_accepted"
        if is_ancestor(root, current_head, release_old)
        else "release_mirror_diverged"
    )
    return [gap]


def _mirror_bootstrap_result(*, root, policy, candidate_head, transitions, context):
    bootstrap, attestation, effect, expectation, permissions = context
    attestations = [attestation]
    if not bootstrap:
        return None, attestations
    release = transitions[1]
    mirror_effect = git_ref_effect(
        f"git-effect:release-mirror:{policy.release_branch}:{candidate_head}",
        effect.plan_digest,
        (release,),
        {
            f"refs/heads/{policy.accepted_branch}": candidate_head,
            f"refs/heads/{policy.candidate_branch}": candidate_head,
        },
    )
    mirror_attestation = _attempt_closeout_effect(
        root=root,
        effect=mirror_effect,
        transitions=(release,),
        expectation=expectation,
        permissions=permissions,
    )
    if isinstance(mirror_attestation, str):
        return (
            _accepted_block(
                policy,
                candidate_head,
                ["release_mirror_bootstrap_incomplete"],
                candidate_head=candidate_head,
                accepted_advanced=True,
                stderr=mirror_attestation,
                attestation=attestation_payload(attestation, kind="effect"),
            ),
            attestations,
        )
    attestations.append(mirror_attestation)
    return None, attestations


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


def _promotion_blocker(*, root, policy, current_head, candidate_head, release_old):
    topology_gaps = _promotion_topology_gaps(root, current_head, candidate_head, release_old)
    if topology_gaps:
        return (
            _accepted_block(policy, current_head, topology_gaps, candidate_head=candidate_head),
            None,
        )
    proof = proof_attestation(root, candidate_head)
    if proof is None:
        return _accepted_block(policy, current_head, ["proof_not_proven"]), None
    return None, proof


def _release_bootstrap(root, current_head, candidate_head, mirror):
    if not mirror:
        return False, ""
    try:
        return reference_transaction_hook_changed(root, current_head, candidate_head), ""
    except ValueError as error:
        return False, str(error)


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
        attestation=attestation_payload(attestation, kind="effect"),
    )


def _attempt_closeout_effect(
    *,
    root: Path,
    effect: GitEffect,
    transitions: tuple[CloseoutTransition, ...],
    expectation: MarkerExpectation,
    permissions: tuple[str, ...],
) -> Attestation | str:
    try:
        return execute_closeout_effect(
            root=root,
            effect=effect,
            transitions=transitions,
            expectation=expectation,
            permissions=permissions,
        )
    except ValueError as error:
        return str(error)


def proof_attestation_bindings(
    root: Path,
    proof: Attestation,
) -> tuple[TransitionPlan, str, str]:
    plan = proof_plan_for_attestation(root, proof)
    if not proof.plan_digest:
        msg = "git_effect_binding_missing:plan_digest"
        raise ValueError(msg)
    if proof.policy_digest != plan.policy_digest:
        msg = "git_effect_binding_stale:policy_digest"
        raise ValueError(msg)
    return plan, proof.commitment_digest, proof.facts_digest


def _accepted_block(policy, current, gaps, **extra):
    return {
        **accepted_payload(policy, current),
        "candidate_head": extra.pop("candidate_head", ""),
        "required_gaps": gaps,
        **extra,
    }


def accepted_payload(policy, head):
    return {
        "ok": False,
        "state": "blocked",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": head,
        "candidate_head": "",
        "previous_head": head,
        "required_gaps": [],
    }
