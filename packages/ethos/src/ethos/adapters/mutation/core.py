from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.remediation.core as remediation
from ethos.adapters.admission.closeout_intent.core import CloseoutTransition
from ethos.adapters.admission.closeout_intent.core import clear_closeout_intent
from ethos.adapters.admission.closeout_intent.core import sweep_stale_closeout_intents
from ethos.adapters.admission.closeout_intent.core import write_closeout_intent
from ethos.adapters.mutation.carriers import openspec_carrier_gaps
from ethos.adapters.mutation.decision import MutationEvaluation
from ethos.adapters.mutation.decision import MutationRequest
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.proof import carry_executed_proof_record
from ethos.adapters.mutation.proof import discard_executed_proof
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.mutation.proof import gate_policy_gaps
from ethos.adapters.mutation.proof import promotion_completeness_gaps
from ethos.adapters.repo.status.core import workspace_status
from ethos.repository.policy.gates import gate_policy_digest
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_CANDIDATE
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import BranchRolePolicy
from ethos_core.contracts.branch.roles import load_branch_role_policy

__all__ = ["MutationEvaluation", "MutationRequest", "mutation_envelope"]


def proof_gaps(root: Path, current_head: str) -> list[str]:
    """Blocking gaps when no executed proof is bound to the exact current HEAD.

    Binds the mutation to executed proof: a land/publish cannot proceed unless
    `ethos prove --execute` recorded a proof at this HEAD. This is the runtime
    precondition that turns "only proven evidence may satisfy land/publish" from
    prose into an enforced barrier (the proof and executability invariants).
    """
    record = executed_proof_record(root, current_head)
    if record is None:
        return ["proof_not_proven"]
    # Completeness: a valid proof record must also cover the required land floor,
    # not merely be one passing trust-bearing run. A focused `prove --gate X` is a
    # valid record but not promotion-worthy — this closes "proven != required gates
    # passed" at the promotion gate (land/closeout/push consume proof_gaps).
    # Policy identity: the proof must be bound to the LIVE required-gate policy (canonical
    # commands, classifications, script content) and each covering run must have actually
    # run its gate — defeats a same-UID forgery that satisfies completeness with mislabeled
    # or /bin/true runs, or a proof recorded against a since-changed gate policy.
    return [
        *promotion_completeness_gaps(root, current_head),
        *gate_policy_gaps(root, current_head),
    ]


def proof_readiness_report(root: Path, current_head: str) -> dict[str, object]:
    """Describe whether the exact HEAD has valid executed proof evidence."""
    gaps = proof_gaps(root, current_head)
    return {
        "kind": "executed_proof_readiness",
        "head": current_head,
        "state": "proven" if not gaps else "missing",
        "blocking": bool(gaps),
        "required_gaps": gaps,
        "next_action": ""
        if not gaps
        else f"ethos prove --execute --expect-head {current_head} --json",
    }


def _candidate_gaps_for_proof(candidate_path: Path, candidate_head: str) -> list[str]:
    """Blocking gaps when closeout lacks proof for the head being promoted."""
    return proof_gaps(candidate_path, candidate_head)


def _closeout_candidate_gaps(
    root: Path,
    candidate: dict[str, object],
    current_head: str,
    *,
    require_proof: bool = True,
) -> list[str]:
    """Candidate-side closeout blockers, ordered by lifecycle before evidence."""
    if not candidate["exists"]:
        return ["candidate_branch_missing"]
    if not candidate["worktree_exists"]:
        return ["candidate_worktree_missing"]
    candidate_path = Path(str(candidate["worktree_path"]))
    if workspace_status(candidate_path)["dirty"]:
        return ["candidate_worktree_dirty"]
    candidate_head = str(candidate.get("head") or "")
    if not _is_ancestor(root, current_head, candidate_head):
        return ["candidate_diverged_from_accepted"]
    gaps = openspec_carrier_gaps(candidate_path, ROLE_CANDIDATE)
    if require_proof:
        gaps.extend(_candidate_gaps_for_proof(candidate_path, candidate_head))
    return gaps


