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


def promote_candidate_to_accepted(  # noqa: C901, PLR0911, RUF100 - bounded closeout transition matrix
    request: CloseoutRequest,
    *,
    dependencies: CloseoutDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, object]:
    """Promote candidate; when enabled, atomically fast-forward release too."""
    root, policy, current, candidate = (
        request.root,
        request.policy,
        request.current_head,
        request.candidate_head,
    )
    runner, ancestor = dependencies.run_git, dependencies.is_ancestor

    def fail(gap: str, *, head: str = current, **extra: object) -> dict[str, object]:
        return _blocked(policy, head, [gap], **extra)

    if not ancestor(root, current, candidate):
        return fail("candidate_diverged_from_accepted", candidate_head=candidate)
    mirror = policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    release_old = (
        runner(root, "rev-parse", policy.release_branch, check=False).stdout.strip()
        if mirror
        else ""
    )
    if mirror and (not release_old or not ancestor(root, release_old, current)):
        gap = (
            "release_mirror_release_branch_missing"
            if not release_old
            else (
                "release_mirror_ahead_of_accepted"
                if ancestor(root, current, release_old)
                else "release_mirror_diverged"
            )
        )
        return fail(gap, candidate_head=candidate)
    accepted = _transition(root, policy.accepted_branch, candidate, runner)
    release = _transition(root, policy.release_branch, candidate, runner) if mirror else None
    sweep_stale_closeout_intents(root)
    proof = dependencies.carry_proof(
        source_root=request.candidate_path, target_root=root, head=candidate
    )
    if failure := proof_carry_failure(request, proof):
        return failure
    evidence_digest = _proof_digest(request.candidate_path, candidate)
    policy_digest = gate_policy_digest(root, tree_ref=candidate)
    bootstrap = bool(release and _hook_changed(request, runner))
    transitions = (accepted,) if bootstrap else tuple(item for item in (accepted, release) if item)
    update = _advance_refs(root, transitions, evidence_digest, policy_digest, runner)
    if update.returncode:
        dependencies.discard_proof(root, candidate)
        return fail(
            "accepted_advanced_concurrently",
            remediation=remediation.remediation_for_gaps(["accepted_advanced_concurrently"]),
            stderr=update.stderr.strip(),
        )
    synced, attempts = _sync(root, candidate, runner)
    if synced.returncode:
        return fail(
            "accepted_worktree_sync_failed",
            candidate_head=candidate,
            stderr=synced.stderr.strip(),
            sync_attempts=attempts,
        )
    status = runner(root, "status", "--short", check=False)
    if status.returncode or status.stdout.strip():
        return fail(
            "accepted_worktree_dirty_after_sync",
            candidate_head=candidate,
            stderr=status.stderr.strip(),
            status=status.stdout.strip(),
        )
    if bootstrap and release:
        update = _advance_refs(root, (release,), evidence_digest, policy_digest, runner)
        if update.returncode:
            return fail(
                "release_mirror_bootstrap_incomplete",
                head=candidate,
                candidate_head=candidate,
                accepted_advanced=True,
                release_mirror={
                    "mode": RELEASE_MIRROR_ACCEPTED_FF,
                    "branch": policy.release_branch,
                    "previous_head": release_old,
                    "head": release_old,
                    "worktree_sync": "not_attempted",
                    "bootstrap": "incomplete",
                    "stderr": update.stderr.strip(),
                },
            )
    mirror_result = sync_release_mirror(release, request.worktrees, candidate, release_old, runner)
    if mirror_result["worktree_sync"] in {"failed", "dirty"}:
        gap = (
            "release_mirror_worktree_sync_failed"
            if mirror_result["worktree_sync"] == "failed"
            else "release_mirror_worktree_dirty_after_sync"
        )
        return fail(gap, head=candidate, candidate_head=candidate, release_mirror=mirror_result)
    if bootstrap:
        mirror_result["bootstrap"] = "completed"
    return {
        "ok": True,
        "state": "accepted_validated",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": candidate,
        "previous_head": current,
        "proof_carry": proof,
        "sync_attempts": attempts,
        "release_mirror": mirror_result,
        "required_gaps": [],
    }


