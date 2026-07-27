"""Git effects for Work Lane landing and accepted-root closeout."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.remediation.guidance as remediation
from ethos.adapters.admission.closeout_intent.marker import CloseoutTransition
from ethos.adapters.admission.closeout_intent.marker import MarkerExpectation
from ethos.adapters.admission.closeout_intent.marker import execute_closeout_effect
from ethos.adapters.admission.closeout_intent.marker import sweep_stale_closeout_intents
from ethos.adapters.mutation.decision import evaluate_closeout_mutation
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_plan_for_attestation
from ethos.adapters.repo.dirty.change_provenance import dirty_provenance
from ethos.adapters.repo.git import GitEffectExecutionRequest
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import execute_git_effect
from ethos.adapters.repo.git import git_effect_attestations
from ethos.adapters.repo.git import git_ref_effect
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import reference_transaction_hook_changed
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git import sync_current_worktree
from ethos.adapters.repo.git import sync_linked_ref_worktree
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.lifecycle.reducer import TransitionDecision
from ethos.contracts.lifecycle.reducer import TransitionRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import PlanIR
from ethos.repository.policy.gates import gate_policy_digest

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation


def apply_land_to_candidate(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
    admitted_decision: TransitionDecision | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()

    def fail(gaps, **extra):
        return _blocked(policy, current_head, gaps, **extra)

    decision = admitted_decision or evaluate_mutation(
        TransitionRequest(
            command="land",
            apply=True,
            authorized=authorized,
            expect_head=expect_head,
        ),
        root=root,
        current_head=current_head,
    )
    if not decision.ok:
        return fail(
            list(decision.gaps),
            state=decision.state,
            remediation=remediation.remediation_for_gaps(decision.gaps),
        )
    base_report = candidate_base_report(root=root)
    if not base_report["ok"]:
        return base_report
    candidate_path = Path(str(base_report["path"]))
    proof = proof_attestation(candidate_path, current_head)
    if proof is None:
        return fail(["proof_not_proven"], path=candidate_path.as_posix())
    candidate_head = str(base_report["candidate_head"])
    try:
        policy_digest = gate_policy_digest(root, tree_ref=current_head)
        plan, change_contract_digest, repository_facts_digest = _proof_attestation_bindings(
            candidate_path,
            proof,
            policy_digest=policy_digest,
        )
        effect = GitEffect(
            id=f"git-effect:candidate:{policy.candidate_branch}:{current_head}",
            plan_digest=proof.plan_digest,
            updates={
                f"refs/heads/{policy.candidate_branch}": GitRefUpdate(
                    expected=candidate_head,
                    desired=current_head,
                )
            },
        )
        attestation = execute_git_effect(
            root,
            effect,
            GitEffectExecutionRequest(
                issuer=_effect_issuer(),
                attestations=git_effect_attestations(root, effect),
                permissions=plan.permissions,
                change_contract_digest=change_contract_digest,
                repository_facts_digest=repository_facts_digest,
                policy_digest=policy_digest,
            ),
        )
        git_effect_attestations(root, effect, attestation)
    except (TypeError, ValueError) as error:
        gaps = ["candidate_update_failed"]
        return fail(
            gaps,
            path=candidate_path.as_posix(),
            remediation=remediation.remediation_for_gaps(gaps),
            stderr=str(error),
        )
    synced = run_git(candidate_path, "reset", "--hard", current_head, check=False)
    if synced.returncode:
        return fail(
            ["candidate_worktree_sync_failed"],
            path=candidate_path.as_posix(),
            stderr=synced.stderr.strip(),
            attestation=attestation.model_dump(mode="json"),
        )
    return {
        "ok": True,
        "state": "candidate_validated",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "attestation": attestation.model_dump(mode="json"),
        "required_gaps": [],
    }


def _blocked(policy, head, gaps, *, state="blocked", **extra):
    return dict(
        ok=False,
        state=state,
        branch=policy.candidate_branch,
        head=head,
        required_gaps=gaps,
        **extra,
    )


def apply_candidate_to_accepted(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
    candidate_head: str | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    decision = evaluate_closeout_mutation(
        TransitionRequest(
            command="closeout",
            apply=True,
            authorized=authorized,
            expect_head=expect_head,
        ),
        root=root,
        current_head=current_head,
    )
    if not decision.ok:
        return {
            **_accepted_payload(policy, current_head),
            "state": decision.state,
            "required_gaps": list(decision.gaps),
            "remediation": remediation.remediation_for_gaps(decision.gaps),
        }
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])
    observed_candidate_head = str(candidate["head"])
    if candidate_head is not None and observed_candidate_head != candidate_head:
        gaps = ["candidate_head_changed_after_control_replacement_check"]
        return {
            **_accepted_payload(policy, current_head),
            "candidate_head": observed_candidate_head,
            "verified_candidate_head": candidate_head,
            "required_gaps": gaps,
            "remediation": remediation.remediation_for_gaps(gaps),
        }
    candidate_head = candidate_head or observed_candidate_head
    policy = branch_role_policy_from_text(
        committed_file_text(root, candidate_head, ".ethos/workspace.toml")
    )
    if decision.state == "current" and policy.release_mirror != RELEASE_MIRROR_ACCEPTED_FF:
        return {
            **_accepted_payload(policy, current_head),
            "ok": True,
            "state": "accepted_current",
            "candidate_head": candidate_head,
            "attestation": {},
        }
    return _promote_candidate(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
        status=status,
    )


def _effect_issuer() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"


def _promote_candidate(*, root, policy, current_head, candidate_head, status):
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
    policy_digest = gate_policy_digest(root, tree_ref=candidate_head)
    result = None
    try:
        plan, change_contract_digest, repository_facts_digest = _proof_attestation_bindings(
            root,
            proof,
            policy_digest=policy_digest,
        )
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
            change_contract_digest=change_contract_digest,
            repository_facts_digest=repository_facts_digest,
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
            "attestation": cast("Attestation", attestation).model_dump(mode="json"),
            "attestations": [item.model_dump(mode="json") for item in attestations],
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
                attestation=attestation.model_dump(mode="json"),
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
        attestation=attestation.model_dump(mode="json"),
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


def _proof_attestation_bindings(
    root: Path,
    proof: Attestation,
    *,
    policy_digest: str,
) -> tuple[PlanIR, str, str]:
    plan = proof_plan_for_attestation(root, proof)
    if not proof.plan_digest:
        msg = "git_effect_binding_missing:plan_digest"
        raise ValueError(msg)
    if proof.policy_digest != policy_digest or plan.policy_digest != policy_digest:
        msg = "git_effect_binding_stale:policy_digest"
        raise ValueError(msg)
    return plan, proof.change_contract_digest, proof.repository_facts_digest


def _accepted_block(policy, current, gaps, **extra):
    return {
        **_accepted_payload(policy, current),
        "candidate_head": extra.pop("candidate_head", ""),
        "required_gaps": gaps,
        **extra,
    }


def _accepted_payload(policy, head):
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


def candidate_base_report(*, root: Path, status=None) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    supplied_status = status is not None
    status = status if status is not None else workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])

    def fail(gaps: list[str], **extra: object) -> dict[str, object]:
        return _blocked(policy, current_head, gaps, **extra)

    if not candidate["exists"]:
        return fail(["candidate_branch_missing"])
    if not candidate["worktree_exists"]:
        return fail(["candidate_worktree_missing"])
    candidate_path = Path(str(candidate["worktree_path"]))
    candidate_dirty = (
        dirty_provenance(candidate_path)["dirty"]
        if supplied_status
        else workspace_status(candidate_path)["dirty"]
    )
    if candidate_dirty:
        return fail(
            ["candidate_worktree_dirty"],
            path=candidate_path.as_posix(),
        )
    candidate_head = run_git(root, "rev-parse", policy.candidate_branch, check=False).stdout.strip()
    if not is_ancestor(root, candidate_head, current_head):
        return fail(
            ["candidate_base_stale"],
            candidate_head=candidate_head,
            path=candidate_path.as_posix(),
            remediation=remediation.remediation_for_gaps(["candidate_base_stale"]),
        )
    return {
        "ok": True,
        "state": "candidate_base_current",
        "branch": policy.candidate_branch,
        "head": current_head,
        "candidate_head": candidate_head,
        "path": candidate_path.as_posix(),
        "required_gaps": [],
    }