def evaluate_mutation(
    request: MutationRequest,
    *,
    root: Path,
    current_head: str,
) -> MutationEvaluation:
    if not request.apply and request.command != "land":
        return MutationEvaluation(ok=True, state="dry_run")
    gaps: list[str] = []
    if request.apply and not request.authorized:
        gaps.append("authorization_required")
    if request.apply and request.expect_head is None:
        gaps.append("expect_head_required")
    elif request.expect_head is not None and request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    status = workspace_status(root)
    if status["role"] != ROLE_WORK_LANE:
        gaps.append("protected_root_mutation")
    elif status["dirty"]:
        gaps.append("work_lane_dirty")
    else:
        gaps.extend(openspec_carrier_gaps(root, ROLE_WORK_LANE))
        closeout = cast("dict[str, object]", status.get("closeout_support", {}))
        gaps.extend(str(gap) for gap in cast("list[object]", closeout.get("required_gaps", [])))
    if request.apply:
        gaps.extend(proof_gaps(root, current_head))
    if gaps:
        return MutationEvaluation(ok=False, state="blocked", gaps=tuple(gaps))
    if not request.apply:
        return MutationEvaluation(ok=True, state="dry_run")
    return MutationEvaluation(ok=True, state=f"{request.command}_ready")


def evaluate_closeout_mutation(
    request: MutationRequest,
    *,
    root: Path,
    current_head: str,
) -> MutationEvaluation:
    gaps: list[str] = []
    if request.apply and not request.authorized:
        gaps.append("authorization_required")
    if request.expect_head is None:
        if request.apply:
            gaps.append("expect_head_required")
    elif request.expect_head != current_head:
        gaps.append("expect_head_mismatch")
    status = workspace_status(root)
    if status["role"] != ROLE_ACCEPTED_ROOT:
        gaps.append("accepted_root_required")
    elif status["dirty"]:
        gaps.append("accepted_root_dirty")
    else:
        gaps.extend(openspec_carrier_gaps(root, ROLE_ACCEPTED_ROOT))
    candidate = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate.get("head") or "")
    gaps.extend(
        _closeout_candidate_gaps(
            root,
            candidate,
            current_head,
            require_proof=request.apply and candidate_head != current_head,
        )
    )
    if gaps:
        return MutationEvaluation(ok=False, state="blocked", gaps=tuple(gaps))
    if candidate_head == current_head:
        return MutationEvaluation(ok=True, state="current")
    if not request.apply:
        return MutationEvaluation(ok=True, state="dry_run")
    return MutationEvaluation(ok=True, state=f"{request.command}_ready")


def apply_land_to_candidate(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
    admitted_decision: MutationEvaluation | None = None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    decision = admitted_decision or evaluate_mutation(
        MutationRequest(
            command="land",
            apply=True,
            authorized=authorized,
            expect_head=expect_head,
        ),
        root=root,
        current_head=current_head,
    )
    if not decision.ok:
        return {
            "ok": False,
            "state": decision.state,
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": list(decision.gaps),
            "remediation": remediation.remediation_for_gaps(decision.gaps),
        }
    base_report = candidate_base_report(root=root)
    if not base_report["ok"]:
        return base_report
    candidate_path = Path(str(base_report["path"]))
    # Carry the work-lane proof into the CANDIDATE worktree BEFORE the fast-forward merge.
    # The merge advances candidate/dev through the armed reference-transaction hook (bypass
    # removed), and the hook's candidate-branch admission runs proof_gaps against the
    # candidate worktree's own proof state. Without the proof pre-placed the sanctioned land
    # would self-block on proof_not_proven; the record is head-keyed and re-verified, so
    # pre-placing admits nothing the checks would not.
    proof_carry = carry_executed_proof_record(
        source_root=root, target_root=candidate_path, head=current_head
    )
    if not proof_carry["ok"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": list(cast("list[str]", proof_carry.get("required_gaps", []))),
            "proof_carry": proof_carry,
        }
    completed = _git(
        candidate_path,
        "merge",
        "--ff-only",
        current_head,
        check=False,
    )
    if completed.returncode != 0:
        discard_executed_proof(candidate_path, current_head)
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_update_failed"],
            "remediation": remediation.remediation_for_gaps(["candidate_update_failed"]),
            "stderr": completed.stderr.strip(),
        }
    return {
        "ok": True,
        "state": "candidate_validated",
        "branch": policy.candidate_branch,
        "head": current_head,
        "path": candidate_path.as_posix(),
        "proof_carry": proof_carry,
        "required_gaps": [],
    }


