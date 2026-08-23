"""Bounded retirement of one absorbed, unbound Work Lane ref."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.ref_intent import committed_ref_intent
from ethos.adapters.mutation.decision import admission_decision
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.commitment import observe_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import MutationSubject
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.verdict import Verdict


def retire_absorbed_ref(
    *,
    root: Path,
    branch: str,
    expect_head: str,
    accepted_head: str,
    authorize: bool,
    confirm_irreversible: bool,
    apply: bool,
) -> dict[str, object]:
    """Plan or execute one exact absorbed ancestor ref retirement."""
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    status = workspace_status(repo)
    branch = branch.strip()
    expect_head = expect_head.strip()
    accepted_head = accepted_head.strip()
    current_ref = ref_head(repo, branch, expected="0" * 40) if branch else ""
    current_accepted = ref_head(repo, policy.accepted_branch, expected="0" * 40)
    lease_state = observe_lease(state_database(repo), branch).state if branch else "missing"
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    linked = any(str(item.get("branch") or "") == branch for item in worktrees)
    desired = "0" * len(expect_head)
    recovery_intent = (
        committed_ref_intent(
            root=repo,
            operation="lane.retire",
            desired=desired,
            ref_name=f"refs/heads/{branch}",
        )
        if branch and expect_head
        else {}
    )
    recovering = (
        current_ref == desired
        and bool(recovery_intent.get("present"))
        and not recovery_intent.get("gap")
        and recovery_intent.get("old_value") == expect_head
    )
    gaps = [
        gap
        for failed, gap in (
            (policy.role_for_branch(branch) != ROLE_WORK_LANE, "absorbed_ref_role_invalid"),
            (not branch, "branch_required"),
            (not expect_head, "expect_head_required"),
            (not accepted_head, "accepted_head_required"),
            (current_ref == desired and not recovering, "absorbed_ref_missing"),
            (
                expect_head and current_ref not in {expect_head, desired},
                "absorbed_ref_head_mismatch",
            ),
            (accepted_head and current_accepted != accepted_head, "accepted_head_mismatch"),
            (linked, "absorbed_ref_worktree_linked"),
            (lease_state != "missing", f"absorbed_ref_lease_{lease_state}"),
            (
                bool(expect_head and accepted_head)
                and not is_ancestor(repo, expect_head, accepted_head),
                "absorbed_ref_not_accepted_ancestor",
            ),
            (apply and not authorize, "authorization_required"),
            (apply and not confirm_irreversible, "irreversible_confirmation_required"),
        )
        if failed
    ]
    required_gaps = list(dict.fromkeys(gaps))
    verdict: Verdict = "pass" if not required_gaps else "block"
    effect = (
        GitEffect(
            updates={
                f"refs/heads/{branch}": GitRefUpdate(
                    expected=expect_head,
                    desired=desired,
                )
            },
            assertions={f"refs/heads/{policy.accepted_branch}": accepted_head},
        )
        if expect_head and accepted_head
        else None
    )
    mutation = _mutation(
        repo=repo,
        branch=branch,
        expect_head=expect_head,
        accepted_head=accepted_head,
        authorize=authorize,
        confirm_irreversible=confirm_irreversible,
        apply=apply,
        verdict=verdict,
        required_gaps=required_gaps,
    )
    report: dict[str, object] = {
        "verdict": verdict,
        "state": (
            "blocked"
            if verdict != "pass"
            else "ready_to_retire_absorbed_ref"
            if not apply
            else "planned"
        ),
        "branch": branch,
        "head": expect_head,
        "accepted_head": accepted_head,
        "mutation": mutation,
        "required_gaps": required_gaps,
    }

    def block_effect(current: dict[str, object], error: OSError | ValueError) -> dict[str, object]:
        return _block_effect_report(
            current,
            repo=repo,
            branch=branch,
            expect_head=expect_head,
            accepted_head=accepted_head,
            authorize=authorize,
            confirm_irreversible=confirm_irreversible,
            apply=apply,
            error=error,
        )

    if verdict != "pass":
        return report
    assert effect is not None
    try:
        plan = _admitted_retirement_plan(
            repo,
            effect,
            branch=branch,
            expect_head=expect_head,
            accepted_branch=policy.accepted_branch,
            accepted_head=accepted_head,
            recovering=recovering,
            recovery_intent=recovery_intent,
        )
    except (OSError, ValueError) as error:
        return block_effect(report, error)
    transition = {
        "state": "git_effect_admitted",
        "effect": plan.effect,
        "plan_digest": plan.digest,
    }
    admitted_report = report | {"transition": transition}
    if not apply:
        return admitted_report
    drift = (
        _effect_drift_gaps(
            repo,
            branch=branch,
            expect_head=expect_head,
            accepted_branch=policy.accepted_branch,
            accepted_head=accepted_head,
        )
        if not recovering
        else []
    )
    if drift:
        return admitted_report | {
            "verdict": "block",
            "state": "blocked",
            "required_gaps": drift,
        }
    try:
        attestation = execute_git_effect(
            repo,
            plan,
            issuer=os.environ.get("ETHOS_ACTOR", "").strip(),
        )
    except (OSError, ValueError) as error:
        return block_effect(admitted_report, error)
    return _project_retirement_postcondition(
        admitted_report
        | {"transition": transition | {"attestation": attestation.model_dump(mode="json")}},
        _retirement_observation(repo, branch, expect_head, accepted_head),
    )


def _admitted_retirement_plan(
    repo: Path,
    effect: GitEffect,
    *,
    branch: str,
    expect_head: str,
    accepted_branch: str,
    accepted_head: str,
    recovering: bool,
    recovery_intent: dict[str, object],
) -> TransitionPlan:
    commitment = load_repository_commitment(repo)
    prestate = observe_repository_commitment(repo, tree_ref=expect_head)
    if prestate.state == "valid":
        prestate_policy: dict[str, str] = {}
    elif prestate.state == "missing":
        prestate_policy = {"repository_prestate": "absent"}
    else:
        raise ValueError(prestate.gap)
    policy = {
        "operation": "lane.retire",
        "retirement_kind": "absorbed-ref",
        "branch": branch,
        "accepted_branch": accepted_branch,
        "accepted_head": accepted_head,
        "holder_ref": os.environ.get("ETHOS_ACTOR", "").strip(),
        **prestate_policy,
    }
    values = {
        "absorbed_ref": branch,
        "absorbed_head": expect_head,
        "accepted_head": accepted_head,
        "lease_state": "missing",
    }
    plan = compile_observed_git_effect(
        repo,
        commitment,
        effect,
        head=current_tracked_head(repo),
        prior_attestations={},
        policy=policy,
        values=values,
    )
    if recovering and plan.digest != recovery_intent.get("plan_digest"):
        plan = compile_observed_git_effect(
            repo,
            commitment,
            effect,
            head=current_tracked_head(repo),
            prior_attestations={},
            policy=policy | {"holder_ref": ""},
            values=values,
        )
        _require_recovery_plan(plan.digest, recovery_intent)
    admit_git_effect(repo, plan)
    return plan


def _block_effect_report(
    report: dict[str, object],
    *,
    repo: Path,
    branch: str,
    expect_head: str,
    accepted_head: str,
    authorize: bool,
    confirm_irreversible: bool,
    apply: bool,
    error: OSError | ValueError,
) -> dict[str, object]:
    """Return a blocked effect projection without mutating the admitted report."""
    gaps = [str(error)]
    return report | {
        "verdict": "block",
        "state": "blocked",
        "required_gaps": gaps,
        "mutation": _mutation(
            repo=repo,
            branch=branch,
            expect_head=expect_head,
            accepted_head=accepted_head,
            authorize=authorize,
            confirm_irreversible=confirm_irreversible,
            apply=apply,
            verdict="block",
            required_gaps=gaps,
        ),
    }


def _project_retirement_postcondition(
    report: dict[str, object], observed: dict[str, object]
) -> dict[str, object]:
    """Return the exact postcondition projection without mutating prior state."""
    if any(
        observed[key] != expected
        for key, expected in (
            ("ref_state", "absent"),
            ("worktree_binding", "absent"),
            ("lease_state", "missing"),
        )
    ):
        return report | {
            "verdict": "block",
            "state": "blocked",
            "required_gaps": ["absorbed_ref_postcondition_failed"],
        }
    return report | {"state": "retired_absorbed_ref", "retired": observed}


def _require_recovery_plan(digest: str, intent: dict[str, object]) -> None:
    if digest != intent.get("plan_digest"):
        message = "git_effect_recovery_unproven"
        raise ValueError(message)


def _mutation(
    *,
    repo: Path,
    branch: str,
    expect_head: str,
    accepted_head: str,
    authorize: bool,
    confirm_irreversible: bool,
    apply: bool,
    verdict: Verdict,
    required_gaps: list[str],
) -> dict[str, object]:
    expected_state = {
        "root": repo.as_posix(),
        "branch": branch,
        "expect_head": expect_head,
        "accepted_head": accepted_head,
        "authorize": authorize,
        "confirm_irreversible": confirm_irreversible,
    }
    decision = admission_decision(
        subject=MutationSubject(
            action="lane.retire.absorbed-ref",
            resource=f"refs/heads/{branch}",
            expected_state=expected_state,
        ),
        verdict=verdict,
        basis=DecisionBasis(
            enforcement_boundary="git_ref_compare_and_swap",
            identity_basis="accepted_head_ancestor_and_no_lease",
            state_bindings=tuple(expected_state),
            evidence_boundary="current_unbound_ref_observation",
            verifier_provenance="current_runner",
            time_basis="evaluation_time",
        ),
        policy_ref="commitment:lane-retire-absorbed-ref",
        required_gaps=tuple(str(item) for item in required_gaps),
        why=("exact_absorbed_ancestor_ready",) if verdict == "pass" else (),
    )
    return mutation_envelope(
        command="lane-retire-absorbed-ref",
        apply=apply,
        authorized=authorize and confirm_irreversible,
        expect_head=expect_head,
        decision=decision,
    )


def _retirement_observation(
    repo: Path,
    branch: str,
    head: str,
    accepted_head: str,
) -> dict[str, object]:
    status = workspace_status(repo)
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    return {
        "branch": branch,
        "head": head,
        "accepted_head": accepted_head,
        "ref_state": "absent" if not ref_head(repo, branch) else "present",
        "worktree_binding": (
            "linked"
            if any(str(item.get("branch") or "") == branch for item in worktrees)
            else "absent"
        ),
        "lease_state": observe_lease(state_database(repo), branch).state,
    }


def _effect_drift_gaps(
    repo: Path,
    *,
    branch: str,
    expect_head: str,
    accepted_branch: str,
    accepted_head: str,
) -> list[str]:
    """Re-observe every destructive precondition immediately before the ref CAS."""
    status = workspace_status(repo)
    worktrees = cast("list[dict[str, object]]", status["worktrees"])
    return [
        gap
        for failed, gap in (
            (ref_head(repo, branch) != expect_head, "absorbed_ref_head_drift"),
            (ref_head(repo, accepted_branch) != accepted_head, "accepted_head_drift"),
            (
                any(str(item.get("branch") or "") == branch for item in worktrees),
                "absorbed_ref_worktree_appeared",
            ),
            (
                observe_lease(state_database(repo), branch).state != "missing",
                "absorbed_ref_lease_appeared",
            ),
            (not is_ancestor(repo, expect_head, accepted_head), "absorbed_ref_ancestry_drift"),
        )
        if failed
    ]
