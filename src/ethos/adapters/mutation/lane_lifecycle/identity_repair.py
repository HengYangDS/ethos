"""Same-tree commit identity replacement across the local integration train."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.commit_identity import equivalent_commit_identity
from ethos.adapters.repo.commit_identity import verify_commit_trust
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import ref_worktree_paths
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.repo.git_ref_worktrees import worktree_sync_gap
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


@dataclass(frozen=True, slots=True)
class _Replacement:
    root: Path
    branch: str
    status: dict[str, object]
    refs: dict[str, str]
    authority: Commitment
    evidence: dict[str, object]
    lease: dict[str, object]
    old: str
    new: str


def repair_commit_identity(
    *,
    root: Path,
    old_commit: str,
    new_commit: str,
    expect_head: str,
    apply: bool,
    authorized: bool,
) -> dict[str, object]:
    """Replace one semantically identical commit OID through exact train-wide CAS."""
    status = workspace_status(root, include_foreign_path_scope=False)
    branch = str(status.get("branch") or "")
    head = current_tracked_head(root)
    lease = leases_by_branch(root).get(branch, {})
    proof = proof_attestation(root, new_commit)
    trust = verify_commit_trust(root, new_commit)
    train, update_gaps = _train_refs(root, old_commit, new_commit)
    gaps = [
        gap
        for valid, gap in (
            (status.get("role") == ROLE_WORK_LANE, "work_lane_required"),
            (not status.get("dirty"), "work_lane_dirty"),
            (authorized or not apply, "authorization_required"),
            (expect_head == new_commit, "expect_head_mismatch"),
            (head == new_commit, "identity_repair_head_mismatch"),
            (old_commit != new_commit, "identity_repair_oid_unchanged"),
            (
                equivalent_commit_identity(root, old_commit, new_commit),
                "identity_repair_commit_payload_mismatch",
            ),
            (lease.get("lease_state") == "valid", f"work_lane_lease_invalid:{branch}"),
            (
                str(lease.get("holder_ref") or "") == os.environ.get("ETHOS_ACTOR", "").strip(),
                "lease_actor_mismatch",
            ),
            (str(lease.get("expected_head") or "") == new_commit, "lease_head_stale"),
            (
                str(lease.get("expected_tree") or "") == current_tree(root, new_commit),
                "lease_expected_tree_stale",
            ),
            (proof is not None, (proof_gaps(root, new_commit) or ["proof_not_proven"])[0]),
        )
        if not valid
    ]
    trust_gaps = trust.get("required_gaps")
    if isinstance(trust_gaps, list):
        gaps.extend(str(gap) for gap in trust_gaps)
    gaps.extend(update_gaps)
    gaps.extend(_worktree_gaps(root, status, train, old_commit, new_commit))
    report = _report(branch, old_commit, new_commit, trust, gaps)
    if gaps or not apply:
        return report | {"state": "blocked" if gaps else "ready_to_repair_identity"}
    authority = load_lease_bound_commitment(root, lease=lease)
    evidence = {
        "proof": proof.model_dump(mode="json") if proof is not None else {},
        "commit_trust": trust,
    }
    replacement = _Replacement(
        root=root,
        branch=branch,
        status=status,
        refs=train,
        authority=authority,
        evidence=evidence,
        lease=lease,
        old=old_commit,
        new=new_commit,
    )
    try:
        candidate_attestation = _apply_candidate_replacement(replacement)
        accepted_attestation = _apply_accepted_replacement(replacement)
    except ValueError as error:
        return _report(
            branch,
            old_commit,
            new_commit,
            trust,
            ["identity_repair_cas_rejected"],
            stderr=str(error),
        )
    return _report(
        branch,
        old_commit,
        new_commit,
        trust,
        [],
        state="identity_repaired",
        candidate_attestation=candidate_attestation,
        accepted_attestation=accepted_attestation,
    )


def _train_refs(root: Path, old: str, new: str) -> tuple[dict[str, str], list[str]]:
    policy = load_branch_role_policy(root)
    branches = [policy.candidate_branch, policy.accepted_branch]
    if policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF:
        branches.append(policy.release_branch)
    heads = {branch: ref_head(root, branch) for branch in branches}
    gaps = [
        f"identity_repair_ref_stale:{branch}:{head}"
        for branch, head in heads.items()
        if head not in {old, new}
    ]
    return heads, gaps


def _worktree_gaps(
    root: Path,
    status: dict[str, object],
    refs: dict[str, str],
    old: str,
    new: str,
) -> list[str]:
    worktrees = cast("list[dict[str, object]]", status.get("worktrees") or [])
    gaps = []
    for branch, head in refs.items():
        if head != old:
            continue
        paths = ref_worktree_paths(worktrees, branch)
        if gap := worktree_sync_gap(root, paths, branch, old, old, new):
            gaps.append(f"identity_repair_{branch.replace('/', '_')}_{gap}")
    return gaps


def _sync_branch_worktrees(
    root: Path,
    status: dict[str, object],
    branch: str,
    old: str,
    new: str,
) -> dict[str, object]:
    worktrees = cast("list[dict[str, object]]", status.get("worktrees") or [])
    return sync_ref_worktrees(
        root,
        ref_worktree_paths(worktrees, branch),
        branch,
        new,
        old,
    )


def _apply_candidate_replacement(replacement: _Replacement) -> dict[str, object]:
    root, old, new = replacement.root, replacement.old, replacement.new
    policy = load_branch_role_policy(root)
    candidate = policy.candidate_branch
    if replacement.refs[candidate] == new:
        sync = _sync_branch_worktrees(root, replacement.status, candidate, old, new)
        if sync["worktree_sync"] == "failed":
            message = "identity_repair_candidate_worktree_sync_failed"
            raise ValueError(message)
        return {"state": "recognized", "worktree_sync": sync}
    effect = GitEffect(
        updates={f"refs/heads/{candidate}": GitRefUpdate(expected=old, desired=new)},
        assertions={f"refs/heads/{replacement.branch}": new},
    )
    plan = _plan(replacement, effect)
    attestation = execute_git_effect(root, plan, issuer=str(replacement.lease["holder_ref"]))
    sync = _sync_branch_worktrees(root, replacement.status, candidate, old, new)
    if sync["worktree_sync"] == "failed":
        message = "identity_repair_candidate_worktree_sync_failed"
        raise ValueError(message)
    return {"effect": attestation.model_dump(mode="json"), "worktree_sync": sync}


def _apply_accepted_replacement(replacement: _Replacement) -> dict[str, object]:
    root, old, new = replacement.root, replacement.old, replacement.new
    policy = load_branch_role_policy(root)
    branches = [policy.accepted_branch]
    if (
        policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
        and replacement.refs[policy.release_branch] == old
    ):
        branches.append(policy.release_branch)
    updates = {
        f"refs/heads/{name}": GitRefUpdate(expected=old, desired=new)
        for name in branches
        if replacement.refs[name] == old
    }
    if not updates:
        synchronized = [
            {"branch": name, **_sync_branch_worktrees(root, replacement.status, name, old, new)}
            for name in branches
        ]
        if any(item["worktree_sync"] == "failed" for item in synchronized):
            message = "identity_repair_accepted_worktree_sync_failed"
            raise ValueError(message)
        return {"state": "recognized", "worktree_sync": synchronized}
    effect = GitEffect(
        updates=updates,
        assertions={f"refs/heads/{policy.candidate_branch}": new},
    )
    plan = _plan(replacement, effect)
    attestation = execute_git_effect(root, plan, issuer=str(replacement.lease["holder_ref"]))
    synchronized = [
        {"branch": name, **_sync_branch_worktrees(root, replacement.status, name, old, new)}
        for name in branches
        if replacement.refs[name] == old
    ]
    if any(item["worktree_sync"] == "failed" for item in synchronized):
        message = "identity_repair_accepted_worktree_sync_failed"
        raise ValueError(message)
    return {"effect": attestation.model_dump(mode="json"), "worktree_sync": synchronized}


def _plan(replacement: _Replacement, effect: GitEffect):
    return compile_observed_git_effect(
        replacement.root,
        replacement.authority,
        effect,
        head=replacement.new,
        prior_attestations=replacement.evidence,
        policy={
            "operation": "git.ref.compare-and-swap",
            "transition": "commit.identity-replace",
            "effect_digest": effect.digest(),
            "execution_branch": replacement.branch,
        },
        values={
            "lease_generation": lease_generation(replacement.lease),
            "old_commit": replacement.old,
            "new_commit": replacement.new,
        },
    )


def _report(
    branch: str,
    old: str,
    new: str,
    trust: dict[str, object],
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    return {
        "verdict": "block" if gaps else "pass",
        "state": "blocked" if gaps else "ready_to_repair_identity",
        "branch": branch,
        "old_commit": old,
        "new_commit": new,
        "trust": trust,
        "required_gaps": list(dict.fromkeys(gaps)),
        **details,
    }
