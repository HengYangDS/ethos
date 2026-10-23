"""Git effects for Work Lane landing and accepted-root closeout."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.remediation.guidance as remediation
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.proof_admission import predecessor_policy_gaps
from ethos.adapters.mutation.proof_admission import proof_attestation
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.openspec.commitment import admissible_openspec_commitments
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import validated_plan_attestation
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.status.bindings import has_changed_paths
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import integration_coordinates
from ethos.adapters.repo.worktree_effects import sync_worktree
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.proof.plan import proof_acceptance_purpose
from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from ethos.contracts.admission import AdmissionDecision
    from ethos.contracts.semantic import Attestation


def apply_land_to_candidate(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
    admitted_decision: AdmissionDecision | None = None,
    identity_transition: bool = False,
    candidate_head: str | None = None,
) -> dict[str, object]:
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    decision = admitted_decision or evaluate_mutation(
        command="land",
        apply=True,
        authorized=authorized,
        expect_head=expect_head,
        root=root,
        current_head=current_head,
    )
    if decision.verdict != "pass":
        return _blocked(
            load_branch_role_policy(root),
            current_head,
            list(decision.required_gaps),
            remediation=remediation.remediation_for_gaps(decision.required_gaps),
        )
    try:
        blocked, transition = _candidate_plan(
            root,
            identity_transition=identity_transition,
            expected_candidate_head=candidate_head,
            admitted_decision=decision,
        )
    except (TypeError, ValueError) as error:
        gap = _candidate_admission_gap(error)
        return _blocked(
            load_branch_role_policy(root),
            current_head,
            [gap],
            **({"stderr": str(error)} if gap != str(error) else {}),
        )
    if blocked:
        return blocked
    policy, _base_report, candidate_path, candidate_head, plan, attestation = transition
    failure: tuple[str, str] | None = None
    observed_candidate_head = ""
    cas_attempts = 0
    extra: dict[str, object] = {}
    if plan is not None and attestation is None:
        try:
            attestation, failure, observed_candidate_head, cas_attempts = _candidate_cas(
                root=root,
                policy=policy,
                plan=plan,
                candidate_head=candidate_head,
            )
        except ProcessExecutionError as error:
            failure = (str(error), str(error))
            unknown = error.observation.get("outcome") != "unchanged"
            extra.update(
                process_failure=error.evidence(),
                verdict="unknown" if unknown else "block",
                state="partial_transition" if unknown else "blocked",
            )
        except (TypeError, ValueError) as error:
            failure = (_candidate_admission_gap(error), str(error))
    if failure is not None or (cas_attempts and attestation is None):
        gap, stderr = failure or ("candidate_update_failed", "candidate attestation missing")
        extra["stderr"] = stderr
        if gap.startswith("candidate_cas_"):
            extra["candidate_head"] = observed_candidate_head
            extra["cas_attempts"] = cas_attempts
        return _blocked(
            policy,
            current_head,
            [gap],
            path=candidate_path.as_posix(),
            remediation=remediation.remediation_for_gaps([gap]),
            **extra,
        )
    try:
        worktree_attestation = sync_worktree(
            root,
            candidate_path,
            branch=policy.candidate_branch,
            previous=candidate_head,
            head=current_head,
        )
    except ValueError as error:
        return _blocked(
            policy,
            current_head,
            ["candidate_worktree_sync_failed"],
            path=candidate_path.as_posix(),
            stderr=str(error),
            attestation=attestation.model_dump(mode="json") if attestation is not None else {},
        )
    return {
        "verdict": "pass",
        "state": "candidate_validated" if attestation is not None else "candidate_current",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "attestation": attestation.model_dump(mode="json") if attestation is not None else {},
        "worktree_attestation": worktree_attestation.model_dump(mode="json"),
        "cas_attempts": cas_attempts,
        "required_gaps": [],
    }


def candidate_transition_readiness(
    *,
    root: Path,
    status=None,
    identity_transition: bool = False,
    candidate_head: str | None = None,
    admitted_decision: AdmissionDecision | None = None,
) -> dict[str, object]:
    """Compile and admit the exact candidate CAS without performing its effect."""
    try:
        blocked, transition = _candidate_plan(
            root,
            status=status,
            identity_transition=identity_transition,
            expected_candidate_head=candidate_head,
            admitted_decision=admitted_decision,
        )
    except (TypeError, ValueError) as error:
        policy = load_branch_role_policy(root)
        current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
        gap = _candidate_admission_gap(error)
        return _blocked(
            policy,
            current_head,
            [gap],
            **({"stderr": str(error)} if gap != str(error) else {}),
        )
    if blocked:
        return blocked
    policy, base_report, candidate_path, _candidate_head, plan, _attestation = transition
    if plan is None:
        return {
            **base_report,
            "state": "candidate_current",
            "effect": {},
            "plan_digest": "",
            "cas_attempts": 0,
        }
    try:
        admit_git_effect(root, plan)
    except (TypeError, ValueError) as error:
        gap = _candidate_admission_gap(error)
        return _blocked(
            policy,
            str(base_report["head"]),
            [gap],
            path=candidate_path.as_posix(),
            **({"stderr": str(error)} if gap != str(error) else {}),
        )
    return {
        **base_report,
        "state": (
            "candidate_materialization_pending"
            if base_report["state"] == "candidate_materialization_pending"
            else "candidate_transition_admitted"
        ),
        "effect": plan.effect,
        "plan_digest": plan.digest,
        "transition_plan": plan.model_dump(mode="json"),
        "cas_attempts": 0,
    }


def _candidate_plan(
    root: Path,
    *,
    status=None,
    identity_transition: bool = False,
    expected_candidate_head: str | None = None,
    admitted_decision: AdmissionDecision | None = None,
):
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    base_report = candidate_base_report(root=root, status=status)
    if (
        base_report.get("required_gaps") == ["candidate_worktree_dirty"]
        and admitted_decision is not None
        and admitted_decision.verdict == "pass"
        and (previous := admitted_decision.subject.expected_state.get("candidate_preimage"))
    ):
        path = Path(str(base_report["path"]))
        if not worktree_sync_gap(
            root, (path,), policy.candidate_branch, current_head, str(previous), current_head
        ):
            base_report = {
                **base_report,
                "verdict": "pass",
                "state": "candidate_materialization_pending",
                "candidate_head": str(previous),
                "required_gaps": [],
            }
    if report_verdict(base_report) != "pass":
        return base_report, None
    candidate_path = Path(str(base_report["path"]))
    candidate_head = str(base_report["candidate_head"])
    if identity_transition:
        if expected_candidate_head is None:
            message = "repository_identity_transition_target_head_required"
            raise ValueError(message)
        if candidate_head not in {expected_candidate_head, current_head}:
            message = "repository_identity_transition_target_head_changed"
            raise ValueError(message)
        candidate_head = expected_candidate_head
    purpose = proof_acceptance_purpose(
        admitted_decision.subject.expected_state if admitted_decision is not None else {}
    )
    proof, proof_required = proof_attestation(
        root,
        current_head,
        store=proof_artifact_root(root),
        acceptance_purpose=purpose,
    )
    if proof is None:
        return (
            _blocked(
                policy,
                current_head,
                proof_required,
                path=candidate_path.as_posix(),
            ),
            None,
        )
    if candidate_head != current_head and (
        gaps := predecessor_policy_gaps(root, current_head, proof)
    ):
        return _blocked(policy, current_head, gaps, path=candidate_path.as_posix()), None
    branch = current_branch(root)
    lease = leases_by_branch(root).get(branch, {})
    # The authority is the encoding of the exact source that the admitted proof carries.
    authority = next(
        (
            commitment
            for commitment in admissible_openspec_commitments(
                root, change_id=None, tree_ref=current_head
            )
            if commitment.digest() == proof.commitment_digest
        ),
        None,
    )
    if authority is None:
        message = "proof_attestation_authority_binding_mismatch"
        raise ValueError(message)
    recovering = base_report.get("state") == "candidate_materialization_pending"
    plan, attestation = (
        _candidate_materialization_plan(
            root,
            policy=policy,
            branch=branch,
            head=current_head,
            previous=candidate_head,
            decision=admitted_decision,
            commitment_digest=proof.commitment_digest,
        )
        if recovering
        else (None, None)
    )
    plan = plan or (
        compile_observed_git_effect(
            root,
            authority,
            policy.candidate_effect(
                branch=branch,
                current_head=current_head,
                candidate_head=candidate_head,
            ),
            head=current_head,
            prior_attestations={"proof": proof.model_dump(mode="json")},
            policy={
                "operation": "candidate.integrate",
                "candidate_branch": policy.candidate_branch,
                "acceptance_purpose": purpose,
            },
            values={
                "operation": "candidate.integrate",
                "lease_generation": lease_generation(lease),
            },
            identity_transition=identity_transition,
        )
        if candidate_head != current_head and not recovering
        else None
    )
    return None, (policy, base_report, candidate_path, candidate_head, plan, attestation)


def _candidate_materialization_plan(
    root: Path,
    *,
    policy: BranchRolePolicy,
    branch: str,
    head: str,
    previous: str,
    decision: AdmissionDecision | None,
    commitment_digest: str | None,
) -> tuple[TransitionPlan, Attestation]:
    """Consume exact original effect evidence and re-admit its current materialization."""
    digest = decision.subject.expected_state.get("candidate_recovery_plan") if decision else None
    issuer = os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"
    original = validated_plan_attestation(root, str(digest), issuer=issuer) if digest else None
    if original is None:
        message = "candidate_recovery_plan_unproven"
        raise ValueError(message)
    plan, attestation = original
    if (
        plan.policy.get("transition") != "candidate.integrate"
        or plan.inputs.commitment != commitment_digest
        or git_effect_from_plan(plan)
        != policy.candidate_effect(
            branch=branch,
            current_head=head,
            candidate_head=previous,
        )
    ):
        message = "candidate_recovery_plan_binding_mismatch"
        raise ValueError(message)
    admit_git_effect(root, plan)
    return plan, attestation


def _candidate_cas(
    *,
    root: Path,
    policy: BranchRolePolicy,
    plan: TransitionPlan,
    candidate_head: str,
) -> tuple[Attestation | None, tuple[str, str] | None, str, int]:
    issuer = os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"
    try:
        return execute_git_effect(root, plan, issuer=issuer), None, "", 1
    except ProcessExecutionError:
        raise
    except ValueError as error:
        if str(error) not in {"git_effect_cas_mismatch", "git_effect_cas_rejected"}:
            raise
        observed = run_git(root, "rev-parse", policy.candidate_branch, check=False).stdout.strip()
        if observed != candidate_head:
            return None, ("candidate_cas_stale", str(error)), observed, 1
        try:
            return execute_git_effect(root, plan, issuer=issuer), None, observed, 2
        except ProcessExecutionError:
            raise
        except ValueError as retry_error:
            if str(retry_error) in {"git_effect_cas_mismatch", "git_effect_cas_rejected"}:
                current = run_git(
                    root, "rev-parse", policy.candidate_branch, check=False
                ).stdout.strip()
                return None, ("candidate_cas_retry_exhausted", str(retry_error)), current, 2
            raise


def _candidate_admission_gap(error: Exception) -> str:
    gap = str(error)
    return (
        gap
        if gap
        in {
            "git_effect_permission_denied",
            "git_effect_lease_generation_stale",
            "git_effect_plan_prestate_mismatch",
            "git_effect_plan_prestate_stale",
            "git_effect_repository_identity_mismatch",
            "lease_actor_mismatch",
            "proof_attestation_authority_binding_mismatch",
        }
        else "candidate_update_failed"
    )


def _blocked(policy, head, gaps, *, state="blocked", verdict="block", **extra):
    return dict(
        verdict=verdict,
        state=state,
        branch=policy.candidate_branch,
        head=head,
        required_gaps=gaps,
        **extra,
    )


def candidate_base_report(*, root: Path, status=None) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    status = status if status is not None else integration_coordinates(root, policy=policy)
    candidate = cast("dict[str, object]", status["candidate"])

    def fail(gaps: list[str], **extra: object) -> dict[str, object]:
        return _blocked(policy, current_head, gaps, **extra)

    if not candidate["exists"]:
        return fail(["candidate_branch_missing"])
    if not candidate["worktree_exists"]:
        return fail(["candidate_worktree_missing"])
    candidate_path = Path(str(candidate["worktree_path"]))
    if has_changed_paths(candidate_path):
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
        "verdict": "pass",
        "state": "candidate_base_current",
        "branch": policy.candidate_branch,
        "head": current_head,
        "candidate_head": candidate_head,
        "path": candidate_path.as_posix(),
        "required_gaps": [],
    }
