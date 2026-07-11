"""Work Lane ref-transition admission — lease-bound local coordination.

The reference-transaction hook fires on every ref update. For a WORK-lane branch this
reducer decides, in the ``prepared`` phase, whether the move is admissible against the
lane's current lease, and in the ``committed`` phase advances the local lease head after
Git has won. It is a peer of `ref_move_admission_report` (which guards accepted/candidate
promotion) split into its own module so `admission/core.py` stays within its size budget
and each admission concern reads as one cohesive unit.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.core import advance_lease_head
from ethos.adapters.store.state.lease.projection import integer_value

_ZERO_OID = "0" * 40


def work_lane_ref_transition_report(
    *,
    root: Path,
    phase: str,
    ref_name: str,
    old_value: str,
    new_value: str,
) -> dict[str, object]:
    """Check or record one Work Lane ref transition against its current lease.

    ``prepared`` is the blocking admission point. ``committed`` updates ignored
    local coordination after Git has won; failure there is repair-required rather
    than an atomic rollback claim.
    """
    repo = root.resolve()
    status = workspace_status(repo)
    branch = ref_name.removeprefix("refs/heads/")
    # A ref CREATION (old==zero) starts the lane saga; a ref DELETION (new==zero) tears it
    # down. Neither promotes anything to a protected branch, so both are admitted without
    # lease binding. The deletion case is what lets a lane with a legacy/unnormalizable
    # lease still be retired: its `git update-ref -d` fires this hook and must not block on
    # lease admission it cannot satisfy — otherwise promotion-free cleanup is unreachable.
    if old_value in {_ZERO_OID, ""} or new_value in {_ZERO_OID, ""}:
        reason = (
            "lane_creation_saga_started"
            if old_value in {_ZERO_OID, ""}
            else "lane_teardown_ref_deletion"
        )
        return _admit(
            phase=phase, ref_name=ref_name, old_value=old_value, new_value=new_value, reason=reason
        )
    worktrees = cast("list[dict[str, str]]", status.get("worktrees", []))
    leases = leases_by_branch(worktrees, current_path=repo)
    lease = leases.get(branch, {})
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    gaps = _work_lane_lease_transition_gaps(
        branch=branch,
        lease=lease,
        actor=actor,
        old_value=old_value,
    )
    base: dict[str, object] = {
        "ok": not gaps,
        "state": "admitted" if not gaps else "blocked",
        "phase": phase,
        "ref": ref_name,
        "branch": branch,
        "old_value": old_value,
        "new_value": new_value,
        "lease": lease,
        "decision": {
            "action": "allow" if not gaps else "block",
            "reason": "work_lane_ref_transition_admitted"
            if not gaps
            else "work_lane_ref_transition_stale",
        },
        "required_gaps": gaps,
    }
    if gaps or phase != "committed":
        return base
    try:
        updated = advance_lease_head(
            _control_state_db(status, repo),
            subject=branch,
            holder_ref=actor,
            expected_lease_id=str(lease.get("lease_id") or lease.get("id") or ""),
            expected_epoch=integer_value(lease.get("epoch")),
            old_head=old_value,
            new_head=new_value,
        )
    except ValueError as exc:
        gap = str(exc)
        return {
            **base,
            "ok": False,
            "state": "repair_required",
            "decision": {"action": "block", "reason": "lease_head_update_failed"},
            "required_gaps": [gap],
        }
    return {
        **base,
        "state": "lease_head_advanced",
        "lease": updated,
        "decision": {"action": "allow", "reason": "lease_head_advanced"},
    }


def _admit(
    *, phase: str, ref_name: str, old_value: str, new_value: str, reason: str
) -> dict[str, object]:
    """A lease-free admit payload for lane creation/teardown ref moves."""
    return {
        "ok": True,
        "state": "admitted",
        "phase": phase,
        "ref": ref_name,
        "branch": ref_name.removeprefix("refs/heads/"),
        "old_value": old_value,
        "new_value": new_value,
        "lease": {},
        "decision": {"action": "allow", "reason": reason},
        "required_gaps": [],
    }


def _work_lane_lease_transition_gaps(
    *, branch: str, lease: dict[str, object], actor: str, old_value: str
) -> list[str]:
    gaps: list[str] = []
    if not lease:
        return [f"work_lane_missing_lease:{branch}"]
    if str(lease.get("normalization_state") or "") != "normalized":
        gaps.append(f"lane_lease_legacy_ambiguous:{branch}")
    holder = str(lease.get("holder_ref") or "")
    if not holder or holder != actor:
        gaps.append(f"lease_holder_mismatch:{branch}")
    if not str(lease.get("lease_id") or "") or integer_value(lease.get("epoch")) < 1:
        gaps.append(f"lease_generation_missing:{branch}")
    expected_head = str(lease.get("expected_head") or "")
    if expected_head != old_value:
        gaps.append(f"lease_head_stale:{expected_head}!={old_value}")
    return gaps


def _control_state_db(status: dict[str, object], repo: Path) -> Path:
    for worktree in cast("list[dict[str, str]]", status.get("worktrees", [])):
        if worktree.get("role") == "accepted_root" and worktree.get("path"):
            return Path(worktree["path"]) / ".ethos" / "state" / "state.sqlite"
    return repo / ".ethos" / "state" / "state.sqlite"
