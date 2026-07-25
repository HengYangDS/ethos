"""Native ref-absent reconciliation of one owner-unavailable Work Lane lease."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation
import ethos.adapters.mutation.lane_retirement.unbound.policy.core as policy
import ethos.adapters.mutation.lane_retirement.unbound.records.core as records
import ethos.adapters.mutation.lane_retirement.unbound.reporting.core as reporting
from ethos.adapters.mutation.lane_retirement.unbound.core import relinquish_owned_lease
from ethos.adapters.repo.git import repository_root
from ethos.adapters.store.state.schema import initialize_state
from ethos.adapters.store.state.schema import state_database


@dataclass(frozen=True, slots=True)
class RefAbsentReconciliationControls:
    """Explicit controls for one lease-only ref-absent reconciliation."""

    reason: str = ""
    chronicle_ref: str = ""
    apply: bool = False
    authorized: bool = False
    break_glass: bool = False
    confirm_irreversible: bool = False

    def normalized(self) -> "RefAbsentReconciliationControls":
        """Trim only human-entered evidence references before observation."""
        return RefAbsentReconciliationControls(
            reason=self.reason.strip(),
            chronicle_ref=self.chronicle_ref.strip(),
            apply=self.apply,
            authorized=self.authorized,
            break_glass=self.break_glass,
            confirm_irreversible=self.confirm_irreversible,
        )

    @classmethod
    def confirmed(cls, *, reason: str) -> "RefAbsentReconciliationControls":
        """Return internal controls after the public apply admission has passed."""
        return cls(
            reason=reason,
            apply=True,
            authorized=True,
            break_glass=True,
            confirm_irreversible=True,
        )


def _data(**values: Any) -> dict[str, Any]:
    return values


def _write(path: Path, payload: dict[str, object], kind: str) -> tuple[str, str]:
    try:
        return records.write_record(path, payload, kind=kind), ""
    except (OSError, TypeError, ValueError) as exc:
        return "", records.stable_gap(exc)


def _blocked(result: dict[str, object], gaps: list[str], **context: object) -> dict[str, object]:
    return reporting.blocked(result | context, gaps)


def reconcile_ref_absent_owner_unavailable_lease(
    *, root: Path, branch: str, controls: RefAbsentReconciliationControls
) -> dict[str, object]:
    """Reconcile only the lease left after one exact ref-delete partial effect."""
    repo = repository_root(root)
    branch = branch.strip()
    controls = controls.normalized()
    before = observation.observe_ref_absent_reconciliation(
        repo, branch=branch, chronicle_ref=controls.chronicle_ref
    )
    holder_ref = lane_retirement_shared.current_holder_ref()
    source_attempt, attempt_gap = _partial_effect_attempt(before)
    gaps = _partial_effect_admission_gaps(
        before,
        controls=controls,
        holder_ref=holder_ref,
        source_attempt=source_attempt,
        attempt_gap=attempt_gap,
    )
    result = reporting.report(
        observed=before,
        chronicle_ref=controls.chronicle_ref,
        owner_unavailable_recovery=True,
        partial_effect_reconciliation=True,
        holder_ref=holder_ref,
        gaps=gaps,
        branch=branch,
        expect_head=str(before.get("head") or ""),
        reason=controls.reason,
        apply=controls.apply,
        authorized=controls.authorized,
        break_glass=controls.break_glass,
        confirm_irreversible=controls.confirm_irreversible,
    )
    if gaps or not controls.apply:
        return result
    return _apply_ref_absent_reconciliation(
        repo=repo,
        before=before,
        result=result,
        chronicle_ref=controls.chronicle_ref,
        holder_ref=holder_ref,
        source_attempt=source_attempt,
    )


def _partial_effect_attempt(observed: dict[str, object]) -> tuple[dict[str, object], str]:
    """Read the exact no-clobber attempt named by accepted reconciliation policy."""
    chronicle = cast("dict[str, object]", observed["chronicle"])
    attempt_id = str(chronicle.get("source_retirement_attempt_id") or "")
    status = cast("dict[str, object]", observed["status"])
    control_root, gap = policy.accepted_control_root(
        status, accepted_head=str(observed.get("accepted_head") or "")
    )
    if control_root is None:
        return {}, gap
    if not attempt_id.startswith("exceptional-unbound-retirement:"):
        return {}, "unbound_retire_partial_effect_attempt_mismatch"
    try:
        return (
            records.read_record(
                records.attempt_path(records.repository_records_root(control_root), attempt_id),
                kind=records.ATTEMPT_KIND,
            ),
            "",
        )
    except (OSError, TypeError, ValueError):
        return {}, "unbound_retire_partial_effect_attempt_missing"


def _partial_effect_admission_gaps(
    observed: dict[str, object],
    *,
    controls: RefAbsentReconciliationControls,
    holder_ref: str,
    source_attempt: dict[str, object],
    attempt_gap: str,
) -> list[str]:
    """Require explicit controls plus exact ref-absent residue bindings."""
    gaps = [attempt_gap] if attempt_gap else []
    if not controls.reason:
        gaps.append("retire_reason_required")
    if controls.apply and not controls.authorized:
        gaps.append("authorization_required")
    if controls.apply and not controls.break_glass:
        gaps.append("unbound_retire_requires_break_glass")
    if controls.apply and not controls.confirm_irreversible:
        gaps.append("irreversible_confirmation_required")
    protected = observed.get("protected_refs")
    if not isinstance(protected, dict) or not all(protected.values()):
        gaps.append("unbound_retire_protected_ref_unavailable")
    chronicle = cast("dict[str, object]", observed["chronicle"])
    target_head = str(chronicle.get("target_head") or "")
    gaps.extend(policy.chronicle_gaps(chronicle, branch=str(observed["branch"]), head=target_head))
    gaps.extend(
        policy.partial_effect_reconciliation_gaps(
            observed, recovery_actor=holder_ref, source_attempt=source_attempt
        )
    )
    return sorted(set(gaps))


def _apply_ref_absent_reconciliation(  # noqa: C901, PLR0911, PLR0912, PLR0913, RUF100 - exact CAS reconciliation under one sqlite transaction
    *,
    repo: Path,
    before: dict[str, object],
    result: dict[str, object],
    chronicle_ref: str,
    holder_ref: str,
    source_attempt: dict[str, object],
) -> dict[str, object]:
    """Recheck and revoke only the source lease retained by a failed ref delete."""
    control_root, gap = policy.accepted_control_root(
        cast("dict[str, object]", before["status"]), accepted_head=str(before["accepted_head"])
    )
    if control_root is None:
        return reporting.blocked(result, [gap])
    records_root = records.repository_records_root(repo)
    operation_id = records.reconciliation_operation_id(
        branch=str(before["branch"]),
        target_head=str(cast("dict[str, object]", before["chronicle"])["target_head"]),
        accepted_head=str(before["accepted_head"]),
        protected_refs=cast("dict[str, str]", before["protected_refs"]),
        claim_id=str(before["claim_id"]),
        chronicle=observation.chronicle_binding(before),
        source_retirement_attempt=source_attempt,
        reason=str(result["reason"]),
        observation_sha256=str(before["observation_sha256"]),
    )
    reconciliation_attempt = records.reconciliation_attempt_payload(
        operation_id=operation_id,
        reason=str(result["reason"]),
        observation=before,
        source_retirement_attempt=source_attempt,
    )
    attempt_path, write_gap = _write(
        records.reconciliation_attempt_path(records_root, operation_id),
        reconciliation_attempt,
        records.RECONCILIATION_ATTEMPT_KIND,
    )
    if write_gap:
        return reporting.blocked(result, [write_gap])
    context = _data(
        operation_id=operation_id,
        attempt_path=attempt_path,
        source_retirement_attempt=source_attempt,
    )
    try:
        database = state_database(repo)
        initialize_state(database)
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("pragma foreign_keys = on")
            connection.execute("begin immediate")
            current = observation.observe_ref_absent_reconciliation(
                repo, branch=str(before["branch"]), chronicle_ref=chronicle_ref
            )
            current_source_attempt, attempt_gap = _partial_effect_attempt(current)
            gaps = _partial_effect_admission_gaps(
                current,
                controls=RefAbsentReconciliationControls.confirmed(reason=str(result["reason"])),
                holder_ref=holder_ref,
                source_attempt=current_source_attempt,
                attempt_gap=attempt_gap,
            )
            if observation.public_observation(before) != observation.public_observation(current):
                gaps.append("unbound_retire_pre_effect_observation_stale")
            if gaps:
                connection.rollback()
                return _blocked(
                    result,
                    gaps,
                    **context,
                    observation=observation.public_observation(current),
                )
            lease_relinquished = relinquish_owned_lease(
                connection,
                observed=current,
                holder_ref=holder_ref,
                owner_unavailable_recovery=True,
            )
            if lease_relinquished is None:
                connection.rollback()
                return _blocked(result, ["unbound_retire_active_lease"], **context)
            connection.commit()
    except sqlite3.Error:
        return _blocked(result, ["unbound_retire_effect_failed"], **context)
    after = observation.observe_ref_absent_reconciliation(
        repo, branch=str(before["branch"]), chronicle_ref=chronicle_ref
    )
    post_gaps = []
    if str(after.get("head") or ""):
        post_gaps.append("unbound_retire_partial_effect_ref_reappeared")
    if str(after.get("worktree_binding") or "") != "absent":
        post_gaps.append("unbound_retire_partial_effect_worktree_reappeared")
    if bool(after[observation.HAS_ACTIVE_LEASE]):
        post_gaps.append("unbound_retire_active_lease")
    if before["protected_refs"] != after["protected_refs"]:
        post_gaps.append("unbound_retire_protected_refs_changed")
    if observation.chronicle_binding(before) != observation.chronicle_binding(after):
        post_gaps.append("unbound_retire_chronicle_changed")
    context |= _data(
        lease_relinquished=lease_relinquished,
        observation=observation.public_observation(after),
    )
    if post_gaps:
        return _blocked(result, post_gaps, **context)
    receipt = records.reconciliation_receipt_payload(
        operation_id=operation_id,
        branch=str(before["branch"]),
        target_head=str(cast("dict[str, object]", before["chronicle"])["target_head"]),
        reason=str(result["reason"]),
        before=before,
        after=after,
        source_retirement_attempt=source_attempt,
        chronicle_unchanged=observation.chronicle_binding(before)
        == observation.chronicle_binding(after),
        lease_relinquished=lease_relinquished,
    )
    receipt_path, write_gap = _write(
        records.reconciliation_receipt_path(records_root, operation_id),
        receipt,
        records.RECONCILIATION_RECEIPT_KIND,
    )
    if write_gap:
        return _blocked(result, [write_gap], **context)
    return (
        result
        | context
        | _data(
            ok=True,
            state="reconciled_ref_absent_owner_unavailable_lease",
            receipt_path=receipt_path,
            receipt=receipt,
            required_gaps=[],
            mutation=reporting.mutation(
                branch=str(before["branch"]),
                expect_head="",
                reason=str(result["reason"]),
                chronicle_ref=chronicle_ref,
                apply=True,
                confirmed=True,
                observed=after,
                break_glass=True,
                confirm_irreversible=True,
                owner_unavailable_recovery=True,
                partial_effect_reconciliation=True,
                holder_ref=holder_ref,
                gaps=[],
            ),
        )
    )