def apply_candidate_to_accepted(
    *,
    root: Path,
    authorized: bool,
    expect_head: str | None,
) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    decision = evaluate_closeout_mutation(
        MutationRequest(
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
            "ok": False,
            "state": decision.state,
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": current_head,
            "required_gaps": list(decision.gaps),
            "remediation": remediation.remediation_for_gaps(decision.gaps),
        }
    status = workspace_status(root)
    candidate_info = cast("dict[str, object]", status["candidate"])
    candidate_head = str(candidate_info["head"])
    if decision.state == "current":
        return _accepted_current_payload(
            policy=policy,
            current_head=current_head,
            candidate_head=candidate_head,
        )
    candidate_path = Path(str(candidate_info["worktree_path"]))
    return _promote_candidate_to_accepted(
        root=root,
        policy=policy,
        current_head=current_head,
        candidate_head=candidate_head,
        candidate_path=candidate_path,
    )


def _accepted_current_payload(
    *,
    policy: BranchRolePolicy,
    current_head: str,
    candidate_head: str,
) -> dict[str, object]:
    """Return the no-op accepted-root closeout payload for synchronized heads."""
    return {
        "ok": True,
        "state": "accepted_current",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": current_head,
        "candidate_head": candidate_head,
        "previous_head": current_head,
        "required_gaps": [],
    }


def _promote_candidate_to_accepted(
    *,
    root: Path,
    policy: BranchRolePolicy,
    current_head: str,
    candidate_head: str,
    candidate_path: Path,
) -> dict[str, object]:
    """Fast-forward accepted root to a newer proven candidate head."""
    if not _is_ancestor(root, current_head, candidate_head):
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": current_head,
            "candidate_head": candidate_head,
            "previous_head": current_head,
            "required_gaps": ["candidate_diverged_from_accepted"],
        }
    # Atomic compare-and-swap: advance the accepted ref to candidate_head ONLY IF the
    # accepted ref is still exactly what it was when the proof was bound. git's
    # update-ref <ref> <newvalue> <oldvalue> is the native CAS primitive. The oldvalue
    # must be the accepted REF's own resolved value (not HEAD, which need not coincide
    # with refs/heads/<accepted> in every root) so the swap compares like-with-like: a
    # concurrent agent that advanced the accepted ref after we read it makes the oldvalue
    # mismatch, so the swap fails cleanly rather than overwriting their landing (Axiom 1
    # held: the proof always covers exactly the tree that becomes accepted; the
    # check-time / use-time TOCTOU window is eliminated).
    accepted_ref = f"refs/heads/{policy.accepted_branch}"
    accepted_old = _git(root, "rev-parse", "--verify", accepted_ref).stdout.strip()
    transition = CloseoutTransition(
        ref_name=accepted_ref,
        old_value=accepted_old,
        new_value=candidate_head,
        candidate_head=candidate_head,
    )
    # Write the one-shot closeout-intent marker in the SAME capture as accepted_old +
    # candidate_head, immediately before the CAS. This is what lets the reference-
    # transaction hook tell THIS official closeout apart from a hand-typed raw ref move
    # to the same candidate head (R12). The marker is consumed and re-verified by the
    # hook's admission; it is a local discipline signal, not a trust root (R19). Cleared
    # on every terminal path below so a consumed/dead marker never lingers as a reusable
    # admit token; crash residue is reclaimed by its TTL and the stale sweep.
    sweep_stale_closeout_intents(root)
    intent = write_closeout_intent(
        root=root,
        transition=transition,
        evidence_digest=_candidate_evidence_digest(candidate_path, candidate_head),
        # Bind the marker's policy digest to the PROMOTED head's committed tree, matching
        # the proof's stamp and the hook's check (both key on candidate_head). Reading the
        # working tree here would bind the OLD accepted tree and mismatch on any closeout
        # that changes a gate policy — the same skew Component 1 fixes for the proof.
        gate_policy_digest=gate_policy_digest(root, tree_ref=candidate_head),
    )
    try:
        return _advance_accepted_ref(
            root=root,
            policy=policy,
            transition=transition,
            candidate_path=candidate_path,
            current_head=current_head,
        )
    finally:
        clear_closeout_intent(root, str(intent["nonce"]))


