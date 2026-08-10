"""Lease-bound Work Lane ref-transition admission."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.openspec.lifecycle.archive_transition import (
    lease_bound_archive_transition_fields,
)
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import rebind_target_fields
from ethos.adapters.repo.commitment import relocated_commitment_fields
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import advance_lease_ref
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import GitRefUpdate
from ethos.repository.openspec.identifiers import malformed_change_identity_repair_valid

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


def work_lane_ref_transition_report(
    *, root: Path, phase: str, ref_name: str, old_value: str, new_value: str
) -> dict[str, object]:
    """Check a prepared move or advance its lease after Git commits it."""
    branch = ref_name.removeprefix("refs/heads/")
    if not (_is_oid(old_value) and _is_oid(new_value)):
        return _report(
            phase,
            ref_name,
            old_value,
            new_value,
            {},
            ["work_lane_ref_oid_invalid"],
        )
    old_zero, new_zero = _is_zero_oid(old_value), _is_zero_oid(new_value)
    repo = root.resolve()
    observed_ref = ref_head(repo, branch)
    immediate_reason = (
        "lane_ref_noop"
        if old_value == new_value and not (old_zero or new_zero) and phase != "committed"
        else "lane_ref_terminal_state_observed"
        if _committed_ref_effect_observed(
            phase=phase,
            old_zero=old_zero,
            new_zero=new_zero,
            observed_ref=observed_ref,
            new_value=new_value,
        )
        else ""
    )
    early = _early_transition_report(
        repo=repo,
        phase=phase,
        ref_name=ref_name,
        old_value=old_value,
        new_value=new_value,
        immediate_reason=immediate_reason,
    )
    if early is not None:
        return early
    lease = leases_by_branch(repo).get(branch, {})
    update = GitRefUpdate(expected=old_value, desired=new_value)
    if not lease:
        return _missing_lease_report(
            repo=repo,
            phase=phase,
            branch=branch,
            update=update,
            new_zero=new_zero,
        )
    expected_ref = (
        ""
        if (phase == "prepared" and old_zero) or (phase == "committed" and new_zero)
        else new_value
        if phase == "committed"
        else old_value
    )
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
    lease_head = new_value if old_zero else old_value
    target_head = old_value if new_zero else new_value
    gaps, target = _work_lane_ref_transition_facts(
        repo,
        branch,
        lease,
        actor,
        lease_head,
        target_head,
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
    report = _commitment_rebind_report(
        repo=repo,
        phase=phase,
        update=update,
        lease=lease,
        target=target,
        gaps=gaps,
        terminal=old_zero or new_zero,
    )
    if report is not None:
        base = report
        advance = False
    else:
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
        advance = not gaps and phase == "committed" and not (old_zero or new_zero)
    return (
        _advance_ref_lease(
            repo=repo,
            branch=branch,
            actor=actor,
            lease=lease,
            old_value=old_value,
            target=target,
            report=base,
        )
        if advance
        else base
    )


def _early_transition_report(
    *,
    repo: Path,
    phase: str,
    ref_name: str,
    old_value: str,
    new_value: str,
    immediate_reason: str,
) -> dict[str, object] | None:
    if immediate_reason:
        return _admit(phase, ref_name, old_value, new_value, immediate_reason)
    guard = local_state_mutation_guard(repo) if phase == "prepared" else {"required_gaps": []}
    gaps = cast("list[str]", guard["required_gaps"])
    if not gaps:
        return None
    report = _report(phase, ref_name, old_value, new_value, {}, gaps)
    report["next_action"] = guard["next_action"]
    return report


def _advance_ref_lease(
    *,
    repo: Path,
    branch: str,
    actor: str,
    lease: dict[str, object],
    old_value: str,
    target: dict[str, str],
    report: dict[str, object],
) -> dict[str, object]:
    try:
        updated = advance_lease_ref(
            state_database(repo),
            request=LeaseOperationRequest(
                operation="advance",
                branch=branch,
                holder_ref=actor,
                lease_id=str(lease.get("lease_id") or ""),
                expected_epoch=integer_value(lease.get("epoch")),
                expect_head=old_value,
                expected_expires_at=str(lease.get("expires_at") or ""),
                expected_payload_sha256=str(lease.get("payload_sha256") or ""),
                apply=True,
            ),
            binding=target,
        )
    except ValueError as exc:
        report.update(verdict="block", state="repair_required")
        report.update(decision={"action": "block", "reason": "lease_ref_update_failed"})
        report["required_gaps"] = [str(exc)]
        return report
    report.update(state="lease_ref_advanced", lease=updated)
    report["decision"] = {"action": "allow", "reason": "lease_ref_advanced"}
    return report


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


def _commitment_rebind_report(
    *,
    repo: Path,
    phase: str,
    update: GitRefUpdate,
    lease: dict[str, object],
    target: dict[str, str],
    gaps: list[str],
    terminal: bool,
) -> dict[str, object] | None:
    if terminal or not gaps or any(gap not in _COMMITMENT_REBIND_GAPS for gap in gaps):
        return None
    ref_name = f"refs/heads/{lease.get('lane_ref') or ''}"
    intent = claim_ref_intent(
        root=repo,
        ref_name=ref_name,
        update=update,
        operation=_rebind_operation(repo, update, lease, target),
        phase=cast(
            "Literal['prepared', 'committed', 'aborted']",
            {"committed": "committed", "aborted": "aborted"}.get(phase, "prepared"),
        ),
    )
    gap = str(intent["gap"] or "")
    if gap:
        if gap != "ref_intent_missing":
            gaps[:] = [gap]
        return None
    if gap := _commitment_rebind_gap(
        repo,
        lease,
        target,
        old_value=update.expected,
        new_value=update.desired,
    ):
        gaps[:] = [gap]
        return None
    reason = {
        "committed": "commitment_rebind_pending",
        "aborted": "commitment_rebind_aborted",
    }.get(phase, "commitment_rebind_admitted")
    report = _admit(phase, ref_name, update.expected, update.desired, reason)
    if phase == "committed":
        report["state"] = "commitment_rebind_pending"
    return report


def _rebind_operation(
    repo: Path,
    update: GitRefUpdate,
    lease: dict[str, object],
    target: dict[str, str],
) -> str:
    try:
        old = load_lease_bound_commitment(repo, lease=lease)
        target = rebind_target_fields(
            repo, old_head=update.expected, new_head=update.desired, commitment=old, target=target
        )
        new = load_commitment(
            repo,
            carrier=target["base_commitment_path"],
            tree_ref=update.desired,
            expected_digest=target["base_commitment_digest"],
        )
    except (KeyError, ValueError):
        return "commitment.rebind"
    return "change.identity-repair" if old.id != new.id else "commitment.rebind"


_COMMITMENT_REBIND_GAPS = frozenset(
    {
        "lease_base_commitment_path_mismatch",
        "lease_base_commitment_bytes_mismatch",
        "lease_base_commitment_digest_mismatch",
    }
)


def _commitment_rebind_gap(
    root: Path,
    lease: dict[str, object],
    target: dict[str, str],
    *,
    old_value: str,
    new_value: str,
) -> str:
    """Validate one semantic Work Lane ref move against live immutable facts."""
    try:
        old_commitment = load_lease_bound_commitment(root, lease=lease)
        target = rebind_target_fields(
            root,
            old_head=old_value,
            new_head=new_value,
            commitment=old_commitment,
            target=target,
        )
        new_commitment = load_commitment(
            root,
            carrier=target["base_commitment_path"],
            tree_ref=new_value,
            expected_digest=target["base_commitment_digest"],
        )
        parents = run_git(root, "rev-list", "--parents", "-n", "1", new_value).stdout.split()
        checks = (
            (parents == [new_value, old_value], "commitment_rebind_target_parent_mismatch"),
            (
                run_git(root, "write-tree").stdout.strip() == target["expected_tree"],
                "commitment_rebind_index_tree_mismatch",
            ),
            (
                new_commitment.id == old_commitment.id
                or malformed_change_identity_repair_valid(
                    carrier=target["base_commitment_path"],
                    old_id=old_commitment.id,
                    old_digest=old_commitment.digest(),
                    new=new_commitment,
                ),
                "commitment_rebind_identity_mismatch",
            ),
            (
                new_commitment.digest() != old_commitment.digest(),
                "commitment_rebind_semantics_unchanged",
            ),
        )
    except (KeyError, ValueError) as error:
        return str(error)
    return next((gap for valid, gap in checks if not valid), "")


def _is_zero_oid(value: str) -> bool:
    return len(value) in {40, 64} and not value.strip("0")


def _is_oid(value: str) -> bool:
    return len(value) in {40, 64} and not set(value) - set("0123456789abcdef")


def _committed_ref_effect_observed(
    *, phase: str, old_zero: bool, new_zero: bool, observed_ref: str, new_value: str
) -> bool:
    return phase == "committed" and (
        (old_zero and observed_ref == new_value) or (new_zero and not observed_ref)
    )


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


def _work_lane_ref_transition_facts(
    root: Path,
    branch: str,
    lease: dict[str, object],
    actor: str,
    lease_head: str,
    target_head: str,
) -> tuple[list[str], dict[str, str]]:
    if not lease:
        return [f"work_lane_missing_lease:{branch}"], {}
    lease_state = str(lease.get("lease_state") or "missing")
    if lease_state != "valid":
        return [
            {
                "unknown": f"work_lane_lease_unknown:{branch}",
                "expired": f"work_lane_lease_expired:{branch}",
            }.get(lease_state, f"work_lane_missing_lease:{branch}")
        ], {}
    expected = str(lease.get("expected_head") or "")
    target: dict[str, str] = {}
    contract_gap = ""
    try:
        load_lease_bound_commitment(root, lease=lease)
        try:
            target = exact_commitment_fields(
                root,
                head=target_head,
                carrier=str(lease.get("base_commitment_path") or ""),
            )
        except ValueError as exc:
            if str(exc) != "commitment_carrier_missing":
                raise
            try:
                target = relocated_commitment_fields(
                    root,
                    old_head=expected,
                    new_head=target_head,
                    lease=lease,
                )
            except ValueError:
                target = lease_bound_archive_transition_fields(root, target_head=target_head) or {}
                if not target:
                    raise
        mismatch = next(
            (
                name
                for name in ("base_commitment_bytes_sha256", "base_commitment_digest")
                if target[name] != str(lease.get(name) or "")
            ),
            "",
        )
        contract_gap = {
            "base_commitment_bytes_sha256": "lease_base_commitment_bytes_mismatch",
            "base_commitment_digest": "lease_base_commitment_digest_mismatch",
        }.get(mismatch, "")
    except ValueError as exc:
        fallback = (
            str(exc) if str(exc).startswith("lease_") else "lease_base_commitment_digest_mismatch"
        )
        contract_gap = {
            "commitment_carrier_path_invalid": "lease_base_commitment_path_mismatch",
            "commitment_carrier_missing": "lease_base_commitment_path_mismatch",
            "commitment_head_unreadable": "lease_expected_tree_mismatch",
        }.get(str(exc), fallback)
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
    return [gap for failed, gap in checks if failed], target
