"""Idempotent cleanup for receipt-complete ownerless closeout."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution._effects import recover_completed_ownerless_closeout
from ethos.adapters.mutation.resolution.receipts import exact_ownerless_resolution_receipt
from ethos.adapters.mutation.resolution.receipts import read_resolution_receipt
from ethos.adapters.mutation.resolution.records.core import ownerless_closeout_reservation_path
from ethos.adapters.mutation.resolution.records.core import release_ownerless_closeout_reservation
from ethos.adapters.store.state.closeout import probe_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos_core.contracts.resolution.lane import OwnerlessCloseoutBinding

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ethos.adapters.mutation.resolution.closeout.recovery import ResolutionRuntime
    from ethos_core.contracts.resolution.lane import LaneObservation

_OWNERLESS_RECEIPT_FIELDS = tuple(OwnerlessCloseoutBinding.model_fields)
_RECEIPT_MISMATCH = "lane_resolution_ownerless_receipt_mismatch"


def ownerless_receipt_recovery_context(  # noqa: PLR0913, RUF100 - exact receipt carrier
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
        return {}, _transition_gap(error, "lane_resolution_receipt_invalid")
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
        "schema_version": 1,
        "decision_id": str(decision["decision_id"]),
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        **typed_binding,
        "phase": "receipt",
        "recovery_state": "effect_complete_receipt_missing",
    }, ""


def recover_existing_ownerless_receipt(  # noqa: PLR0913, RUF100 - exact recovery envelope
    *,
    control_root: Path,
    artifact_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    reservation: dict[str, object],
    report: dict[str, object],
    runtime: ResolutionRuntime,
    chronicle_event: Callable[[dict[str, Any], dict[str, object] | None], dict[str, object]],
) -> bool:
    """Converge cleanup around one already durable exact receipt."""
    decision_id = str(decision.get("decision_id") or "")
    try:
        current = read_resolution_receipt(
            root=control_root,
            decision_id=decision_id,
            artifact_root=artifact_root,
            require_ownerless_closeout_binding=True,
        )
    except (OSError, TypeError, ValueError) as error:
        runtime.block_resolution_report(
            report,
            _transition_gap(error, "lane_resolution_receipt_invalid"),
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
        runtime.block_resolution_report(report, _RECEIPT_MISMATCH, state="partial_transition")
        return True
    executor_ref = os.environ.get("ETHOS_ACTOR", "").strip()
    if not executor_ref:
        runtime.block_resolution_report(
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
            observation=observation,
            executor_ref=executor_ref,
            reservation=reservation,
            receipt=receipt,
        )
    except OwnerlessCloseoutError as error:
        runtime.block_resolution_report(
            report,
            _transition_gap(error, "lane_resolution_ownerless_recovery_not_finalizable"),
            state="partial_transition",
        )
        return True
    if binding != expected_binding:
        runtime.block_resolution_report(report, _RECEIPT_MISMATCH, state="partial_transition")
    else:
        report.update(
            state=receipt["state"],
            preservation_package={},
            receipt=receipt,
            receipt_path=receipt_path,
            ownerless_closeout_binding=expected_binding,
            chronicle_event=chronicle_event(decision, receipt),
        )
        cleanup_gap = release_ownerless_closeout_resources(
            control_root=control_root,
            artifact_root=artifact_root,
            decision=decision,
            observation=observation,
            binding=binding,
            runtime=runtime,
        )
        if cleanup_gap:
            runtime.block_resolution_report(report, cleanup_gap, state="partial_transition")
        sidecar_gap = release_receipt_reservation(
            control_root=control_root,
            artifact_root=artifact_root,
            decision_id=decision_id,
            release_allowed=True,
            runtime=runtime,
        )
        if sidecar_gap:
            current_gaps = cast("list[str]", report["required_gaps"])
            runtime.block_resolution_report(
                report,
                *current_gaps,
                sidecar_gap,
                state="partial_transition",
            )
    return True


def release_ownerless_closeout_resources(  # noqa: PLR0913, RUF100 - exact CAS envelope
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    binding: dict[str, object],
    runtime: ResolutionRuntime,
) -> str:
    """Release an exact fence then its visible reservation; tolerate an absent fence."""
    expected = {
        "schema_version": 1,
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
            runtime.release_closeout_fence(
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
    release_allowed: bool,
    runtime: ResolutionRuntime,
) -> str:
    """Release the exact receipt sidecar unless a destructive effect is still partial."""
    if not release_allowed:
        return ""
    try:
        runtime.release_resolution_receipt_reservation(
            root=control_root,
            decision_id=decision_id,
            artifact_root=artifact_root,
        )
    except OSError:
        return "lane_resolution_receipt_reservation_release_failed"
    return ""


def _transition_gap(error: Exception, fallback: str) -> str:
    message = str(error).strip()
    return message if message.startswith(("lane_resolution_", "lane_closeout_")) else fallback