def _candidate_evidence_digest(candidate_path: Path, candidate_head: str) -> str:
    """The executed-proof evidence digest bound to candidate_head, or '' if absent.

    Binds the closeout-intent marker to the exact proof the closeout carries, so a
    marker minted for one proof cannot authorize a move of a differently-proven tree.
    """
    record = executed_proof_record(candidate_path, candidate_head)
    if not isinstance(record, dict):
        return ""
    evidence = record.get("evidence")
    return str(evidence.get("digest", "")) if isinstance(evidence, dict) else ""


def _advance_accepted_ref(
    *,
    root: Path,
    policy: BranchRolePolicy,
    transition: CloseoutTransition,
    candidate_path: Path,
    current_head: str,
) -> dict[str, object]:
    candidate_head = transition.candidate_head

    def blocked(gaps: list[str], **extra: object) -> dict[str, object]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": current_head,
            "previous_head": current_head,
            "required_gaps": gaps,
            **extra,
        }

    # Carry the executed proof into the ACCEPTED root BEFORE the CAS. The CAS now routes
    # through the armed reference-transaction hook (the ETHOS_ALLOW_REF_MOVE bypass is
    # gone), and the hook re-runs proof_gaps against the accepted root — which reads proof
    # state from THIS worktree's `.ethos/state/proof/`, not the candidate's. If the proof
    # were still carried after the CAS (as it was under the bypass), the hook would find no
    # proof at candidate_head and abort the sanctioned closeout with proof_not_proven. The
    # record is head-keyed and re-verified on read, so pre-placing it cannot admit anything
    # the checks would not: a raw ref move to the same head still fails on the missing
    # one-shot closeout-intent marker.
    proof_carry = carry_executed_proof_record(
        source_root=candidate_path, target_root=root, head=candidate_head
    )
    if not proof_carry["ok"]:
        return blocked(
            list(cast("list[str]", proof_carry.get("required_gaps", []))), proof_carry=proof_carry
        )
    completed = _git(
        root,
        "update-ref",
        transition.ref_name,
        transition.new_value,
        transition.old_value,
        check=False,
    )
    if completed.returncode != 0:
        # The CAS lost (a concurrent advance moved the accepted ref). Reclaim the proof we
        # pre-placed for a head that never became accepted so it does not linger as orphan
        # local state; it is inert either way (a later move to it still needs a marker).
        discard_executed_proof(root, candidate_head)
        return blocked(
            ["accepted_advanced_concurrently"],
            remediation=remediation.remediation_for_gaps(["accepted_advanced_concurrently"]),
            stderr=completed.stderr.strip(),
        )
    # CAS won: sync the accepted worktree/index to the ref it now points at. Closeout
    # admission already required the accepted root to be clean, and the ref now points
    # at candidate_head; `reset --keep candidate_head` can become a no-op after the ref
    # move because HEAD already resolves to candidate_head even while the worktree still
    # contains the previous tree. A checked hard reset is therefore the narrow Git-native
    # synchronization step: it cannot discard admitted user edits (dirty roots were
    # blocked) and it makes the promoted truth visible in the accepted checkout.
    synced, sync_attempts = _sync_accepted_worktree(root, candidate_head)
    if synced.returncode != 0:
        return blocked(
            ["accepted_worktree_sync_failed"],
            candidate_head=candidate_head,
            stderr=synced.stderr.strip(),
            sync_attempts=sync_attempts,
        )
    post_status = _git(root, "status", "--short", check=False)
    if post_status.returncode != 0 or post_status.stdout.strip():
        return blocked(
            ["accepted_worktree_dirty_after_sync"],
            candidate_head=candidate_head,
            stderr=post_status.stderr.strip(),
            status=post_status.stdout.strip(),
        )
    return {
        "ok": True,
        "state": "accepted_validated",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": candidate_head,
        "previous_head": current_head,
        "proof_carry": proof_carry,
        "sync_attempts": sync_attempts,
        "required_gaps": [],
    }


