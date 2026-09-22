"""Current-fact mutation admission and public decision projection."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import recover_plan
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.repo.status.workspace import integration_coordinates
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import git_effect_from_plan
from ethos.normalization.coercion import integer
from ethos.normalization.coercion import string_mapping

if TYPE_CHECKING:
    from ethos.contracts.branch.roles import BranchRolePolicy
    from ethos.contracts.semantic import Attestation
    from ethos.contracts.verdict import Verdict


def admission_decision(
    *,
    subject: MutationSubject,
    verdict: Verdict,
    basis: DecisionBasis,
    policy_ref: str,
    required_gaps: tuple[str, ...] = (),
    why: tuple[str, ...] = (),
    next_action: str = "",
) -> AdmissionDecision:
    """Return the sole exact-request mutation decision contract."""
    return AdmissionDecision(
        verdict=verdict,
        subject=subject,
        policy_refs=(policy_ref,),
        evidence_refs=(f"evidence:{basis.evidence_boundary}",),
        basis=basis,
        why=why or required_gaps or ("request_admitted",),
        next_action=next_action,
        required_gaps=required_gaps,
    )


def _local_process_decision(
    *,
    action: str,
    resource: str,
    expected_state: dict[str, object],
    policy_ref: str,
    required_gaps: tuple[str, ...] = (),
    why: tuple[str, ...] = (),
) -> AdmissionDecision:
    return admission_decision(
        subject=MutationSubject(
            action=action,
            resource=resource,
            expected_state=expected_state,
        ),
        verdict="block" if required_gaps else "pass",
        basis=DecisionBasis(
            enforcement_boundary="local_process_guard",
            identity_basis="not_evaluated",
            state_bindings=tuple(expected_state),
            evidence_boundary="current_local_observation",
            verifier_provenance="current_runner",
            time_basis="evaluation_time",
        ),
        policy_ref=policy_ref,
        required_gaps=required_gaps,
        why=why,
    )


def _closeout_candidate_gaps(
    root: Path,
    candidate: dict[str, object],
    current_head: str,
    *,
    require_proof: bool,
) -> list[str]:
    """Return candidate facts that block accepted-root promotion."""
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    candidate_path = Path(str(candidate["worktree_path"]))
    if has_changed_paths(candidate_path):
        return ["candidate_worktree_dirty"]
    candidate_head = str(candidate.get("head") or "")
    if not is_ancestor(root, current_head, candidate_head):
        return ["candidate_diverged_from_accepted"]
    if not require_proof:
        return []
    _proof, proof_gaps = proof_for_repository_transition(candidate_path, candidate_head)
    return proof_gaps


def request_gaps(
    *, apply: bool, authorized: bool, expect_head: str | None, current_head: str
) -> list[str]:
    """Return the shared exact-HEAD mutation request gaps."""
    gaps = []
    if apply and not authorized:
        gaps.append("authorization_required")
    if apply and expect_head is None:
        gaps.append("expect_head_required")
    if expect_head is not None and expect_head != current_head:
        gaps.append("expect_head_mismatch")
    return gaps


def evaluate_mutation(
    *,
    command: str,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    root: Path,
    current_head: str,
    status: dict[str, object] | None = None,
) -> AdmissionDecision:
    """Admit land or publish from current facts."""
    action = "candidate.integrate" if command == "land" else "remote.publish"
    base_state: dict[str, object] = {
        "root": root.resolve().as_posix(),
        "head": current_head,
        "apply": apply,
        "confirmation_present": authorized,
        "expect_head": expect_head or "",
    }
    if not apply and command != "land":
        return _local_process_decision(
            action=action,
            resource=root.resolve().as_posix(),
            expected_state=base_state,
            policy_ref=f"commitment:{command}-admission",
            why=("readiness_only",),
        )
    status = status if status is not None else workspace_status(root)
    closeout = cast("dict[str, object]", status.get("closeout_support", {}))
    gaps = request_gaps(
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
        current_head=current_head,
    )
    role = str(status["role"])
    gaps.extend(
        ["protected_root_mutation"]
        if role != ROLE_WORK_LANE
        else ["work_lane_dirty"]
        if status["dirty"]
        else []
    )
    closeout_gaps = [str(gap) for gap in cast("list[object]", closeout.get("required_gaps", []))]
    if command == "land" and not gaps and closeout_gaps == ["candidate_worktree_dirty"]:
        try:
            materialization = _candidate_materialization(root, status, current_head)
        except ValueError as error:
            gaps.append(str(error))
        else:
            if materialization:
                base_state.update(materialization)
                closeout_gaps.remove("candidate_worktree_dirty")
    gaps.extend(closeout_gaps)
    if apply:
        gaps.extend(proof_gaps(root, current_head))
    required_gaps = tuple(dict.fromkeys(gaps))
    expected_state = {**base_state, "role": role, "dirty": bool(status["dirty"])}
    resource = root.resolve().as_posix()
    if command == "land":
        candidate = string_mapping(status.get("candidate"))
        resource = f"refs/heads/{load_branch_role_policy(root).candidate_branch}"
        expected_state.update(
            source_ref=f"refs/heads/{status.get('branch', '')}",
            source_head=current_head,
            target_ref=resource,
            target_head=str(candidate.get("head") or ""),
            holder_ref=str(closeout.get("holder_ref") or ""),
            lease_generation=integer(closeout.get("lease_generation")),
            lease_expires_at=str(closeout.get("lease_expires_at") or ""),
        )
    return _local_process_decision(
        action=action,
        resource=resource,
        expected_state=expected_state,
        policy_ref=f"commitment:{command}-admission",
        required_gaps=required_gaps,
    )


def _candidate_materialization(
    root: Path, status: dict[str, object], head: str
) -> dict[str, object]:
    """Admit only the unchanged preimage of a completed, currently authorized ref effect."""
    candidate = cast("dict[str, object]", status.get("candidate", {}))
    if candidate.get("head") != head or not status.get("branch"):
        return {}
    policy = load_branch_role_policy(root)
    ref = f"refs/heads/{policy.candidate_branch}"
    plan = recover_plan(
        root,
        operation="candidate.integrate",
        desired=head,
        ref_name=ref,
        assertions={f"refs/heads/{status['branch']}": head},
    )
    if plan is None:
        return {}
    admit_git_effect(root, plan)
    previous = git_effect_from_plan(plan).updates[ref].expected
    path = Path(str(candidate["worktree_path"]))
    if worktree_sync_gap(root, (path,), policy.candidate_branch, head, previous, head):
        return {}
    return {"candidate_preimage": previous, "candidate_recovery_plan": plan.digest}


def evaluate_closeout_mutation(
    *,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    root: Path,
    current_head: str,
    completed_effect: Attestation | None = None,
) -> AdmissionDecision:
    """Admit accepted-root closeout from current candidate facts."""
    policy = load_branch_role_policy(root)
    status = integration_coordinates(root, policy=policy)
    dirty = has_changed_paths(root)
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    previous = _closeout_preimage(completed_effect, policy, current_head, candidate_head)
    recoverable = previous is not None and not worktree_sync_gap(
        root, (root,), policy.accepted_branch, current_head, previous, current_head
    )
    gaps = request_gaps(
        apply=apply,
        authorized=authorized,
        expect_head=expect_head,
        current_head=previous if previous and expect_head == previous else current_head,
    )
    role = str(status["role"])
    gaps.extend(
        ["accepted_root_required"]
        if role != ROLE_ACCEPTED_ROOT
        else ["accepted_root_dirty"]
        if dirty and not recoverable
        else []
    )
    gaps.extend(
        (
            *_closeout_candidate_gaps(
                root,
                candidate,
                current_head,
                require_proof=(candidate_head != current_head or completed_effect is not None)
                and not gaps,
            ),
        )
    )
    required_gaps = tuple(dict.fromkeys(gaps))
    expected_state = {
        "root": root.resolve().as_posix(),
        "head": current_head,
        "candidate_head": candidate_head,
        "role": role,
        "dirty": dirty,
        "apply": apply,
        "confirmation_present": authorized,
        "expect_head": expect_head or "",
        "recovery_preimage": previous or "",
    }
    return _local_process_decision(
        action="accepted.advance",
        resource=root.resolve().as_posix(),
        expected_state=expected_state,
        policy_ref="commitment:land-admission",
        required_gaps=required_gaps,
    )


def _closeout_preimage(
    completed: Attestation | None, policy: BranchRolePolicy, head: str, candidate_head: str
) -> str | None:
    """Read the exact scope of an observed effect, not a reusable authorization."""
    if completed is None or head != candidate_head:
        return None
    plan = plan_from_attestation(completed)
    effect = git_effect_from_plan(plan)
    update = effect.updates.get(f"refs/heads/{policy.accepted_branch}")
    if (
        plan.policy.get("transition") != "candidate.accept"
        or update is None
        or update.desired != head
        or effect.assertions.get(f"refs/heads/{policy.candidate_branch}") != head
    ):
        return None
    return update.expected


def mutation_envelope(
    *,
    command: str,
    apply: bool,
    authorized: bool,
    expect_head: str | None,
    decision: AdmissionDecision,
) -> dict[str, object]:
    """Project one exact AdmissionDecision with its invocation intent."""
    return {
        "request": {
            "command": command,
            "apply": apply,
            "expect_head": expect_head,
            "confirmation_present": authorized,
        },
        "decision": decision.to_payload(),
    }
