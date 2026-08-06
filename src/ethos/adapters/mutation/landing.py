"""Git effects for Work Lane landing and accepted-root closeout."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.accepted as accepted
import ethos.adapters.mutation.remediation.guidance as remediation
from ethos.adapters.mutation.decision import evaluate_closeout_mutation
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.dirty.change_provenance import dirty_provenance
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.repo.worktree_effects import sync_worktree
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from ethos.contracts.admission import AdmissionDecision
    from ethos.contracts.semantic import Attestation
    from ethos.contracts.semantic import Commitment


def apply_land_to_candidate(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
    admitted_decision: AdmissionDecision | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()

    def fail(gaps, **extra):
        return _blocked(policy, current_head, gaps, **extra)

    decision = admitted_decision or evaluate_mutation(
        command="land",
        apply=True,
        authorized=authorized,
        expect_head=expect_head,
        root=root,
        current_head=current_head,
    )
    if decision.verdict != "pass":
        return fail(
            list(decision.required_gaps),
            remediation=remediation.remediation_for_gaps(decision.required_gaps),
        )
    base_report = candidate_base_report(root=root)
    if report_verdict(base_report) != "pass":
        return base_report
    candidate_path = Path(str(base_report["path"]))
    candidate_head = str(base_report["candidate_head"])
    status = workspace_status(root, include_foreign_path_scope=False)
    branch = str(status["branch"])
    proof = proof_attestation(candidate_path, current_head)
    if proof is None:
        return fail(
            proof_gaps(candidate_path, current_head),
            path=candidate_path.as_posix(),
        )
    failure: tuple[str, str] | None = None
    attestation: Attestation | None = None
    observed_candidate_head = ""
    cas_attempts = 1
    try:
        lease = leases_by_branch(root).get(branch, {})
        authority = load_lease_bound_commitment(root, lease=lease)
        if proof.commitment_digest != authority.digest():
            failure = ("proof_attestation_authority_binding_mismatch", "")
        else:
            attestation, failure, observed_candidate_head, cas_attempts = _candidate_cas(
                root=root,
                authority=authority,
                policy=policy,
                refs=(branch, current_head, candidate_head),
                candidate_path=candidate_path,
                lease=lease,
                proof=proof,
            )
    except (TypeError, ValueError) as error:
        failure = ("candidate_update_failed", str(error))
    if failure is not None or attestation is None:
        gap, stderr = failure or ("candidate_update_failed", "candidate attestation missing")
        extra = {"stderr": stderr} if stderr else {}
        if gap.startswith("candidate_cas_"):
            extra["candidate_head"] = observed_candidate_head
            extra["cas_attempts"] = cas_attempts
        return fail(
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
        return fail(
            ["candidate_worktree_sync_failed"],
            path=candidate_path.as_posix(),
            stderr=str(error),
            attestation=attestation.model_dump(mode="json"),
        )
    return {
        "verdict": "pass",
        "state": "candidate_validated",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "attestation": attestation.model_dump(mode="json"),
        "worktree_attestation": worktree_attestation.model_dump(mode="json"),
        "cas_attempts": cas_attempts,
        "required_gaps": [],
    }


def _candidate_cas(
    *,
    root: Path,
    authority: Commitment,
    policy: BranchRolePolicy,
    refs: tuple[str, str, str],
    candidate_path: Path,
    lease: dict[str, object],
    proof: Attestation,
) -> tuple[Attestation | None, tuple[str, str] | None, str, int]:
    branch, current_head, candidate_head = refs
    effect = GitEffect(
        updates={
            f"refs/heads/{policy.candidate_branch}": GitRefUpdate(
                expected=candidate_head, desired=current_head
            )
        },
        assertions={f"refs/heads/{branch}": current_head},
    )
    plan = _candidate_transition_plan(
        root=root,
        authority=authority,
        effect=effect,
        head=current_head,
        lease=lease,
        prior_attestations={"proof": proof.model_dump(mode="json")},
        policy=policy,
    )
    issuer = os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"
    try:
        return execute_git_effect(root, plan, issuer=issuer), None, "", 1
    except ValueError as error:
        if str(error) not in {"git_effect_cas_mismatch", "git_effect_cas_rejected"}:
            raise
        observed = run_git(root, "rev-parse", policy.candidate_branch, check=False).stdout.strip()
        if observed != candidate_head:
            return None, ("candidate_cas_stale", str(error)), observed, 1
        current_proof = proof_attestation(candidate_path, current_head)
        if current_proof is None:
            return None, ("candidate_retry_proof_stale", str(error)), observed, 1
        retry = _candidate_transition_plan(
            root=root,
            authority=authority,
            effect=effect,
            head=current_head,
            lease=lease,
            prior_attestations={"proof": current_proof.model_dump(mode="json")},
            policy=policy,
        )
        try:
            return execute_git_effect(root, retry, issuer=issuer), None, observed, 2
        except ValueError as retry_error:
            if str(retry_error) in {"git_effect_cas_mismatch", "git_effect_cas_rejected"}:
                current = run_git(
                    root, "rev-parse", policy.candidate_branch, check=False
                ).stdout.strip()
                return None, ("candidate_cas_retry_exhausted", str(retry_error)), current, 2
            raise


def _candidate_transition_plan(
    *,
    root: Path,
    authority: Commitment,
    effect: GitEffect,
    head: str,
    lease: dict[str, object],
    prior_attestations: dict[str, object],
    policy: BranchRolePolicy,
) -> TransitionPlan:
    if not prior_attestations.get("proof"):
        message = "candidate_prior_proof_missing"
        raise ValueError(message)
    return compile_observed_git_effect(
        root,
        authority,
        effect,
        head=head,
        prior_attestations=prior_attestations,
        policy={
            "operation": "candidate.integrate",
            "candidate_branch": policy.candidate_branch,
        },
        values={
            "operation": "candidate.integrate",
            "lease_generation": lease_generation(lease),
        },
    )


def _blocked(policy, head, gaps, *, state="blocked", **extra):
    return dict(
        verdict="block",
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
    control_replacement_receipt: dict[str, object] | None = None,
) -> dict[str, object]:
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    try:
        workspace = committed_file_text(root, current_head, ".ethos/workspace.toml")
        policy = (
            _accepted_transition_policy(workspace)
            if workspace
            else _default_accepted_transition_policy(root, current_head)
        )
    except (TypeError, ValueError):
        return {
            "verdict": "block",
            "state": "blocked",
            "branch": "",
            "head": current_head,
            "required_gaps": ["accepted_policy_unavailable"],
        }
    decision = evaluate_closeout_mutation(
        apply=True,
        authorized=authorized,
        expect_head=expect_head,
        root=root,
        current_head=current_head,
    )
    if decision.verdict != "pass":
        return {
            **accepted.accepted_payload(policy, current_head),
            "state": "blocked",
            "required_gaps": list(decision.required_gaps),
            "remediation": remediation.remediation_for_gaps(decision.required_gaps),
        }
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])
    observed_candidate_head = str(candidate["head"])
    if candidate_head is not None and observed_candidate_head != candidate_head:
        gaps = ["candidate_head_changed_after_control_replacement_check"]
        return {
            **accepted.accepted_payload(policy, current_head),
            "candidate_head": observed_candidate_head,
            "verified_candidate_head": candidate_head,
            "required_gaps": gaps,
            "remediation": remediation.remediation_for_gaps(gaps),
        }
    candidate_head = candidate_head or observed_candidate_head
    if (
        candidate_head == current_head
        and policy.release_mirror != RELEASE_MIRROR_ACCEPTED_FF
        and not workspace_status(root)["dirty"]
    ):
        return {
            **accepted.accepted_payload(policy, current_head),
            "verdict": "pass",
            "state": "accepted_current",
            "candidate_head": candidate_head,
            "attestation": {},
        }
    return accepted.promote_candidate(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
        status=status,
        control_replacement_receipt=control_replacement_receipt,
    )


def _accepted_transition_policy(text: str) -> BranchRolePolicy:
    """Parse the exact incumbent branch-role contract without compatibility."""
    return strict_branch_role_policy_from_text(text)


def _default_accepted_transition_policy(root: Path, head: str) -> BranchRolePolicy:
    """Use defaults only when the accepted tree contains no workspace carrier."""
    present = run_git(
        root,
        "ls-tree",
        "--name-only",
        head,
        "--",
        ".ethos/workspace.toml",
        check=False,
    )
    if present.returncode or present.stdout.strip():
        message = "accepted transition policy is unreadable"
        raise ValueError(message)
    return BranchRolePolicy()


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
        "verdict": "pass",
        "state": "candidate_base_current",
        "branch": policy.candidate_branch,
        "head": current_head,
        "candidate_head": candidate_head,
        "path": candidate_path.as_posix(),
        "required_gaps": [],
    }
