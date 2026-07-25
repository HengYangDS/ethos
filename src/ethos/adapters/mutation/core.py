from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.remediation.core as remediation
from ethos.adapters.admission.closeout_intent.core import CloseoutTransition
from ethos.adapters.admission.closeout_intent.core import execute_closeout_effect
from ethos.adapters.admission.closeout_intent.core import sweep_stale_closeout_intents
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.mutation.carriers import openspec_carrier_gaps
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.mutation.proof import gate_policy_gaps
from ethos.adapters.mutation.proof import promotion_completeness_gaps
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import execute_git_effect
from ethos.adapters.repo.git import git_effect_attestations
from ethos.adapters.repo.git import git_ref_effect
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import reference_transaction_hook_changed
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git import sync_current_worktree
from ethos.adapters.repo.git import sync_linked_ref_worktree
from ethos.adapters.repo.status.core import workspace_status
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.transition import TransitionDecision
from ethos.contracts.transition import TransitionFacts
from ethos.contracts.transition import TransitionRequest
from ethos.contracts.transition import reduce_transition
from ethos.contracts.workflow import load_workflow_contract_declaration
from ethos.repository.policy.gates import gate_policy_digest


def _transition_policy(root: Path, identifier: str):
    return load_workflow_contract_declaration(root).policy(identifier)


def proof_gaps(root, current_head):
    """Return exact-HEAD proof blockers."""
    record = executed_proof_record(root, current_head)
    if record is None:
        return ["proof_not_proven"]
    return [
        *promotion_completeness_gaps(root, current_head),
        *gate_policy_gaps(root, current_head),
    ]


def proof_readiness_report(root, current_head):
    """Describe whether the exact HEAD has valid executed proof evidence."""
    gaps = proof_gaps(root, current_head)
    independent = independent_verification_admission_report(
        root=root,
        action="publish",
        request=independent_verification_request(root=root, action="publish"),
    )
    return {
        "kind": "executed_proof_readiness",
        "head": current_head,
        "state": "proven" if not gaps else "missing",
        "blocking": bool(gaps),
        "local_readiness": not gaps,
        "evidence_class": str(independent.get("evidence_class") or "local_readiness"),
        "independent_verification": independent,
        "required_gaps": gaps,
        "next_action": (
            "" if not gaps else f"ethos prove --execute --expect-head {current_head} --json"
        ),
    }


def _closeout_candidate_gaps(root, candidate, current_head, *, require_proof=True):
    """Candidate-side closeout blockers, ordered by lifecycle before evidence."""
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    candidate_path = Path(str(candidate["worktree_path"]))
    if workspace_status(candidate_path)["dirty"]:
        return ["candidate_worktree_dirty"]
    candidate_head = str(candidate.get("head") or "")
    if not is_ancestor(root, current_head, candidate_head):
        return ["candidate_diverged_from_accepted"]
    gaps = openspec_carrier_gaps(candidate_path, ROLE_CANDIDATE)
    return gaps + proof_gaps(candidate_path, candidate_head) if require_proof else gaps


def evaluate_mutation(request, *, root, current_head, status=None):
    if not request.apply and request.command != "land":
        return reduce_transition(
            _transition_policy(root, "work_lane"),
            request,
            TransitionFacts(current_head=current_head),
        )
    status = status if status is not None else workspace_status(root)
    closeout = cast("dict[str, object]", status.get("closeout_support", {}))
    return reduce_transition(
        _transition_policy(root, "work_lane"),
        request,
        TransitionFacts(
            current_head=current_head,
            role=str(status["role"]),
            dirty=bool(status["dirty"]),
            initial_gaps=tuple(
                str(gap)
                for gap in (
                    *openspec_carrier_gaps(root, ROLE_WORK_LANE),
                    *cast("list[object]", closeout.get("required_gaps", [])),
                )
            ),
            evidence_gaps=tuple(proof_gaps(root, current_head)),
        ),
    )


