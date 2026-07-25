"""Native ownerless retirement effect ownership."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution._shared import transition_gap
from ethos.adapters.mutation.resolution.closeout.effect import retire_clean_ownerless_lane

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
        OwnerlessCloseoutAdmission,
    )
    from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
        OwnerlessReceiptReservationContext,
    )
    from ethos_core.contracts.resolution.lane import LaneObservation


@dataclass(frozen=True, slots=True)
class OwnerlessCloseoutEffectContext:
    """Local fact and sidecar context for one ownerless closeout effect attempt."""

    admission: OwnerlessCloseoutAdmission | None
    receipt_reservation: OwnerlessReceiptReservationContext | None


def is_ownerless_closeout_candidate(disposition: str, observation: LaneObservation) -> bool:
    """Return whether the observed lane uses the native ownerless effect."""
    return (
        disposition == "retire"
        and not observation.dirty
        and observation.orphan
        and not observation.holder_ref
    )


def retire_ownerless_resolution(
    *,
    control_root: Path,
    decision_path: Path,
    decision: dict[str, object],
    artifact_root: Path,
    effect_context: OwnerlessCloseoutEffectContext | None = None,
) -> tuple[bool, str, dict[str, object]]:
    """Run the native ownerless effect and classify its durable recovery state."""
    executor_ref = os.environ.get("ETHOS_ACTOR", "").strip()
    if not executor_ref:
        return False, "lane_resolution_ownerless_executor_required", {}
    try:
        binding = retire_clean_ownerless_lane(
            root=control_root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
            artifact_root=artifact_root,
            admission=effect_context.admission if effect_context is not None else None,
            receipt_reservation=(
                effect_context.receipt_reservation if effect_context is not None else None
            ),
        )
    except OwnerlessCloseoutError as error:
        return (
            error.phase not in {None, "reserved"},
            transition_gap(error, "lane_resolution_ownerless_transition_unknown"),
            {},
        )
    return True, "", binding
