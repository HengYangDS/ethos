"""Lease-bound Work Lane ref-transition admission."""

from __future__ import annotations

import os
from pathlib import Path

from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import worktree_records
from ethos.adapters.store.state.lease.lifecycle.core import advance_lease_head
from ethos.adapters.store.state.lease.projection import integer_value
from ethos_core.contracts.branch.roles import load_branch_role_policy

_ZERO_OID = "0" * 40


def work_lane_ref_transition_report(
    *, root: Path, phase: str, ref_name: str, old_value: str, new_value: str
) -> dict[str, object]:
    """Check a prepared move or advance its lease after Git commits it."""
    branch = ref_name.removeprefix("refs/heads/")
    if old_value == new_value:
        return _admit(phase, ref_name, old_value, new_value, "lane_ref_noop")
    if old_value in {_ZERO_OID, ""} or new_value in {_ZERO_OID, ""}:
        reason = (
            "lane_creation_saga_started"
            if old_value in {_ZERO_OID, ""}
            else "lane_teardown_ref_deletion"
        )
        return _admit(phase, ref_name, old_value, new_value, reason)
    repo = root.resolve()
    worktrees = worktree_records(repo, current_path=repo, policy=load_branch_role_policy(repo))
    lease = leases_by_branch(worktrees, current_path=repo).get(branch, {})
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    gaps = _work_lane_lease_transition_gaps(branch, lease, actor, old_value)
    base = _report(phase, ref_name, old_value, new_value, lease, gaps)
    if gaps or phase != "committed":
        return base
    try:
        updated = advance_lease_head(
            _control_state_db(worktrees, repo),
            subject=branch,
            holder_ref=actor,
            expected_lease_id=str(lease.get("lease_id") or lease.get("id") or ""),
            expected_epoch=integer_value(lease.get("epoch")),
            old_head=old_value,
            new_head=new_value,
        )
    except ValueError as exc:
        base.update(ok=False, state="repair_required")
        base.update(decision={"action": "block", "reason": "lease_head_update_failed"})
        base["required_gaps"] = [str(exc)]
        return base
    base.update(state="lease_head_advanced", lease=updated)
    base["decision"] = {"action": "allow", "reason": "lease_head_advanced"}
    return base


def _admit(
    phase: str, ref_name: str, old_value: str, new_value: str, reason: str
) -> dict[str, object]:
    return _report(phase, ref_name, old_value, new_value, {}, [], reason)


def _report(  # noqa: PLR0913, RUF100 - exact transition receipt dimensions
    phase: str,
    ref_name: str,
    old_value: str,
    new_value: str,
    lease: dict[str, object],
    gaps: list[str],
    reason: str = "",
) -> dict[str, object]:
    report: dict[str, object] = {"ok": not gaps, "state": "admitted" if not gaps else "blocked"}
    report.update(phase=phase, ref=ref_name, branch=ref_name.removeprefix("refs/heads/"))
    report.update(old_value=old_value, new_value=new_value, lease=lease)
    report["decision"] = {
        "action": "allow" if not gaps else "block",
        "reason": reason
        or ("work_lane_ref_transition_stale" if gaps else "work_lane_ref_transition_admitted"),
    }
    report["required_gaps"] = gaps
    return report


def _work_lane_lease_transition_gaps(
    branch: str, lease: dict[str, object], actor: str, old_value: str
) -> list[str]:
    if not lease:
        return [f"work_lane_missing_lease:{branch}"]
    expected = str(lease.get("expected_head") or "")
    checks = (
        (
            str(lease.get("normalization_state") or "") != "normalized",
            f"lane_lease_legacy_ambiguous:{branch}",
        ),
        (
            not (holder := str(lease.get("holder_ref") or "")) or holder != actor,
            f"lease_holder_mismatch:{branch}",
        ),
        (
            not str(lease.get("lease_id") or "") or integer_value(lease.get("epoch")) < 1,
            f"lease_generation_missing:{branch}",
        ),
        (expected != old_value, f"lease_head_stale:{expected}!={old_value}"),
    )
    return [gap for failed, gap in checks if failed]


def _control_state_db(worktrees: list[dict[str, str]], repo: Path) -> Path:
    accepted = next(
        (
            Path(item["path"])
            for item in worktrees
            if item.get("role") == "accepted_root" and item.get("path")
        ),
        repo,
    )
    return accepted / ".ethos/state/state.sqlite"