def candidate_base_report(*, root: Path) -> dict[str, object]:
    policy = load_branch_role_policy(root)
    current_head = _git(root, "rev-parse", "HEAD").stdout.strip()
    status = workspace_status(root)
    if not cast("dict[str, object]", status["candidate"])["exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": ["candidate_branch_missing"],
        }
    if not cast("dict[str, object]", status["candidate"])["worktree_exists"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "required_gaps": ["candidate_worktree_missing"],
        }
    candidate_path = Path(str(cast("dict[str, object]", status["candidate"])["worktree_path"]))
    candidate_status = workspace_status(candidate_path)
    if candidate_status["dirty"]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_worktree_dirty"],
        }
    candidate_head = str(cast("dict[str, object]", status["candidate"])["head"])
    if not _is_ancestor(root, candidate_head, current_head):
        return {
            "ok": False,
            "state": "blocked",
            "branch": policy.candidate_branch,
            "head": current_head,
            "candidate_head": candidate_head,
            "path": candidate_path.as_posix(),
            "required_gaps": ["candidate_base_stale"],
            "remediation": remediation.remediation_for_gaps(["candidate_base_stale"]),
        }
    return {
        "ok": True,
        "state": "candidate_base_current",
        "branch": policy.candidate_branch,
        "head": current_head,
        "candidate_head": candidate_head,
        "path": candidate_path.as_posix(),
        "required_gaps": [],
    }


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    completed = _git(root, "merge-base", "--is-ancestor", ancestor, descendant, check=False)
    return completed.returncode == 0


def _sync_accepted_worktree(
    root: Path, candidate_head: str
) -> tuple[subprocess.CompletedProcess[str], int]:
    """Synchronize the accepted checkout after the accepted ref CAS has won."""
    first = _reset_accepted_worktree(root, candidate_head)
    if first.returncode == 0 or not _is_transient_sync_failure(first.stderr):
        return first, 1
    second = _reset_accepted_worktree(root, candidate_head)
    return second, 2


def _reset_accepted_worktree(root: Path, candidate_head: str) -> subprocess.CompletedProcess[str]:
    """Hard-reset the accepted checkout to the ref the CAS already advanced.

    Runs AFTER the accepted CAS has won, so `refs/heads/<accepted>` is already at
    candidate_head: this reset moves the WORKTREE/index, not the ref (old == new ==
    candidate_head). The reference-transaction hook admits an old==new move unconditionally
    (ref_move_admission_report short-circuits equal values), so this needs no ref-move
    escape — the ETHOS_ALLOW_REF_MOVE bypass has been removed from the candidate train.
    """
    return _git(
        root,
        "reset",
        "--hard",
        candidate_head,
        check=False,
    )


def _is_transient_sync_failure(stderr: str) -> bool:
    text = stderr.lower()
    return "index.lock" in text or "could not lock index" in text


def _git(
    root: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = {**os.environ, **env} if env is not None else None
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        text=True,
        capture_output=True,
        env=run_env,
    )
