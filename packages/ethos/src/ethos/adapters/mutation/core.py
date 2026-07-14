from __future__ import annotations

from pathlib import Path
from typing import cast

import ethos.adapters.mutation.remediation.core as remediation
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.mutation.carriers import openspec_carrier_gaps
from ethos.adapters.mutation.closeout.core import promote_candidate_to_accepted
from ethos.adapters.mutation.decision import MutationEvaluation
from ethos.adapters.mutation.decision import MutationRequest
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.proof import carry_executed_proof_record
from ethos.adapters.mutation.proof import discard_executed_proof
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.mutation.proof import gate_policy_gaps
from ethos.adapters.mutation.proof import promotion_completeness_gaps
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_CANDIDATE
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.lifecycle.core import CLOSEOUT_MUTATION
from ethos_core.contracts.lifecycle.core import WORK_LANE_MUTATION
from ethos_core.contracts.lifecycle.core import MutationFacts
from ethos_core.contracts.lifecycle.core import reduce_mutation

__all__ = ["MutationEvaluation", "MutationRequest", "mutation_envelope"]


def proof_gaps(root, current_head):
    """Blocking gaps when no executed proof is bound to the exact current HEAD.

    Binds the mutation to executed proof: a land/publish cannot proceed unless
    `ethos prove --execute` recorded a proof at this HEAD. This is the runtime
    precondition that turns "only proven evidence may satisfy land/publish" from
    prose into an enforced barrier (the proof and executability invariants).
    """
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
        "next_action": ""
        if not gaps
        else f"ethos prove --execute --expect-head {current_head} --json",
    }


def _candidate_gaps_for_proof(candidate_path, candidate_head):
    """Compatibility seam for closeout proof admission."""
    return proof_gaps(candidate_path, candidate_head)


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
    return openspec_carrier_gaps(candidate_path, ROLE_CANDIDATE) + (
        _candidate_gaps_for_proof(candidate_path, candidate_head) if require_proof else []
    )


def evaluate_mutation(request, *, root, current_head):
    if not request.apply and request.command != "land":
        return reduce_mutation(
            request,
            current_head=current_head,
            facts=MutationFacts(),
            transition=WORK_LANE_MUTATION,
        )
    closeout = cast(
        "dict[str, object]", (status := workspace_status(root)).get("closeout_support", {})
    )
    return reduce_mutation(
        request,
        current_head=current_head,
        facts=MutationFacts(
            role=str(status["role"]),
            dirty=bool(status["dirty"]),
            healthy_gaps=tuple(
                str(gap)
                for gap in (
                    *openspec_carrier_gaps(root, ROLE_WORK_LANE),
                    *cast("list[object]", closeout.get("required_gaps", [])),
                )
            ),
            evidence_gaps=tuple(proof_gaps(root, current_head)),
        ),
        transition=WORK_LANE_MUTATION,
    )


def evaluate_closeout_mutation(request, *, root, current_head):
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])
    return reduce_mutation(
        request,
        current_head=current_head,
        facts=MutationFacts(
            role=str(status["role"]),
            dirty=bool(status["dirty"]),
            healthy_gaps=tuple(openspec_carrier_gaps(root, ROLE_ACCEPTED_ROOT)),
            always_gaps=tuple(
                _closeout_candidate_gaps(
                    root,
                    candidate,
                    current_head,
                    require_proof=request.apply
                    and str(candidate.get("head") or "") != current_head,
                )
            ),
            current=str(candidate.get("head") or "") == current_head,
        ),
        transition=CLOSEOUT_MUTATION,
    )


def apply_land_to_candidate(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
    admitted_decision: MutationEvaluation | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()

    def fail(gaps: list[str], **extra: object) -> dict[str, object]:
        return _blocked(policy, current_head, gaps, **extra)

    decision = admitted_decision or evaluate_mutation(
        MutationRequest(command="land", apply=True, authorized=authorized, expect_head=expect_head),
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
    proof_carry = carry_executed_proof_record(
        source_root=root, target_root=candidate_path, head=current_head
    )
    if not proof_carry["ok"]:
        return fail(
            list(cast("list[str]", proof_carry.get("required_gaps", []))),
            path=candidate_path.as_posix(),
            proof_carry=proof_carry,
        )
    completed = run_git(
        candidate_path,
        "merge",
        "--ff-only",
        current_head,
        check=False,
    )
    if completed.returncode != 0:
        discard_executed_proof(candidate_path, current_head)
        return fail(
            ["candidate_update_failed"],
            path=candidate_path.as_posix(),
            remediation=remediation.remediation_for_gaps(["candidate_update_failed"]),
            stderr=completed.stderr.strip(),
        )
    return {
        "ok": True,
        "state": "candidate_validated",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "proof_carry": proof_carry,
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
    *, root: Path, authorized: bool, expect_head: str | None
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    decision = evaluate_closeout_mutation(
        MutationRequest(
            command="closeout", apply=True, authorized=authorized, expect_head=expect_head
        ),
        root=root,
        current_head=current_head,
    )
    if not decision.ok:
        return {
            **_accepted_payload(policy, current_head),
            "ok": False,
            "state": decision.state,
            "required_gaps": list(decision.gaps),
            "remediation": remediation.remediation_for_gaps(decision.gaps),
        }
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate["head"])
    policy = load_branch_role_policy(root, candidate_head)
    if decision.state == "current" and policy.release_mirror != RELEASE_MIRROR_ACCEPTED_FF:
        return {
            **_accepted_payload(policy, current_head),
            "ok": True,
            "state": "accepted_current",
            "candidate_head": candidate_head,
        }
    return promote_candidate_to_accepted(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
        candidate_path=Path(str(candidate["worktree_path"])),
        worktrees=cast("list[dict[str, object]]", status.get("worktrees", [])),
        run_git=run_git,
        is_ancestor_fn=is_ancestor,
        carry_proof=carry_executed_proof_record,
        discard_proof=discard_executed_proof,
    )


def _accepted_payload(policy, head):
    return {
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": head,
        "previous_head": head,
    }


def candidate_base_report(*, root: Path) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = run_git(root, "rev-parse", "HEAD").stdout.strip()
    status = workspace_status(root)
    candidate = cast("dict[str, object]", status["candidate"])

    def fail(gaps: list[str], **extra: object) -> dict[str, object]:
        return _blocked(policy, current_head, gaps, **extra)

    if not candidate["exists"]:
        return fail(["candidate_branch_missing"])
    if not candidate["worktree_exists"]:
        return fail(["candidate_worktree_missing"])
    candidate_path = Path(str(candidate["worktree_path"]))
    candidate_status = workspace_status(candidate_path)
    if candidate_status["dirty"]:
        return fail(
            ["candidate_worktree_dirty"],
            path=candidate_path.as_posix(),
        )
    candidate_head = str(candidate["head"])
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
