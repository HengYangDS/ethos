"""Fail-closed reset for natively admitted zero-effect ownerless retries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.records.reservations import (
    release_ownerless_no_effect_reservation,
)
from ethos.adapters.store.state.closeout import release_closeout_fence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.mutation.resolution.closeout.admission import OwnerlessCloseoutAdmission


def reset_reserved_no_effect_retry(
    *,
    admission: OwnerlessCloseoutAdmission,
    database: Path,
    record_root: Path,
) -> None:
    """Release only the old exact fence and reservation classified by admission."""
    reservation = admission.existing_reservation
    if reservation is None:
        return
    if admission.retry_fence_acquisition_id is not None:
        release_closeout_fence(
            database,
            subject=admission.observation.lane_ref,
            decision_id=admission.decision.decision_id,
            target_binding_digest=reservation.target_binding_digest,
        )
    release_ownerless_no_effect_reservation(
        root=admission.root,
        expected=reservation.to_payload(),
        artifact_root=record_root,
    )
