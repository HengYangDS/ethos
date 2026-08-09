"""Strict policy resolution for protected and legacy ref transitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.identity import commit_contained_in
from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.repo.commit_identity import equivalent_commit_identity
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.branch.roles import strict_branch_role_policy_from_text
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path

_ZERO_OIDS = {"0" * 40, "0" * 64}


def accepted_advance_gaps(
    repo: Path,
    policy: BranchRolePolicy,
    *,
    old_value: str,
    new_value: str,
) -> list[str]:
    """Return candidate-head and fast-forward gaps for an accepted advance."""
    candidate = policy.candidate_branch
    identity_replacement = equivalent_commit_identity(repo, old_value, new_value)
    contained = commit_contained_in(repo, new_value, candidate)
    candidate_head = git_stdout(repo, "rev-parse", "--verify", "--quiet", candidate)
    gaps = (
        []
        if new_value == candidate_head and (identity_replacement or contained)
        else ["accepted_ref_move_not_candidate_head"]
        if contained
        else ["accepted_advance_not_candidate_validated"]
    )
    if (
        not identity_replacement
        and old_value not in _ZERO_OIDS
        and not commit_contained_in(repo, old_value, new_value)
    ):
        gaps.append("accepted_ref_move_not_fast_forward")
    return gaps


def prepared_ref_intent_gaps(
    *,
    repo: Path,
    ref_name: str,
    update: GitRefUpdate,
    operation: str,
    missing_gap: str,
) -> list[str]:
    intent = claim_ref_intent(
        root=repo,
        ref_name=ref_name,
        update=update,
        operation=operation,
        phase="prepared",
    )
    gap = str(intent["gap"] or "")
    return [missing_gap if gap == "ref_intent_missing" else gap] if gap else []


def resolve_ref_move_policy(
    repo: Path, ref_name: str, old_value: str, new_value: str
) -> BranchRolePolicy:
    """Resolve the strict policy that governs one ref transition.

    The incumbent strict policy remains authoritative. When it predates the
    current schema, the promoted strict policy performs the one-control
    bootstrap. No legacy policy parser participates in admission.
    """
    branch = ref_name.removeprefix("refs/heads/")
    policy = _strict_ref_policy(repo, old_value)
    if policy is None:
        policy = _strict_ref_policy(repo, new_value)
    if policy is None:
        for revision in (old_value, new_value):
            if revision not in _ZERO_OIDS:
                profile = load_committed_repository_profile(repo, revision)
                if profile.state == "valid" and profile.declaration is not None:
                    policy = BranchRolePolicy()
                    break
    if policy is None:
        policy = _absorbed_ref_transition_policy(repo, branch, old_value, new_value)
    if policy is None:
        message = "ref_move_policy_unavailable"
        raise ValueError(message)
    if branch != policy.release_branch:
        return policy
    accepted_head = git_stdout(repo, "rev-parse", policy.accepted_branch)
    accepted_policy = _strict_ref_policy(repo, accepted_head)
    if accepted_policy is None:
        return policy
    return (
        accepted_policy if accepted_policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF else policy
    )


def _absorbed_ref_transition_policy(
    repo: Path, branch: str, old_value: str, new_value: str
) -> BranchRolePolicy | None:
    """Resolve current strict policy for one exact legacy retirement transition."""
    deleting = new_value in _ZERO_OIDS and old_value not in _ZERO_OIDS
    compensating = old_value in _ZERO_OIDS and new_value not in _ZERO_OIDS
    if not (deleting or compensating):
        return None
    current_policy = load_branch_role_policy(repo)
    accepted_head = git_stdout(repo, "rev-parse", current_policy.accepted_branch)
    accepted_policy = _strict_ref_policy(repo, accepted_head)
    if (
        accepted_policy is None
        or git_stdout(repo, "rev-parse", "HEAD") != accepted_head
        or accepted_policy.role_for_branch(branch) != "work_lane"
        or not is_ancestor(repo, old_value if deleting else new_value, accepted_head)
    ):
        return None
    intent = claim_ref_intent(
        root=repo,
        ref_name=f"refs/heads/{branch}",
        update=GitRefUpdate(expected=old_value, desired=new_value),
        operation="lane.retire" if deleting else "lane.retire.compensate",
        phase="prepared",
    )
    return accepted_policy if intent.get("present") and not intent.get("gap") else None


def _strict_ref_policy(repo: Path, revision: str) -> BranchRolePolicy | None:
    if revision in _ZERO_OIDS:
        return None
    try:
        return strict_branch_role_policy_from_text(
            committed_file_text(repo, revision, ".ethos/workspace.toml")
        )
    except (TypeError, ValueError):
        return None
