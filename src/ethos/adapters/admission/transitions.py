"""Lease-bound Work Lane ref-transition admission."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ethos.adapters.admission.closeout_intent.marker import consume_closeout_intent
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.profile import load_profile_lease_bound_commitment
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.store.state.lease.lifecycle.transitions import advance_lease_head
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


def work_lane_ref_transition_report(
    *, root: Path, phase: str, ref_name: str, old_value: str, new_value: str
) -> dict[str, object]:
    """Check a prepared move or advance its lease after Git commits it."""
    branch = ref_name.removeprefix("refs/heads/")
    old_zero, new_zero = _is_zero_oid(old_value), _is_zero_oid(new_value)
    if old_value == new_value and not (old_zero or new_zero):
        return _admit(phase, ref_name, old_value, new_value, "lane_ref_noop")
    repo = root.resolve()
    if phase == "committed" and (
        (old_zero and ref_head(repo, branch) == new_value)
        or (new_zero and not ref_head(repo, branch))
    ):
        return _admit(phase, ref_name, old_value, new_value, "lane_ref_terminal_state_observed")
    lease = leases_by_branch(repo).get(branch, {})
    if not lease and new_zero:
        intent = consume_closeout_intent(
            root=repo,
            ref_name=ref_name,
            old_value=old_value,
            new_value=new_value,
        )
        if intent["present"] and not intent["gap"]:
            return _admit(phase, ref_name, old_value, new_value, "lane_ref_intent_admitted")
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    lease_head = new_value if old_zero else old_value
    target_head = old_value if new_zero else new_value
    gaps = _work_lane_lease_transition_gaps(
        repo,
        branch,
        lease,
        actor,
        lease_head,
        target_head,
    )
    reason = (
        "lane_creation_saga_started"
        if old_zero
        else "lane_teardown_ref_deletion"
        if new_zero
        else ""
    )
    base = _report(
        phase,
        ref_name,
        old_value,
        new_value,
        lease,
        gaps,
        reason if not gaps else "",
    )
    if gaps or phase != "committed" or old_zero or new_zero:
        return base
    try:
        updated = advance_lease_head(
            state_database(repo),
            request=LeaseOperationRequest(
                operation="advance",
                branch=branch,
                holder_ref=actor,
                lease_id=str(lease.get("lease_id") or lease.get("id") or ""),
                expected_epoch=integer_value(lease.get("epoch")),
                expect_head=old_value,
                expected_expires_at=str(lease.get("expires_at") or ""),
                expected_payload_sha256=str(lease.get("payload_sha256") or ""),
                apply=True,
            ),
            new_head=new_value,
        )
    except ValueError as exc:
        base.update(verdict="block", state="repair_required")
        base.update(decision={"action": "block", "reason": "lease_head_update_failed"})
        base["required_gaps"] = [str(exc)]
        return base
    base.update(state="lease_head_advanced", lease=updated)
    base["decision"] = {"action": "allow", "reason": "lease_head_advanced"}
    return base


def _is_zero_oid(value: str) -> bool:
    return len(value) in {40, 64} and not value.strip("0")


def _admit(
    phase: str, ref_name: str, old_value: str, new_value: str, reason: str
) -> dict[str, object]:
    return _report(phase, ref_name, old_value, new_value, {}, [], reason)


def _report(
    phase: str,
    ref_name: str,
    old_value: str,
    new_value: str,
    lease: dict[str, object],
    gaps: list[str],
    reason: str = "",
) -> dict[str, object]:
    verdict = _transition_verdict(gaps)
    report: dict[str, object] = {
        "verdict": verdict,
        "state": "admitted" if verdict == "pass" else verdict,
    }
    report.update(phase=phase, ref=ref_name, branch=ref_name.removeprefix("refs/heads/"))
    report.update(old_value=old_value, new_value=new_value, lease=lease)
    report["decision"] = {
        "action": "allow" if not gaps else "block",
        "reason": reason
        or ("work_lane_ref_transition_stale" if gaps else "work_lane_ref_transition_admitted"),
    }
    report["required_gaps"] = gaps
    return report


def _transition_verdict(gaps: list[str]) -> Verdict:
    if not gaps:
        return "pass"
    return "unknown" if all(gap.startswith("work_lane_lease_unknown:") for gap in gaps) else "block"


def _work_lane_lease_transition_gaps(
    root: Path,
    branch: str,
    lease: dict[str, object],
    actor: str,
    lease_head: str,
    target_head: str,
) -> list[str]:
    if not lease:
        return [f"work_lane_missing_lease:{branch}"]
    lease_state = str(lease.get("lease_state") or "missing")
    if lease_state != "valid":
        return [
            {
                "unknown": f"work_lane_lease_unknown:{branch}",
                "expired": f"work_lane_lease_expired:{branch}",
            }.get(lease_state, f"work_lane_missing_lease:{branch}")
        ]
    expected = str(lease.get("expected_head") or "")
    base_digest = str(lease.get("base_commitment_digest") or "")
    contract_gap = ""
    try:
        load_profile_lease_bound_commitment(
            root,
            expected_head=expected,
            base_commitment_digest=base_digest,
        )
        if openspec_profile_enabled(root):
            load_profile_lease_bound_commitment(
                root,
                expected_head=target_head,
                base_commitment_digest=base_digest,
            )
        else:
            load_commitment(
                root,
                tree_ref=target_head,
                expected_digest=base_digest,
            )
    except ValueError as exc:
        contract_gap = (
            "lease_base_commitment_digest_mismatch"
            if str(exc) == "commitment_digest_mismatch"
            else str(exc)
        )
    checks = (
        (
            not (holder := str(lease.get("holder_ref") or "")) or holder != actor,
            f"lease_holder_mismatch:{branch}",
        ),
        (
            not str(lease.get("lease_id") or "") or integer_value(lease.get("epoch")) < 1,
            f"lease_generation_missing:{branch}",
        ),
        (expected != lease_head, f"lease_head_stale:{expected}!={lease_head}"),
        (bool(contract_gap), contract_gap),
    )
    return [gap for failed, gap in checks if failed]
