"""Admit an exact staged overlay into the next Change generation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal
from typing import TypedDict

from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import git_stdout
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.normalization.coercion import repository_path_matches

if TYPE_CHECKING:
    from pathlib import Path


class ChangeOverlay(TypedDict):
    """Exact pre-transition overlay observation."""

    paths: tuple[str, ...]
    digest: str
    required_gaps: list[str]


EffectState = Literal["zero_effect", "mutated", "committed"]
CompensationState = Literal["not_required", "not_attempted", "completed", "failed"]
ResidueState = Literal[
    "absent",
    "retained",
    "lease_finalization_pending",
    "terminal_attestation_pending",
]
LifecycleOutcomeKind = Literal[
    "zero_effect",
    "mutation_uncompensated",
    "mutation_compensated",
    "compensation_failed",
    "committed_complete",
    "committed_residue",
    "lease_finalization_pending",
    "terminal_attestation_pending",
]
_OUTCOME_STATES: dict[
    LifecycleOutcomeKind,
    tuple[EffectState, CompensationState, ResidueState],
] = {
    "zero_effect": ("zero_effect", "not_required", "absent"),
    "mutation_uncompensated": ("mutated", "not_attempted", "retained"),
    "mutation_compensated": ("mutated", "completed", "absent"),
    "compensation_failed": ("mutated", "failed", "retained"),
    "committed_complete": ("committed", "not_required", "absent"),
    "committed_residue": ("committed", "not_required", "retained"),
    "lease_finalization_pending": (
        "committed",
        "not_required",
        "lease_finalization_pending",
    ),
    "terminal_attestation_pending": (
        "committed",
        "not_required",
        "terminal_attestation_pending",
    ),
}


class LifecycleEffectOutcome(TypedDict):
    """Closed effect-boundary projection shared by lifecycle mutations."""

    effect_state: EffectState
    compensation_state: CompensationState
    residue_state: ResidueState
    next_action: str
    user_decision_required: bool


def lifecycle_effect_outcome(
    *,
    kind: LifecycleOutcomeKind,
    next_action: str = "",
    user_decision_required: bool = False,
) -> LifecycleEffectOutcome:
    """Project one valid lifecycle effect outcome from a closed state algebra."""
    states = _OUTCOME_STATES[kind]
    effect_state, compensation_state, residue_state = states
    return {
        "effect_state": effect_state,
        "compensation_state": compensation_state,
        "residue_state": residue_state,
        "next_action": next_action,
        "user_decision_required": user_decision_required,
    }


def lifecycle_report(
    branch: str,
    head: str,
    state: str,
    gaps: list[str],
    **details: object,
) -> dict[str, object]:
    """Project the common lifecycle mutation result contract."""
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "branch": branch,
        "head": head,
        "required_gaps": list(dict.fromkeys(gaps)),
        **details,
    }


def work_lane_transition_gaps(
    root: Path,
    *,
    branch: str,
    head: str,
    expect_head: str,
    lease: dict[str, object],
    actor: str,
    role_gap: str,
    require_clean: bool = False,
) -> list[str]:
    """Validate the coordinates shared by OpenSpec lifecycle transitions."""
    lease_state = str(lease.get("lease_state") or "missing")
    if lease_state != "valid":
        return [
            {
                "unknown": f"work_lane_lease_unknown:{branch}",
                "expired": f"work_lane_lease_expired:{branch}",
            }.get(lease_state, f"work_lane_missing_lease:{branch}")
        ]
    checks = (
        (load_branch_role_policy(root).role_for_branch(branch) == ROLE_WORK_LANE, role_gap),
        (head == expect_head, "expect_head_mismatch"),
        (not require_clean or not git_stdout(root, "status", "--short"), "work_lane_dirty"),
        (lease.get("holder_ref") == actor, "lease_actor_mismatch"),
    )
    return [gap for valid, gap in checks if not valid]


def change_overlay_report(
    root: Path,
    *,
    scope: tuple[str, ...],
    expected_digest: str,
    apply: bool,
) -> ChangeOverlay:
    """Bind a clean tree or one fully staged, scope-covered overlay."""
    paths = changed_paths(root)
    if not paths:
        return {"paths": (), "digest": "", "required_gaps": []}
    unstaged = tuple(git_stdout(root, "diff", "--name-only", "--").splitlines())
    staged = tuple(git_stdout(root, "diff", "--cached", "--name-only", "--").splitlines())
    digest = dirty_content_sha256(root)
    gaps: list[str] = []
    if unstaged or set(staged) != set(paths):
        gaps.append("openspec_change_overlay_not_fully_staged")
    uncovered = [
        path
        for path in paths
        if not any(repository_path_matches(path, pattern) for pattern in scope)
    ]
    gaps.extend(f"openspec_change_overlay_uncovered:{path}" for path in uncovered)
    if expected_digest and expected_digest != digest:
        gaps.append("openspec_change_overlay_digest_mismatch")
    if apply and not expected_digest:
        gaps.append("openspec_change_overlay_digest_required")
    return {"paths": paths, "digest": digest, "required_gaps": gaps}
