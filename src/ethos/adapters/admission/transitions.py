"""Lease-bound Work Lane ref-transition admission."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.repo.git import ref_head
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


def work_lane_ref_transition_report(
    *, root: Path, phase: str, ref_name: str, old_value: str, new_value: str
) -> dict[str, object]:
    """Check a prepared Work Lane ref move; terminal phases only observe."""
    if not (_is_oid(old_value) and _is_oid(new_value)):
        return _report(
            phase,
            ref_name,
            old_value,
            new_value,
            {},
            ["work_lane_ref_oid_invalid"],
        )
    if phase in {"committed", "aborted"}:
        return _admit(phase, ref_name, old_value, new_value, f"{phase}_observed")
    return _prepared_work_lane_ref_transition_report(
        root=root,
        phase=phase,
        ref_name=ref_name,
        old_value=old_value,
        new_value=new_value,
    )


def _prepared_work_lane_ref_transition_report(
    *, root: Path, phase: str, ref_name: str, old_value: str, new_value: str
) -> dict[str, object]:
    """Admit one exact prepared Work Lane ref transition."""
    branch = ref_name.removeprefix("refs/heads/")
    old_zero, new_zero = _is_zero_oid(old_value), _is_zero_oid(new_value)
    repo = root.resolve()
    observed_ref = ref_head(repo, branch)
    immediate_reason = (
        "lane_ref_noop" if old_value == new_value and not (old_zero or new_zero) else ""
    )
    early = _early_transition_report(
        phase=phase,
        ref_name=ref_name,
        old_value=old_value,
        new_value=new_value,
        immediate_reason=immediate_reason,
    )
    if early is not None:
        return early
    observation = observe_lease(state_database(repo), branch)
    lease = {} if observation.state == "missing" else observation.record()
    update = GitRefUpdate(expected=old_value, desired=new_value)
    if report := _executor_intent_report(repo, phase, ref_name, update):
        return report
    if not lease:
        return _missing_lease_report(
            repo=repo,
            phase=phase,
            branch=branch,
            update=update,
            new_zero=new_zero,
        )
    expected_ref = "" if old_zero else old_value
    if lease.get("lease_state") == "valid" and observed_ref != expected_ref:
        return _report(
            phase,
            ref_name,
            old_value,
            new_value,
            {},
            [f"lane_ref_observation_stale:{expected_ref}!={observed_ref}"],
        )
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    gaps = _work_lane_ref_transition_gaps(
        branch,
        lease,
        actor,
    )
    if phase == "prepared" and new_zero and not gaps:
        intent = claim_ref_intent(
            root=repo,
            ref_name=ref_name,
            update=update,
            operation="lane.retire",
            phase="prepared",
        )
        if gap := str(intent["gap"] or ""):
            gaps.append(
                "work_lane_ref_delete_no_ref_intent" if gap == "ref_intent_missing" else gap
            )
    if phase == "prepared" and old_zero and not gaps:
        intent = claim_ref_intent(
            root=repo,
            ref_name=ref_name,
            update=update,
            operation="lane.start",
            phase="prepared",
        )
        if gap := str(intent["gap"] or ""):
            gaps.append(
                "work_lane_ref_create_no_ref_intent" if gap == "ref_intent_missing" else gap
            )
    reason = (
        "lane_creation_saga_started"
        if old_zero
        else "lane_teardown_ref_deletion"
        if new_zero
        else ""
    )
    return _report(
        phase,
        ref_name,
        old_value,
        new_value,
        lease,
        gaps,
        reason if not gaps else "",
    )


def _executor_intent_report(
    root: Path,
    phase: str,
    ref_name: str,
    update: GitRefUpdate,
) -> dict[str, object] | None:
    if phase != "prepared":
        return None
    intent = claim_ref_intent(
        root=root,
        ref_name=ref_name,
        update=update,
        operation="",
        phase="prepared",
    )
    if not intent.get("present") or intent.get("gap"):
        return None
    return _admit(
        phase,
        ref_name,
        update.expected,
        update.desired,
        "executor_ref_intent_admitted",
    )


def _early_transition_report(
    *,
    phase: str,
    ref_name: str,
    old_value: str,
    new_value: str,
    immediate_reason: str,
) -> dict[str, object] | None:
    if immediate_reason:
        return _admit(phase, ref_name, old_value, new_value, immediate_reason)
    return None


def _missing_lease_report(
    *,
    repo: Path,
    phase: str,
    branch: str,
    update: GitRefUpdate,
    new_zero: bool,
) -> dict[str, object]:
    ref_name = f"refs/heads/{branch}"
    operation = "lane.retire" if new_zero else "lane.retire.compensate"
    intent = (
        claim_ref_intent(
            root=repo,
            ref_name=ref_name,
            update=update,
            operation=operation,
            phase="prepared",
        )
        if phase == "prepared" and (new_zero or _is_zero_oid(update.expected))
        else {}
    )
    return (
        _admit(
            phase,
            ref_name,
            update.expected,
            update.desired,
            "lane_ref_intent_admitted",
        )
        if intent.get("present") and not intent.get("gap")
        else _report(
            phase,
            ref_name,
            update.expected,
            update.desired,
            {},
            [f"work_lane_missing_lease:{branch}"],
        )
    )


def _is_zero_oid(value: str) -> bool:
    return len(value) in {40, 64} and not value.strip("0")


def _is_oid(value: str) -> bool:
    return len(value) in {40, 64} and not set(value) - set("0123456789abcdef")


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
    return {
        "verdict": verdict,
        "state": "admitted" if verdict == "pass" else verdict,
        "phase": phase,
        "ref": ref_name,
        "branch": ref_name.removeprefix("refs/heads/"),
        "old_value": old_value,
        "new_value": new_value,
        "lease": lease,
        "decision": {
            "action": "allow" if not gaps else "block",
            "reason": reason
            or ("work_lane_ref_transition_stale" if gaps else "work_lane_ref_transition_admitted"),
        },
        "required_gaps": gaps,
    }


def _transition_verdict(gaps: list[str]) -> Verdict:
    if not gaps:
        return "pass"
    return "unknown" if all(gap.startswith("work_lane_lease_unknown:") for gap in gaps) else "block"


def _work_lane_ref_transition_gaps(
    branch: str,
    lease: dict[str, object],
    actor: str,
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
    checks = (
        (
            not (holder := str(lease.get("holder_ref") or "")) or holder != actor,
            f"lease_holder_mismatch:{branch}",
        ),
        (
            integer_value(lease.get("generation")) < 1,
            f"lease_generation_missing:{branch}",
        ),
    )
    return [gap for failed, gap in checks if failed]