def evaluate_closeout_mutation(request, *, root, current_head):
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])
    return reduce_transition(
        _transition_policy(root, "closeout"),
        request,
        TransitionFacts(
            current_head=current_head,
            role=str(status["role"]),
            dirty=bool(status["dirty"]),
            initial_gaps=(
                *openspec_carrier_gaps(root, ROLE_ACCEPTED_ROOT),
                *_closeout_candidate_gaps(
                    root,
                    candidate,
                    current_head,
                    require_proof=request.apply
                    and str(candidate.get("head") or "") != current_head,
                ),
            ),
            current=str(candidate.get("head") or "") == current_head,
        ),
    )


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
    proof = executed_proof_record(candidate_path, current_head)
    if proof is None:
        return fail(["proof_not_proven"], path=candidate_path.as_posix())
    candidate_head = str(base_report["candidate_head"])
    effect = GitEffect(
        id=f"git-effect:candidate:{policy.candidate_branch}:{current_head}",
        plan_digest=str(proof["plan_digest"]),
        updates={
            f"refs/heads/{policy.candidate_branch}": GitRefUpdate(
                expected=candidate_head,
                desired=current_head,
            )
        },
    )
    permissions = tuple(str(item) for item in proof["plan"].get("permissions", ()))
    try:
        attestation = execute_git_effect(
            root,
            effect,
            issuer=_effect_issuer(),
            attestations=git_effect_attestations(root, effect.id),
            permissions=permissions,
        )
        git_effect_attestations(root, effect.id, attestation)
    except ValueError as error:
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
    proof = cast("dict[str, object]", proof)
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
    evidence_digest = str(proof.get("evidence_digest") or "")
    policy_digest = gate_policy_digest(root, tree_ref=candidate_head)
    bootstrap, bootstrap_gap = _release_bootstrap(root, current_head, candidate_head, mirror)
    if bootstrap_gap:
        return _accepted_block(policy, current_head, [bootstrap_gap], candidate_head=candidate_head)
    first_leg = transitions[:1] if bootstrap else transitions
    effect = git_ref_effect(
        f"git-effect:closeout:{policy.accepted_branch}:{candidate_head}",
        str(proof["plan_digest"]),
        first_leg,
        {f"refs/heads/{policy.candidate_branch}": candidate_head},
    )
    permissions = tuple(str(item) for item in proof["plan"].get("permissions", ()))
    attestation, error = _execute_closeout_effect(
        root, effect, first_leg, evidence_digest, policy_digest, permissions
    )
    if error:
        return _accepted_block(
            policy,
            current_head,
            ["accepted_atomic_update_rejected"],
            candidate_head=candidate_head,
            stderr=error,
        )
    sync_blocker = _accepted_sync_blocker(root, policy, current_head, candidate_head, attestation)
    if sync_blocker:
        return sync_blocker
    mirror_blocker, attestations = _mirror_bootstrap_result(
        root=root,
        policy=policy,
        candidate_head=candidate_head,
        transitions=transitions,
        context=(bootstrap, attestation, effect, evidence_digest, policy_digest, permissions),
    )
    if mirror_blocker:
        return mirror_blocker
    mirror_result = sync_linked_ref_worktree(
        worktrees, policy.release_branch if mirror else "", candidate_head, release_old
    )
    mirror_blocker = _mirror_sync_blocker(policy, candidate_head, mirror_result)
    if mirror_blocker:
        return mirror_blocker
    return {
        "ok": True,
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
    bootstrap, attestation, effect, evidence_digest, policy_digest, permissions = context
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
    mirror_attestation, error = _execute_closeout_effect(
        root, mirror_effect, (release,), evidence_digest, policy_digest, permissions
    )
    if error:
        return (
            _accepted_block(
                policy,
                candidate_head,
                ["release_mirror_bootstrap_incomplete"],
                candidate_head=candidate_head,
                accepted_advanced=True,
                stderr=error,
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
    proof = executed_proof_record(root, candidate_head)
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


def _execute_closeout_effect(
    root,
    effect,
    transitions,
    evidence_digest,
    policy_digest,
    permissions,
):
    try:
        return execute_closeout_effect(
            root=root,
            effect=effect,
            transitions=transitions,
            evidence_digest=evidence_digest,
            gate_policy_digest=policy_digest,
            permissions=permissions,
        ), ""
    except ValueError as error:
        return None, str(error)


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
