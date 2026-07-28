"""Git effects for Work Lane landing and accepted-root closeout."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.accepted as accepted
import ethos.adapters.mutation.remediation.guidance as remediation
from ethos.adapters.mutation.attestation_projection import attestation_payload
from ethos.adapters.mutation.decision import evaluate_closeout_mutation
from ethos.adapters.mutation.decision import evaluate_mutation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.repo.dirty.change_provenance import dirty_provenance
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effects import GitEffectExecutionRequest
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_effects import git_effect_attestations
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.lifecycle.reducer import TransitionDecision
from ethos.contracts.lifecycle.reducer import TransitionRequest
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.repository.policy.gates import gate_policy_digest


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
        plan, commitment_digest, facts_digest = accepted.proof_attestation_bindings(
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
                commitment_digest=commitment_digest,
                facts_digest=facts_digest,
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
            attestation=attestation_payload(attestation, kind="effect"),
        )
    return {
        "ok": True,
        "state": "candidate_validated",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "attestation": attestation_payload(attestation, kind="effect"),
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
            **accepted.accepted_payload(policy, current_head),
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
            **accepted.accepted_payload(policy, current_head),
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
            **accepted.accepted_payload(policy, current_head),
            "ok": True,
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
    )


def _effect_issuer() -> str:
    return os.environ.get("ETHOS_ACTOR", "").strip() or "agent:local:process:ethos"


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
