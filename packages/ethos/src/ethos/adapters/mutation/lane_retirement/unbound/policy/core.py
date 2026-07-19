"""Admission and postcondition policy for exceptional unbound Work Lane retirement."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

EVENT = "lane_retire/unbound_exceptional"


def admission_gaps(
    repo: Path,
    *,
    branch: str,
    expect_head: str,
    reason: str,
    apply: bool,
    authorized: bool,
    break_glass: bool,
    confirm_irreversible: bool,
    observed: dict[str, object],
) -> list[str]:
    """Return every fail-closed admission gap before a ref effect."""
    gaps: list[str] = []
    branch_gap = branch_admission_gap(repo, branch=branch, observed=observed)
    if branch_gap:
        gaps.append(branch_gap)
    if not reason:
        gaps.append("retire_reason_required")
    if not expect_head:
        gaps.append("expect_head_required")
    elif expect_head != observed["head"]:
        gaps.append("expect_head_mismatch")
    if not all(cast("dict[str, str]", observed["protected_refs"]).values()):
        gaps.append("unbound_retire_protected_ref_unavailable")
    gaps.extend(
        chronicle_gaps(
            cast("dict[str, object]", observed["chronicle"]),
            branch=branch,
            head=str(observed["head"]),
        )
    )
    if apply and not authorized:
        gaps.append("authorization_required")
    if apply and not break_glass:
        gaps.append("unbound_retire_requires_break_glass")
    if apply and not confirm_irreversible:
        gaps.append("irreversible_confirmation_required")
    return sorted(set(gaps))


def branch_admission_gap(repo: Path, *, branch: str, observed: dict[str, object]) -> str:
    """Return the first target/ref/lifecycle mismatch for this transition."""
    policy = load_branch_role_policy(repo)
    checks = (
        (not branch, "unbound_retire_branch_required"),
        (policy.role_for_branch(branch) != ROLE_WORK_LANE, "unbound_retire_not_work_lane"),
        (not str(observed["head"]), "unbound_retire_branch_not_found"),
        (not bool(observed["status_unbound"]), "unbound_retire_ref_not_unbound"),
        (observed["worktree_binding"] != "unbound", "unbound_retire_worktree_binding_drift"),
        (
            observed["relation_to_accepted"] != "ancestor_of_accepted",
            "unbound_retire_not_accepted_ancestor",
        ),
        (
            bool(observed[observation.ACTIVE_LEASE_PRESENT]),
            "unbound_retire_active_lease",
        ),
    )
    return next((gap for failed, gap in checks if failed), "")


def chronicle_gaps(chronicle: dict[str, object], *, branch: str, head: str) -> list[str]:
    """Require accepted, exact Chronicle and Claim evidence in priority order."""
    return (
        reference_gaps(chronicle)
        or target_gaps(chronicle, branch=branch, head=head)
        or claim_gaps(chronicle)
    )


def reference_gaps(chronicle: dict[str, object]) -> list[str]:
    """Validate the local Chronicle path and its accepted-byte identity."""
    checks = (
        (not chronicle["ref"], "unbound_retire_chronicle_ref_required"),
        (not chronicle["path_valid"], "unbound_retire_chronicle_ref_invalid"),
        (not chronicle[observation.LOCAL_PRESENT], "unbound_retire_chronicle_missing"),
        (
            not chronicle[observation.ACCEPTED_PRESENT],
            "unbound_retire_chronicle_not_accepted",
        ),
        (
            not chronicle["byte_identical_to_accepted"],
            "unbound_retire_chronicle_content_drift",
        ),
    )
    return [gap for failed, gap in checks if failed][:1]


def target_gaps(chronicle: dict[str, object], *, branch: str, head: str) -> list[str]:
    """Require the Chronicle to name the exact exceptional target."""
    if chronicle["event"] != EVENT:
        return ["unbound_retire_chronicle_event_missing"]
    if chronicle["target_branch"] != branch or chronicle["target_head"] != head:
        return ["unbound_retire_chronicle_target_mismatch"]
    return []


def claim_gaps(chronicle: dict[str, object]) -> list[str]:
    """Require the Chronicle-named active Claim to match accepted bytes."""
    checks = (
        (not chronicle["target_claim"], "unbound_retire_chronicle_claim_missing"),
        (
            not chronicle[observation.CLAIM_LOCAL_PRESENT]
            or not chronicle[observation.CLAIM_ACCEPTED_PRESENT],
            "unbound_retire_claim_missing",
        ),
        (
            not chronicle["claim_byte_identical_to_accepted"],
            "unbound_retire_claim_content_drift",
        ),
        (
            not chronicle["claim_id_matches_target"] or not chronicle["claim_active"],
            "unbound_retire_claim_target_mismatch",
        ),
    )
    return [gap for failed, gap in checks if failed][:1]


def accepted_control_root(
    status: dict[str, object],
    *,
    accepted_head: str,
) -> tuple[Path | None, str]:
    """Find the current accepted-root checkout that owns durable local records."""
    worktrees = status.get("worktrees")
    if not isinstance(worktrees, list):
        return None, "unbound_retire_accepted_control_root_unavailable"
    for worktree in worktrees:
        if not isinstance(worktree, dict) or worktree.get("role") != ROLE_ACCEPTED_ROOT:
            continue
        raw_path = str(worktree.get("path") or "")
        if not raw_path:
            continue
        root = Path(raw_path).resolve()
        if not root.is_dir():
            return None, "unbound_retire_accepted_control_root_unavailable"
        current = observation.ref_head(root, "HEAD")
        if not current or current != accepted_head:
            return None, "unbound_retire_accepted_control_root_stale"
        return root, ""
    return None, "unbound_retire_accepted_control_root_unavailable"


def post_effect_gaps(
    *,
    before: dict[str, object],
    after: dict[str, object],
    deleted: object,
) -> list[str]:
    """Verify that the sole compare-and-delete effect achieved no more or less."""
    gaps: list[str] = []
    if int(getattr(deleted, "returncode", 1)) != 0:
        gaps.append("unbound_retire_ref_delete_failed")
    if before["protected_refs"] != after["protected_refs"]:
        gaps.append("unbound_retire_protected_refs_changed")
    if observation.chronicle_binding(before) != observation.chronicle_binding(after):
        gaps.append("unbound_retire_chronicle_changed")
    if after["head"]:
        gaps.append("unbound_retire_ref_remove_not_observed")
    if after["status_unbound"] or after["worktree_binding"] == "unbound":
        gaps.append("unbound_retire_status_postcondition_not_observed")
    if after[observation.ACTIVE_LEASE_PRESENT]:
        gaps.append("unbound_retire_active_lease")
    return sorted(set(gaps))
