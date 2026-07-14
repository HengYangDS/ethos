"""Atomic accepted-root closeout with an optional fast-forward release mirror."""

from __future__ import annotations

from pathlib import Path

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


def promote_candidate_to_accepted(
    *,
    root: Path,
    policy: BranchRolePolicy,
    current_head: str,
    candidate_head: str,
    candidate_path: Path,
    worktrees: list[dict[str, object]],
    run_git=run_git,
    is_ancestor_fn=is_ancestor,
    carry_proof=carry_executed_proof_record,
    discard_proof=discard_executed_proof,
) -> dict[str, object]:
    """Promote candidate; when enabled, atomically fast-forward release too."""
    if not is_ancestor_fn(root, current_head, candidate_head):
        return _blocked(
            policy,
            current_head,
            ["candidate_diverged_from_accepted"],
            candidate_head=candidate_head,
        )
    mirror = policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    release_old = (
        run_git(root, "rev-parse", policy.release_branch, check=False).stdout.strip()
        if mirror
        else ""
    )
    if mirror and (not release_old or not is_ancestor_fn(root, release_old, current_head)):
        gap = (
            "release_mirror_release_branch_missing"
            if not release_old
            else "release_mirror_ahead_of_accepted"
            if is_ancestor_fn(root, current_head, release_old)
            else "release_mirror_diverged"
        )
        return _blocked(policy, current_head, [gap], candidate_head=candidate_head)
    accepted = _transition(root, policy.accepted_branch, candidate_head, run_git)
    release = _transition(root, policy.release_branch, candidate_head, run_git) if mirror else None
    sweep_stale_closeout_intents(root)
    intents = [
        write_closeout_intent(
            root=root,
            transition=item,
            evidence_digest=_proof_digest(candidate_path, candidate_head),
            gate_policy_digest=gate_policy_digest(root, tree_ref=candidate_head),
        )
        for item in (accepted, release)
        if item
    ]
    try:
        proof = carry_proof(source_root=candidate_path, target_root=root, head=candidate_head)
        if not proof["ok"]:
            return _blocked(policy, current_head, list(proof["required_gaps"]), proof_carry=proof)
        update = _atomic_update(root, accepted, release, run_git)
        if update.returncode:
            discard_proof(root, candidate_head)
            return _blocked(
                policy,
                current_head,
                ["accepted_advanced_concurrently"],
                remediation=remediation.remediation_for_gaps(["accepted_advanced_concurrently"]),
                stderr=update.stderr.strip(),
            )
        synced, attempts = _sync(root, candidate_head, run_git)
        if synced.returncode:
            return _blocked(
                policy,
                current_head,
                ["accepted_worktree_sync_failed"],
                candidate_head=candidate_head,
                stderr=synced.stderr.strip(),
                sync_attempts=attempts,
            )
        checked = run_git(root, "status", "--short", check=False)
        if checked.returncode or checked.stdout.strip():
            return _blocked(
                policy,
                current_head,
                ["accepted_worktree_dirty_after_sync"],
                candidate_head=candidate_head,
                stderr=checked.stderr.strip(),
                status=checked.stdout.strip(),
            )
        mirror_result = _sync_mirror(release, worktrees, candidate_head, release_old, run_git)
        if mirror_result["worktree_sync"] in {"failed", "dirty"}:
            return _blocked(
                policy,
                current_head,
                [
                    "release_mirror_worktree_sync_failed"
                    if mirror_result["worktree_sync"] == "failed"
                    else "release_mirror_worktree_dirty_after_sync"
                ],
                candidate_head=candidate_head,
                release_mirror=mirror_result,
            )
        return {
            "ok": True,
            "state": "accepted_validated",
            "branch": policy.accepted_branch,
            "source_branch": policy.candidate_branch,
            "head": candidate_head,
            "previous_head": current_head,
            "proof_carry": proof,
            "sync_attempts": attempts,
            "release_mirror": mirror_result,
            "required_gaps": [],
        }
    finally:
        for intent in intents:
            clear_closeout_intent(root, str(intent["nonce"]))


def _atomic_update(root, accepted, release, run_git):
    transitions = (accepted, release) if release else (accepted,)
    program = "\n".join(
        [
            "start",
            *(f"update {item.ref_name} {item.new_value} {item.old_value}" for item in transitions),
            "prepare",
            "commit",
            "",
        ]
    )
    return run_git(root, "update-ref", "--stdin", check=False, stdin=program)


def _transition(root, branch, head, run_git):
    return CloseoutTransition(
        f"refs/heads/{branch}",
        run_git(root, "rev-parse", "--verify", branch).stdout.strip(),
        head,
        head,
    )


def _sync(root, head, run_git):
    result = run_git(root, "reset", "--hard", head, check=False)
    if not result.returncode or not any(
        token in result.stderr.lower() for token in ("index.lock", "could not lock index")
    ):
        return result, 1
    return run_git(root, "reset", "--hard", head, check=False), 2


def _sync_mirror(transition, worktrees, head, previous, run_git):
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
    reset, attempts = _sync(root, head, run_git)
    if reset.returncode:
        return {
            **result,
            "worktree_sync": "failed",
            "sync_attempts": attempts,
            "stderr": reset.stderr.strip(),
        }
    status = run_git(root, "status", "--short", check=False)
    return {
        **result,
        "worktree_sync": "dirty" if status.returncode or status.stdout.strip() else "synced",
    }


def _blocked(policy, current, gaps, **extra):
    return dict(
        ok=False,
        state="blocked",
        branch=policy.accepted_branch,
        source_branch=policy.candidate_branch,
        head=current,
        candidate_head=extra.pop("candidate_head", ""),
        previous_head=current,
        required_gaps=gaps,
        **extra,
    )


def _proof_digest(root, head):
    record = executed_proof_record(root, head)
    return str(record.get("evidence", {}).get("digest", "")) if isinstance(record, dict) else ""
