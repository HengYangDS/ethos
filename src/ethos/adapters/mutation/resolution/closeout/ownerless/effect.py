"""Native ownerless retirement effect ownership."""

from __future__ import annotations

import os
from dataclasses import dataclass
from dataclasses import replace
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.closeout.receipt_recovery as cleanup
from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution.closeout.effect import retire_clean_ownerless_lane
from ethos.adapters.mutation.resolution.closeout.failure import classify_closeout_failure
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.fence import (
    OwnerlessCloseoutAdmissionError,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.observation import (
    admit_ownerless_closeout,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.reservation import (
    claim_effect_receipt_reservation,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.reservation import (
    claim_receipt_reservation,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.reservation import (
    ownerless_receipt_reservation_context,
)

if TYPE_CHECKING:
    from contextlib import ExitStack
    from pathlib import Path
    from typing import Any

    from ethos.adapters.mutation.resolution.closeout.ownerless.admission.fence import (
        OwnerlessCloseoutAdmission,
    )
    from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.reservation import (
        OwnerlessReceiptReservationContext,
    )
    from ethos.contracts.resolution.lane import LaneObservation


@dataclass(frozen=True, slots=True)
class OwnerlessCloseoutEffectContext:
    """Immutable execution context for one ownerless closeout attempt."""

    control_root: Path
    artifact_root: Path
    decision_path: Path
    decision: dict[str, Any]
    observation: LaneObservation
    disposition: str
    recover_receipt_reservation: bool
    admission: OwnerlessCloseoutAdmission | None
    receipt_reservation: OwnerlessReceiptReservationContext | None
    receipt_descriptor: int | None = None
    reservation: dict[str, object] | None = None


def _ownerless_gap(suffix: str) -> str:
    return f"lane_resolution_ownerless_{suffix}"


def is_ownerless_closeout_candidate(disposition: str, observation: LaneObservation) -> bool:
    """Return whether the observed lane uses the native ownerless effect."""
    return (
        disposition == "retire"
        and not observation.dirty
        and observation.orphan
        and not observation.holder_ref
    )


def admit_ownerless_effect_target(
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
    receipt_reservation: OwnerlessReceiptReservationContext | None,
) -> OwnerlessCloseoutAdmission:
    """Admit one effect attempt while retaining sidecar identity only locally."""
    try:
        return admit_ownerless_closeout(
            root=root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
            receipt_reservation=receipt_reservation,
        )
    except OwnerlessCloseoutAdmissionError as error:
        raise OwnerlessCloseoutError(error.gap) from error
    except OwnerlessCloseoutError:
        raise
    except Exception as error:
        raise OwnerlessCloseoutError(_ownerless_gap("admission_unverifiable")) from error


def pre_admit_ownerless_lane(
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    receipt_reservation: OwnerlessReceiptReservationContext | None = None,
) -> tuple[OwnerlessCloseoutAdmission | None, str]:
    """Admit an ownerless candidate with no sidecar or one local locked context."""
    if not is_ownerless_closeout_candidate(disposition, observation):
        return None, ""
    executor_ref = os.environ.get("ETHOS_ACTOR", "").strip()
    if not executor_ref:
        return None, _ownerless_gap("executor_required")
    try:
        admission = admit_ownerless_effect_target(
            root=root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
            receipt_reservation=receipt_reservation,
        )
    except OwnerlessCloseoutError as error:
        return None, str(error)
    return admission, ""


def claim_resolution_effect_attempt(
    *, stack: ExitStack, context: OwnerlessCloseoutEffectContext
) -> tuple[OwnerlessCloseoutEffectContext, tuple[str, ...]]:
    """Claim one receipt writer and retain its local ownerless sidecar context."""
    decision_id = str(context.decision.get("decision_id") or "")
    if context.recover_receipt_reservation:
        claimed, descriptor, gap = claim_receipt_reservation(
            stack,
            context.control_root,
            context.artifact_root,
            decision_id,
            mode="recover",
        )
        if gap or not claimed or descriptor is None:
            return (
                replace(context, receipt_descriptor=descriptor),
                (gap or "lane_resolution_receipt_invalid",),
            )
        receipt_reservation = None
        if is_ownerless_closeout_candidate(context.disposition, context.observation):
            try:
                receipt_reservation = ownerless_receipt_reservation_context(
                    control_root=context.control_root,
                    artifact_root=context.artifact_root,
                    decision_id=decision_id,
                    descriptor=descriptor,
                )
            except (OSError, TypeError, ValueError) as error:
                return (
                    replace(context, receipt_descriptor=descriptor),
                    (classify_closeout_failure(error, "lane_resolution_receipt_invalid"),),
                )
        admission, admission_gap = pre_admit_ownerless_lane(
            root=context.control_root,
            decision_path=context.decision_path,
            decision=context.decision,
            observation=context.observation,
            disposition=context.disposition,
            receipt_reservation=receipt_reservation,
        )
        return (
            replace(
                context,
                admission=admission,
                receipt_reservation=receipt_reservation,
                receipt_descriptor=descriptor,
            ),
            ((admission_gap,) if admission_gap else ()),
        )
    admission, admission_gap = pre_admit_ownerless_lane(
        root=context.control_root,
        decision_path=context.decision_path,
        decision=context.decision,
        observation=context.observation,
        disposition=context.disposition,
    )
    if admission_gap:
        return context, (admission_gap,)
    admission, descriptor, receipt_reservation, claim_gap = claim_effect_receipt_reservation(
        stack,
        context.control_root,
        context.artifact_root,
        decision_id,
        mode="create",
        admission=admission,
    )
    if not claim_gap:
        return (
            replace(
                context,
                admission=admission,
                receipt_reservation=receipt_reservation,
                receipt_descriptor=descriptor,
            ),
            (),
        )
    release_gap = (
        cleanup.release_receipt_reservation(
            control_root=context.control_root,
            artifact_root=context.artifact_root,
            decision_id=decision_id,
            locked_descriptor=descriptor,
        )
        if descriptor is not None
        else ""
    )
    return (
        replace(context, receipt_descriptor=descriptor),
        tuple(gap for gap in (claim_gap, release_gap) if gap),
    )


def retire_ownerless_resolution(
    *, context: OwnerlessCloseoutEffectContext
) -> tuple[bool, str, dict[str, object]]:
    """Run the native ownerless effect and classify its durable recovery state."""
    executor_ref = os.environ.get("ETHOS_ACTOR", "").strip()
    if not executor_ref:
        return False, "lane_resolution_ownerless_executor_required", {}
    try:
        binding = retire_clean_ownerless_lane(
            root=context.control_root,
            decision_path=context.decision_path,
            decision=context.decision,
            executor_ref=executor_ref,
            artifact_root=context.artifact_root,
            admission=context.admission,
            receipt_reservation=context.receipt_reservation,
        )
    except OwnerlessCloseoutError as error:
        return (
            error.phase not in {None, "reserved"},
            classify_closeout_failure(error, "lane_resolution_ownerless_transition_unknown"),
            {},
        )
    return True, "", binding