def _advance_refs(root, transitions, evidence_digest, policy_digest, runner):
    intents = [
        write_closeout_intent(
            root=root,
            transition=item,
            evidence_digest=evidence_digest,
            gate_policy_digest=policy_digest,
        )
        for item in transitions
    ]
    try:
        program = "\n".join(
            [
                "start",
                *(
                    f"update {item.ref_name} {item.new_value} {item.old_value}"
                    for item in transitions
                ),
                "prepare",
                "commit",
                "",
            ]
        )
        return runner(root, "update-ref", "--stdin", check=False, stdin=program)
    finally:
        for intent in intents:
            clear_closeout_intent(root, str(intent["nonce"]))


def _hook_changed(request: CloseoutRequest, runner) -> bool:
    blobs = [
        runner(
            request.root,
            "rev-parse",
            f"{head}:.githooks/reference-transaction",
            check=False,
        )
        for head in (request.current_head, request.candidate_head)
    ]
    return (
        all(not item.returncode for item in blobs)
        and blobs[0].stdout.strip() != blobs[1].stdout.strip()
    )


def _transition(root, branch, head, runner):
    return CloseoutTransition(
        f"refs/heads/{branch}",
        runner(root, "rev-parse", "--verify", branch).stdout.strip(),
        head,
        head,
    )


def _sync(root, head, runner):
    result = runner(root, "reset", "--hard", head, check=False)
    if result.returncode and any(
        token in result.stderr.lower() for token in ("index.lock", "could not lock index")
    ):
        return runner(root, "reset", "--hard", head, check=False), 2
    return result, 1


def sync_release_mirror(transition, worktrees, head, previous, runner):
    if transition is None:
        return {"mode": "independent", "worktree_sync": "not_enabled"}
    branch = transition.ref_name.removeprefix("refs/heads/")
    root = next(
        (
            Path(str(item["path"]))
            for item in worktrees
            if item.get("branch") == branch
            and item.get("worktree_binding") in {"current", "linked"}
        ),
        None,
    )
    result = {
        "mode": RELEASE_MIRROR_ACCEPTED_FF,
        "branch": branch,
        "previous_head": previous,
        "head": head,
        "worktree_sync": "not_linked" if root is None else "synced",
    }
    if root is None:
        return result
    reset, attempts = _sync(root, head, runner)
    if reset.returncode:
        return {
            **result,
            "worktree_sync": "failed",
            "sync_attempts": attempts,
            "stderr": reset.stderr.strip(),
        }
    status = runner(root, "status", "--short", check=False)
    return {
        **result,
        "worktree_sync": "dirty" if status.returncode or status.stdout.strip() else "synced",
    }


def _blocked(policy, current, gaps, **extra):
    return {
        "ok": False,
        "state": "blocked",
        "branch": policy.accepted_branch,
        "source_branch": policy.candidate_branch,
        "head": current,
        "candidate_head": extra.pop("candidate_head", ""),
        "previous_head": current,
        "required_gaps": gaps,
        **extra,
    }


def _proof_digest(root, head):
    record = executed_proof_record(root, head)
    return str(record.get("evidence", {}).get("digest", "")) if isinstance(record, dict) else ""


def proof_carry_failure(request: CloseoutRequest, proof: object) -> dict[str, object] | None:
    if isinstance(proof, dict) and proof.get("ok") is True:
        return None
    raw = proof.get("required_gaps") if isinstance(proof, dict) else None
    gaps = [str(gap) for gap in raw] if isinstance(raw, list) and raw else ["proof_invalid"]
    return _blocked(
        request.policy,
        request.current_head,
        gaps,
        proof_carry=proof,
    )
