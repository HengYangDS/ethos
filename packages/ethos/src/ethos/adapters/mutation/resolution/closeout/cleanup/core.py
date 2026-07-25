"""Idempotent cleanup for receipt-complete ownerless closeout."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution._shared import transition_gap
from ethos.adapters.mutation.resolution.closeout.effect import recover_completed_ownerless_closeout
from ethos.adapters.mutation.resolution.receipts import chronicle_event
from ethos.adapters.mutation.resolution.receipts import exact_ownerless_resolution_receipt
from ethos.adapters.mutation.resolution.receipts import read_resolution_receipt
from ethos.adapters.mutation.resolution.records.core import release_resolution_receipt_reservation
from ethos.adapters.mutation.resolution.records.reservations import (
    ownerless_closeout_reservation_path,
)
from ethos.adapters.mutation.resolution.records.reservations import (
    read_ownerless_closeout_reservation,
)
from ethos.adapters.mutation.resolution.records.reservations import (
    release_ownerless_closeout_reservation,
)
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos.adapters.store.state.closeout import probe_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutBinding

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ethos_core.contracts.resolution.lane import LaneObservation

_OWNERLESS_RECEIPT_FIELDS = tuple(OwnerlessCloseoutBinding.model_fields)
_RECEIPT_MISMATCH = "lane_resolution_ownerless_receipt_mismatch"


def _block(report: dict[str, object], *gaps: str, state: str) -> None:
    report.update(
        ok=False,
        state=state,
        required_gaps=list(dict.fromkeys(gap for gap in gaps if gap)),
    )


def ownerless_receipt_recovery_context(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
) -> tuple[dict[str, object], str]:
    """Recover a deleted reservation only from one exact immutable receipt."""
    try:
        current = read_resolution_receipt(
            root=control_root,
            decision_id=str(decision.get("decision_id") or ""),
            artifact_root=artifact_root,
            require_ownerless_closeout_binding=True,
        )
    except (OSError, TypeError, ValueError) as error:
        return {}, transition_gap(error, "lane_resolution_receipt_invalid")
    if current is None:
        return {}, ""
    receipt, _receipt_path = current
    binding = receipt.get("ownerless_closeout_binding")
    if not isinstance(binding, dict):
        return {}, _RECEIPT_MISMATCH
    typed_binding = cast("dict[str, object]", binding)
    if not exact_ownerless_resolution_receipt(
        receipt=receipt,
        decision=decision,
        observation=observation,
        expected_binding=typed_binding,
    ):
        return {}, _RECEIPT_MISMATCH
    return {
        "schema_version": 2,
        "decision_id": str(decision["decision_id"]),
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        **typed_binding,
        "phase": "receipt",
        "recovery_state": "effect_complete_receipt_missing",
    }, ""


def ownerless_reservation_recovery_context(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    receipt_recovery: dict[str, object],
) -> tuple[dict[str, object], str]:
    """Reconcile one exact typed reservation with optional receipt recovery."""
    reservation_path = ownerless_closeout_reservation_path(
        control_root,
        target_digest(observation.lane_ref, observation.head),
        artifact_root=artifact_root,
    )
    if not reservation_path.exists() and not reservation_path.is_symlink():
        return receipt_recovery, ""
    try:
        reservation = read_ownerless_closeout_reservation(
            record_root=artifact_root,
            path=reservation_path,
        )
    except (OSError, TypeError, ValueError) as error:
        return {}, transition_gap(error, "lane_resolution_ownerless_reservation_invalid")
    exact = (
        reservation.get("decision_id") == decision.get("decision_id")
        and reservation.get("lane_ref") == observation.lane_ref
        and reservation.get("head") == observation.head
    )
    if not exact:
        return reservation, "lane_resolution_ownerless_recovery_binding_mismatch"
    if receipt_recovery and reservation != receipt_recovery:
        return reservation, "lane_resolution_ownerless_receipt_mismatch"
    recovery_state = str(reservation["recovery_state"])
    if recovery_state not in {"reserved_no_effect", "effect_complete_receipt_missing"}:
        return reservation, f"lane_resolution_ownerless_reconciliation_required:{recovery_state}"
    return reservation, ""


def recover_existing_ownerless_receipt(  # noqa: PLR0913, RUF100 - exact recovery inputs
    *,
    control_root: Path,
    artifact_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    reservation: dict[str, object],
    report: dict[str, object],
    decision_bytes: bytes,
    require_decision_current: Callable[[], None],
) -> bool:
    """Validate one durable receipt and perform only idempotent cleanup."""
    decision_id = str(decision.get("decision_id") or "")
    try:
        current = read_resolution_receipt(
            root=control_root,
            decision_id=decision_id,
            artifact_root=artifact_root,
            require_ownerless_closeout_binding=True,
        )
    except (OSError, TypeError, ValueError) as error:
        _block(
            report,
            transition_gap(error, "lane_resolution_receipt_invalid"),
            state="partial_transition",
        )
        return True
    if current is None:
        return False
    receipt, receipt_path = current
    expected_binding = {field: reservation[field] for field in _OWNERLESS_RECEIPT_FIELDS}
    if not exact_ownerless_resolution_receipt(
        receipt=receipt,
        decision=decision,
        observation=observation,
        expected_binding=expected_binding,
    ):
        _block(report, _RECEIPT_MISMATCH, state="partial_transition")
        return True
    executor_ref = os.environ.get("ETHOS_ACTOR", "").strip()
    if not executor_ref:
        _block(
            report,
            "lane_resolution_ownerless_executor_required",
            state="partial_transition",
        )
        return True
    try:
        binding = recover_completed_ownerless_closeout(
            root=control_root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
            reservation=reservation,
            receipt=receipt,
            decision_bytes=decision_bytes,
        )
        require_decision_current()
    except OwnerlessCloseoutError as error:
        _block(
            report,
            transition_gap(error, "lane_resolution_ownerless_recovery_not_finalizable"),
            state="partial_transition",
        )
        return True
    if binding != expected_binding:
        _block(report, _RECEIPT_MISMATCH, state="partial_transition")
    else:
        report.update(
            state=receipt["state"],
            preservation_package={},
            receipt=receipt,
            receipt_path=receipt_path,
            ownerless_closeout_binding=expected_binding,
            chronicle_event=chronicle_event(decision, receipt),
        )
        if cleanup_gap := release_ownerless_closeout_resources(
            control_root=control_root,
            artifact_root=artifact_root,
            decision=decision,
            observation=observation,
            binding=binding,
        ):
            _block(report, cleanup_gap, state="partial_transition")
    return True


def release_ownerless_closeout_resources(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    binding: dict[str, object],
) -> str:
    """Release the exact fence before removing the visible reservation."""
    expected = {
        "schema_version": 2,
        "decision_id": str(decision.get("decision_id") or ""),
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        **{
            field: binding[field]
            for field in _OWNERLESS_RECEIPT_FIELDS
            if field != "postcondition_digest"
        },
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }
    database = state_database(control_root)
    try:
        try:
            release_closeout_fence(
                database,
                subject=observation.lane_ref,
                decision_id=str(decision.get("decision_id") or ""),
                target_binding_digest=str(binding["target_binding_digest"]),
            )
        except ValueError as error:
            fence_state, _fence = probe_closeout_fence(database, subject=observation.lane_ref)
            stale = str(error).startswith("lane_closeout_fence_release_stale:")
            if not stale or fence_state != "absent":
                raise
        reservation_path = ownerless_closeout_reservation_path(
            control_root,
            str(binding["target_digest"]),
            artifact_root=artifact_root,
        )
        if not reservation_path.exists() and not reservation_path.is_symlink():
            return ""
        release_ownerless_closeout_reservation(
            root=control_root,
            expected=expected,
            artifact_root=artifact_root,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return "lane_resolution_ownerless_cleanup_failed"
    return ""


def release_receipt_reservation(
    *,
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    locked_descriptor: int | None,
) -> str:
    """Release the exact descriptor-bound receipt sidecar."""
    if locked_descriptor is None:
        return ""
    try:
        release_resolution_receipt_reservation(
            root=control_root,
            decision_id=decision_id,
            artifact_root=artifact_root,
            locked_descriptor=locked_descriptor,
        )
    except (OSError, ValueError):
        return "lane_resolution_receipt_reservation_release_failed"
    return ""
