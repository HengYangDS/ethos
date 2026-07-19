# ruff: noqa: E501 - source-budget closeout preserves the exact AST in a compact representation.
# fmt: off
"""Atomic accepted-root closeout with an optional fast-forward release mirror."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.mutation.remediation.core as remediation
from ethos.adapters.admission.closeout_intent.core import CloseoutTransition
from ethos.adapters.admission.closeout_intent.core import clear_closeout_intent
from ethos.adapters.admission.closeout_intent.core import sweep_stale_closeout_intents
from ethos.adapters.admission.closeout_intent.core import write_closeout_intent
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.proof import carry_executed_proof_record
from ethos.adapters.mutation.proof import discard_executed_proof
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.repository.policy.gates import gate_policy_digest
from ethos_core.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos_core.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class CloseoutDependencies:
    """Injected closeout collaborators; production uses the canonical adapters."""

    run_git: Callable[..., subprocess.CompletedProcess[str]] = run_git
    is_ancestor: Callable[..., bool] = is_ancestor
    carry_proof: Callable[..., object] = carry_executed_proof_record
    discard_proof: Callable[..., object] = discard_executed_proof


_DEFAULT_DEPENDENCIES = CloseoutDependencies()


@dataclass(frozen=True, slots=True)
class CloseoutRequest:
    """Immutable promotion inputs shared by validation and execution."""

    root: Path
    policy: BranchRolePolicy
    current_head: str
    candidate_head: str
    candidate_path: Path
    worktrees: list[dict[str, object]]


def promote_candidate_to_accepted(request: CloseoutRequest, *, dependencies: CloseoutDependencies = _DEFAULT_DEPENDENCIES) -> dict[str, object]:
    """Promote candidate; when enabled, atomically fast-forward release too."""
    preflight = _promotion_preflight(request, dependencies)
    if isinstance(preflight, dict):
        return preflight
    return _execute_promotion(request, preflight, dependencies)


def _promotion_preflight(request: CloseoutRequest, dependencies: CloseoutDependencies) -> tuple[CloseoutTransition, CloseoutTransition | None, str] | dict[str, object]:
    if not dependencies.is_ancestor(request.root, request.current_head, request.candidate_head):
        return _blocked(request.policy, request.current_head, ["candidate_diverged_from_accepted"], candidate_head=request.candidate_head)
    mirror = request.policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    release_old = dependencies.run_git(request.root, "rev-parse", request.policy.release_branch, check=False).stdout.strip() if mirror else ""
    if mirror and (not release_old or not dependencies.is_ancestor(request.root, release_old, request.current_head)):
        gap = "release_mirror_release_branch_missing" if not release_old else "release_mirror_ahead_of_accepted" if dependencies.is_ancestor(request.root, request.current_head, release_old) else "release_mirror_diverged"
        return _blocked(request.policy, request.current_head, [gap], candidate_head=request.candidate_head)
    accepted = _transition(request.root, request.policy.accepted_branch, request.candidate_head, dependencies.run_git)
    release = _transition(request.root, request.policy.release_branch, request.candidate_head, dependencies.run_git) if mirror else None
    return accepted, release, release_old


def _execute_promotion(request: CloseoutRequest, preflight: tuple[CloseoutTransition, CloseoutTransition | None, str], dependencies: CloseoutDependencies) -> dict[str, object]:
    accepted, release, release_old = preflight
    sweep_stale_closeout_intents(request.root)
    proof = dependencies.carry_proof(source_root=request.candidate_path, target_root=request.root, head=request.candidate_head)
    if failure := proof_carry_failure(request, proof):
        return failure
    digest = _proof_digest(request.candidate_path, request.candidate_head)
    policy_digest = gate_policy_digest(request.root, tree_ref=request.candidate_head)
    bootstrap = _hook_bootstrap_required(request, release, dependencies)
    first_leg = (accepted,) if bootstrap else tuple(item for item in (accepted, release) if item is not None)
    sync_attempts = _advance_and_sync_accepted(request, dependencies, first_leg, digest, policy_digest)
    if isinstance(sync_attempts, dict):
        return sync_attempts
    if bootstrap and release:
        release_intents = _write_intents(request.root, (release,), digest, policy_digest)
        try:
            mirror_update = _ref_transaction(request.root, (release,), dependencies.run_git)
        finally:
            _clear_intents(request.root, release_intents)
        if mirror_update.returncode:
            return _blocked(request.policy, request.candidate_head, ["release_mirror_bootstrap_incomplete"], candidate_head=request.candidate_head, accepted_advanced=True, release_mirror={"mode": RELEASE_MIRROR_ACCEPTED_FF, "branch": request.policy.release_branch, "previous_head": release_old, "head": release_old, "worktree_sync": "not_attempted", "bootstrap": "incomplete", "stderr": mirror_update.stderr.strip()})
    mirror_result = sync_release_mirror(release, request.worktrees, request.candidate_head, release_old, dependencies.run_git)
    if mirror_result["worktree_sync"] in {"failed", "dirty"}:
        return _blocked(request.policy, request.candidate_head, ["release_mirror_worktree_sync_failed" if mirror_result["worktree_sync"] == "failed" else "release_mirror_worktree_dirty_after_sync"], candidate_head=request.candidate_head, release_mirror=mirror_result)
    if bootstrap:
        mirror_result["bootstrap"] = "completed"
    return {"ok": True, "state": "accepted_validated", "branch": request.policy.accepted_branch, "source_branch": request.policy.candidate_branch, "head": request.candidate_head, "previous_head": request.current_head, "proof_carry": proof, "sync_attempts": sync_attempts, "release_mirror": mirror_result, "required_gaps": []}


def _advance_and_sync_accepted(request, dependencies, transitions, evidence_digest, policy_digest):
    intents = _write_intents(request.root, transitions, evidence_digest, policy_digest)
    try:
        update = _ref_transaction(request.root, transitions, dependencies.run_git, ref_checks=((f"refs/heads/{request.policy.candidate_branch}", request.candidate_head),))
    finally:
        _clear_intents(request.root, intents)
    if update.returncode:
        dependencies.discard_proof(request.root, request.candidate_head)
        return _ref_transaction_failure(request, transitions[0], update, dependencies.run_git)
    synced, attempts = _sync(request.root, request.candidate_head, dependencies.run_git)
    if synced.returncode:
        return _blocked(request.policy, request.current_head, ["accepted_worktree_sync_failed"], candidate_head=request.candidate_head, stderr=synced.stderr.strip(), sync_attempts=attempts)
    checked = dependencies.run_git(request.root, "status", "--short", check=False)
    if checked.returncode or checked.stdout.strip():
        return _blocked(request.policy, request.current_head, ["accepted_worktree_dirty_after_sync"], candidate_head=request.candidate_head, stderr=checked.stderr.strip(), status=checked.stdout.strip())
    return attempts


def _ref_transaction_failure(request, accepted, update, run_git):
    """Classify atomic closeout failure from both observed source and target refs."""
    accepted_now = run_git(request.root, "rev-parse", "--verify", accepted.ref_name, check=False).stdout.strip()
    candidate_ref = f"refs/heads/{request.policy.candidate_branch}"
    candidate_now = run_git(request.root, "rev-parse", "--verify", candidate_ref, check=False).stdout.strip()
    observed = {"stderr": update.stderr.strip(), "observed_accepted_head": accepted_now, "observed_candidate_head": candidate_now}
    if accepted_now != accepted.old_value:
        gaps = ["accepted_advanced_concurrently"]
        return _blocked(request.policy, request.current_head, gaps, remediation=remediation.remediation_for_gaps(gaps), **observed)
    if candidate_now != request.candidate_head:
        return _blocked(request.policy, request.current_head, ["candidate_head_changed_after_control_replacement_check"], verified_candidate_head=request.candidate_head, **observed)
    return _blocked(request.policy, request.current_head, ["accepted_atomic_update_rejected"], **observed)


def _hook_bootstrap_required(request, release, dependencies):
    if release is None:
        return False
    accepted_blob = dependencies.run_git(request.root, "rev-parse", f"{request.current_head}:.githooks/reference-transaction", check=False)
    candidate_blob = dependencies.run_git(request.root, "rev-parse", f"{request.candidate_head}:.githooks/reference-transaction", check=False)
    return accepted_blob.returncode == 0 and candidate_blob.returncode == 0 and accepted_blob.stdout.strip() != candidate_blob.stdout.strip()


def _write_intents(root, transitions, evidence_digest, policy_digest):
    return [write_closeout_intent(root=root, transition=item, evidence_digest=evidence_digest, gate_policy_digest=policy_digest) for item in transitions if item]


def _clear_intents(root, intents):
    for intent in intents:
        clear_closeout_intent(root, str(intent["nonce"]))


def _ref_transaction(root, transitions, run_git, *, ref_checks=()):
    program = "\n".join(["start", *(f"update {ref} {head} {head}" for ref, head in ref_checks), *(f"update {item.ref_name} {item.new_value} {item.old_value}" for item in transitions), "prepare", "commit", ""])
    return run_git(root, "update-ref", "--stdin", check=False, stdin=program)


def _transition(root, branch, head, run_git):
    return CloseoutTransition(f"refs/heads/{branch}", run_git(root, "rev-parse", "--verify", branch).stdout.strip(), head, head)


def _sync(root, head, run_git):
    result = run_git(root, "reset", "--hard", head, check=False)
    if not result.returncode or not any(token in result.stderr.lower() for token in ("index.lock", "could not lock index")):
        return result, 1
    return run_git(root, "reset", "--hard", head, check=False), 2


def sync_release_mirror(transition, worktrees, head, previous, run_git):
    if transition is None:
        return {"mode": "independent", "worktree_sync": "not_enabled"}
    branch = transition.ref_name.removeprefix("refs/heads/")
    root = next((Path(str(item["path"])) for item in worktrees if item.get("branch") == branch and item.get("worktree_binding") in {"current", "linked"}), None)
    result = {"mode": RELEASE_MIRROR_ACCEPTED_FF, "branch": branch, "previous_head": previous, "head": head, "worktree_sync": "not_linked" if root is None else "synced"}
    if root is None:
        return result
    reset, attempts = _sync(root, head, run_git)
    if reset.returncode:
        return {**result, "worktree_sync": "failed", "sync_attempts": attempts, "stderr": reset.stderr.strip()}
    status = run_git(root, "status", "--short", check=False)
    return {**result, "worktree_sync": "dirty" if status.returncode or status.stdout.strip() else "synced"}


def _blocked(policy, current, gaps, **extra):
    return dict(ok=False, state="blocked", branch=policy.accepted_branch, source_branch=policy.candidate_branch, head=current, candidate_head=extra.pop("candidate_head", ""), previous_head=current, required_gaps=gaps, **extra)


def _proof_digest(root, head):
    record = executed_proof_record(root, head)
    return str(record.get("evidence", {}).get("digest", "")) if isinstance(record, dict) else ""


def proof_required_gaps(proof: object) -> list[str]:
    if not isinstance(proof, dict):
        return ["proof_invalid"]
    raw = proof.get("required_gaps")
    if not isinstance(raw, list) or not raw or not all(isinstance(gap, str) for gap in raw):
        return ["proof_invalid"]
    return [gap for gap in raw if isinstance(gap, str)]


def proof_carry_failure(request: CloseoutRequest, proof: object) -> dict[str, object] | None:
    if not isinstance(proof, dict):
        return _blocked(request.policy, request.current_head, ["proof_invalid"], proof_carry=proof)
    if proof.get("ok") is not True:
        return _blocked(request.policy, request.current_head, proof_required_gaps(proof), proof_carry=proof)
    return None
# fmt: on
