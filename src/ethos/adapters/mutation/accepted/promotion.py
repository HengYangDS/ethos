"""Accepted-root promotion effects for a proven candidate revision."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.actor import process_issuer
from ethos.adapters.admission.ref_intent import sweep_stale_ref_intents
from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.commit.provenance import accepted_provenance
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import ref_worktree_paths
from ethos.adapters.repo.git_ref_worktrees import sync_linked_ref_worktree
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.branch.roles import BranchRolePolicy
    from ethos.contracts.value import JsonObject


def current_acceptance(
    *,
    root: Path,
    policy: BranchRolePolicy,
    current_head: str,
    candidate_head: str,
    status: dict[str, object],
    expected_head: str | None = None,
) -> dict[str, object] | None:
    """Recognize an attested ref effect separately from its worktree materialization."""
    if current_head != candidate_head:
        return None
    if (
        policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
        and ref_head(root, f"refs/heads/{policy.release_branch}") != candidate_head
    ):
        return None
    try:
        recorded = accepted_provenance(
            root,
            accepted_ref=f"refs/heads/{policy.accepted_branch}",
            candidate_ref=f"refs/heads/{policy.candidate_branch}",
            head=candidate_head,
        )
        plan = recorded.plan if recorded else None
        effect = git_effect_from_plan(plan) if plan else None
        previous = effect.updates.get(f"refs/heads/{policy.accepted_branch}") if effect else None
        original_previous = previous.expected if previous else current_head
        previous_head = recorded.previous_head if recorded else current_head
        if expected_head is not None and expected_head not in {
            current_head,
            previous_head,
            original_previous,
        }:
            return None
        pending = _materialization_pending(root, policy, status, current_head, effect)
    except ValueError as error:
        return _accepted_block(policy, current_head, [str(error)])
    return {
        **accepted_payload(policy, current_head),
        "verdict": "pass",
        "state": "accepted_materialization_pending" if pending else "accepted_current",
        "candidate_head": candidate_head,
        "previous_head": (
            original_previous
            if expected_head == original_previous
            else previous_head
            if pending or expected_head == previous_head
            else current_head
        ),
        "attestation": recorded.attestation.model_dump(mode="json") if recorded else {},
        "provenance": recorded.projection() if recorded else {},
    }


def _materialization_pending(
    root: Path,
    policy: BranchRolePolicy,
    status: dict[str, object],
    head: str,
    effect: GitEffect | None,
) -> bool:
    """Accept only terminal bytes or the exact preimage of a recorded ref update."""
    scopes = [(policy.accepted_branch, (root,), "accepted")]
    if policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF:
        scopes.append(
            (
                policy.release_branch,
                ref_worktree_paths(
                    cast("list[dict[str, object]]", status.get("worktrees", [])),
                    policy.release_branch,
                ),
                "release_mirror",
            )
        )
    pending = False
    for branch, paths, prefix in scopes:
        terminal_gap = worktree_sync_gap(
            root, paths=paths, branch=branch, ref_head=head, previous=head, head=head
        )
        if not terminal_gap:
            continue
        update = effect.updates.get(f"refs/heads/{branch}") if effect else None
        gap = (
            worktree_sync_gap(
                root, paths=paths, branch=branch, ref_head=head, previous=update.expected, head=head
            )
            if update
            else terminal_gap
        )
        if gap:
            message = f"{prefix}_{gap}"
            raise ValueError(message)
        pending = True
    return pending


def recover_current_acceptance(
    *,
    root: Path,
    policy: BranchRolePolicy,
    current_head: str,
    status: dict[str, object],
    current: dict[str, object],
) -> dict[str, object]:
    """Freshly admit remaining file effects without repeating the recorded ref CAS."""
    attestation = Attestation.model_validate(current["attestation"])
    plan = plan_from_attestation(attestation)
    try:
        admit_git_effect(root, plan)
    except ValueError as error:
        return _accepted_block(policy, current_head, [str(error)])
    effect = git_effect_from_plan(plan)
    release = effect.updates.get(f"refs/heads/{policy.release_branch}")
    result = _synchronize_promotion(
        root,
        worktrees=cast("list[dict[str, object]]", status.get("worktrees", [])),
        policy=policy,
        current_head=effect.updates[f"refs/heads/{policy.accepted_branch}"].expected,
        candidate_head=current_head,
        release_old=release.expected if release else None,
        attestation=attestation,
    )
    if result["verdict"] == "pass":
        result["state"] = "accepted_current"
    return result


def promote_candidate(
    *,
    root: Path,
    policy: BranchRolePolicy,
    current_head: str,
    candidate_head: str,
    status: Mapping[str, object],
    control_replacement_receipt: dict[str, object] | None = None,
    apply: bool = True,
    identity_transition: bool = False,
) -> dict[str, object]:
    """Advance the accepted branch to a proven candidate, or report what blocks it."""
    admitted = _promotion_blocker(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
    )
    if isinstance(admitted, dict):
        return admitted
    return _candidate_promotion(
        root=root,
        policy=policy,
        status=status,
        current_head=current_head,
        candidate_head=candidate_head,
        proof=admitted,
        control_replacement_receipt=control_replacement_receipt,
        apply=apply,
        identity_transition=identity_transition,
    )


def _candidate_promotion(
    *,
    root: Path,
    policy: BranchRolePolicy,
    status: Mapping[str, object],
    current_head: str,
    candidate_head: str,
    proof: Attestation,
    control_replacement_receipt: dict[str, object] | None,
    apply: bool,
    identity_transition: bool,
) -> dict[str, object]:
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
    if apply:
        sweep_stale_ref_intents(root)
    try:
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
            paths=(root,),
            branch=policy.accepted_branch,
            ref_head=current_head,
            previous=current_head,
            head=candidate_head,
        )
        preflight_gap = f"accepted_{preflight_gap}" if preflight_gap else ""
        if (
            not preflight_gap
            and release_old is not None
            and (
                gap := worktree_sync_gap(
                    root,
                    paths=ref_worktree_paths(worktrees, policy.release_branch),
                    branch=policy.release_branch,
                    ref_head=release_old,
                    previous=release_old,
                    head=candidate_head,
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
            effect=effect,
            head=current_head,
            candidate_worktree_path=candidate_worktree_path,
            prior_attestations=prior_attestations,
            identity_transition=identity_transition,
        )
        if not apply:
            admit_git_effect(root, plan)
            return {
                **accepted_payload(policy, current_head),
                "verdict": "pass",
                "state": "ready_to_closeout",
                "candidate_head": candidate_head,
                "transition_plan": plan.model_dump(mode="json"),
                "required_gaps": [],
            }
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
            issuer=process_issuer(),
        )
    except ValueError as error:
        report = _accepted_block(
            policy,
            current_head,
            ["accepted_atomic_update_rejected"],
            candidate_head=candidate_head,
            stderr=str(error),
        )
        if isinstance(error, ProcessExecutionError):
            report["process_failure"] = error.evidence()
            if error.observation.get("outcome") != "unchanged":
                report.update(verdict="unknown", state="partial_transition")
        return report
    return _synchronize_promotion(
        root,
        worktrees=worktrees,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
        release_old=release_old,
        attestation=attestation,
    )


def _synchronize_promotion(
    root: Path,
    *,
    worktrees: list[dict[str, object]],
    policy: BranchRolePolicy,
    current_head: str,
    candidate_head: str,
    release_old: str | None,
    attestation: Attestation,
) -> dict[str, object]:
    """Reconcile accepted and mirrored checkouts after the single admitted ref effect."""
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
    effect: GitEffect,
    head: str,
    candidate_worktree_path: str,
    prior_attestations: JsonObject,
    identity_transition: bool = False,
) -> TransitionPlan:
    effect_policy = {
        "operation": "candidate.accept",
        "release_branch": role_policy.release_branch,
        "accepted_branch": role_policy.accepted_branch,
        "candidate_branch": role_policy.candidate_branch,
        "release_mirror": role_policy.release_mirror,
    }
    return compile_observed_git_effect(
        root,
        None,
        effect,
        head=head,
        prior_attestations=prior_attestations,
        policy=effect_policy,
        values={"candidate_worktree_path": candidate_worktree_path},
        identity_transition=identity_transition,
    )


def _promotion_effect(
    root: Path, policy: BranchRolePolicy, current_head: str, candidate_head: str
) -> tuple[GitEffect, str | None]:
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
    release_ref = f"refs/heads/{policy.release_branch}"
    # A declared mirror without its branch is created in this transaction; a present one must
    # still be an ancestor of the candidate head.
    release_old = ref_head(root, release_ref, "0" * len(candidate_head))
    if release_old.strip("0") and not is_ancestor(root, release_old, candidate_head):
        message = "release_mirror_diverged"
        raise ValueError(message)
    updates[release_ref] = GitRefUpdate(
        expected=release_old,
        desired=candidate_head,
    )
    assertions = {
        f"refs/heads/{
            policy.accepted_branch if current_head == candidate_head else policy.candidate_branch
        }": candidate_head
    }
    return GitEffect(updates=updates, assertions=assertions), release_old


def _promotion_blocker(
    *, root: Path, policy: BranchRolePolicy, current_head: str, candidate_head: str
) -> dict[str, object] | Attestation:
    """Return the block that stops promotion, or the proof that admits it."""
    if not is_ancestor(root, current_head, candidate_head):
        return _accepted_block(
            policy,
            current_head,
            ["candidate_diverged_from_accepted"],
            candidate_head=candidate_head,
        )
    proof, gaps = proof_for_repository_transition(root, candidate_head)
    if proof is None:
        return _accepted_block(policy, current_head, gaps, candidate_head=candidate_head)
    return proof


def _accepted_block(
    policy: BranchRolePolicy, current: str, gaps: list[str], **extra: object
) -> dict[str, object]:
    return {
        **accepted_payload(policy, current),
        "candidate_head": extra.pop("candidate_head", ""),
        "required_gaps": gaps,
        **extra,
    }


def accepted_payload(policy: BranchRolePolicy, head: str) -> dict[str, object]:
    """Return the blocked accepted-branch report that a decision then completes."""
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
