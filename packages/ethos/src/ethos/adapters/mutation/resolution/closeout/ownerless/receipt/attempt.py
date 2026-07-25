"""Descriptor-bound admission for one ownerless resolution effect attempt."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup
from ethos.adapters.mutation.resolution._shared import transition_gap
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.runtime import (
    pre_admit_ownerless_lane,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.effect import (
    is_ownerless_closeout_candidate,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
    claim_effect_receipt_reservation,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
    claim_receipt_reservation,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
    ownerless_receipt_reservation_context,
)

if TYPE_CHECKING:
    from contextlib import ExitStack
    from pathlib import Path
    from typing import Any

    from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
        OwnerlessCloseoutAdmission,
    )
    from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
        OwnerlessReceiptReservationContext,
    )
    from ethos_core.contracts.resolution.lane import LaneObservation


def claim_resolution_effect_attempt(  # noqa: PLR0913, RUF100 - exact claim/admission inputs
    *,
    stack: ExitStack,
    control_root: Path,
    artifact_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    recover: bool,
) -> tuple[
    OwnerlessCloseoutAdmission | None,
    int | None,
    OwnerlessReceiptReservationContext | None,
    tuple[str, ...],
]:
    """Claim one receipt writer and retain its local ownerless sidecar context."""
    decision_id = str(decision.get("decision_id") or "")
    if recover:
        claimed, descriptor, gap = claim_receipt_reservation(
            stack,
            control_root,
            artifact_root,
            decision_id,
            mode="recover",
        )
        if gap or not claimed or descriptor is None:
            return None, descriptor, None, (gap or "lane_resolution_receipt_invalid",)
        receipt_reservation = None
        if is_ownerless_closeout_candidate(disposition, observation):
            try:
                receipt_reservation = ownerless_receipt_reservation_context(
                    control_root=control_root,
                    artifact_root=artifact_root,
                    decision_id=decision_id,
                    descriptor=descriptor,
                )
            except (OSError, TypeError, ValueError) as error:
                return (
                    None,
                    descriptor,
                    None,
                    (transition_gap(error, "lane_resolution_receipt_invalid"),),
                )
        admission, admission_gap = pre_admit_ownerless_lane(
            root=control_root,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            disposition=disposition,
            receipt_reservation=receipt_reservation,
        )
        return (
            admission,
            descriptor,
            receipt_reservation,
            ((admission_gap,) if admission_gap else ()),
        )
    admission, admission_gap = pre_admit_ownerless_lane(
        root=control_root,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        disposition=disposition,
    )
    if admission_gap:
        return None, None, None, (admission_gap,)
    admission, descriptor, receipt_reservation, claim_gap = claim_effect_receipt_reservation(
        stack,
        control_root,
        artifact_root,
        decision_id,
        mode="create",
        admission=admission,
    )
    if not claim_gap:
        return admission, descriptor, receipt_reservation, ()
    release_gap = (
        cleanup.release_receipt_reservation(
            control_root=control_root,
            artifact_root=artifact_root,
            decision_id=decision_id,
            locked_descriptor=descriptor,
        )
        if descriptor is not None
        else ""
    )
    return None, descriptor, None, tuple(gap for gap in (claim_gap, release_gap) if gap)
