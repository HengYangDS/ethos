"""Fail-closed reset for natively admitted zero-effect ownerless retries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.fence import (
    ownerless_retry_fence,
)
from ethos.adapters.mutation.resolution.records.reservations import (
    release_ownerless_no_effect_reservation,
)
from ethos.adapters.store.state.closeout import probe_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence

_OWNERLESS_FENCE_STALE = "lane_resolution_ownerless_fence_stale"
_OWNERLESS_FENCE_UNVERIFIABLE = "lane_resolution_ownerless_fence_unverifiable"

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.fence import (
        OwnerlessCloseoutAdmission,
    )


def reset_reserved_no_effect_retry(
    *,
    admission: OwnerlessCloseoutAdmission,
    database: Path,
    record_root: Path,
) -> None:
    """Reobserve and release only the old exact fence and reservation."""
    reservation = admission.existing_reservation
    if reservation is None:
        return
    state, fence = probe_closeout_fence(database, subject=admission.observation.lane_ref)
    if state == "unverifiable":
        raise ValueError(_OWNERLESS_FENCE_UNVERIFIABLE)
    if state == "present":
        payload = fence.get("payload") if isinstance(fence, dict) else None
        acquisition_id = payload.get("acquisition_id") if isinstance(payload, dict) else None
        if type(acquisition_id) is not str:
            raise ValueError(_OWNERLESS_FENCE_STALE)
        expected_fence = ownerless_retry_fence(
            admission=admission,
            reservation=reservation,
            acquisition_id=acquisition_id,
        )
        if fence != expected_fence:
            raise ValueError(_OWNERLESS_FENCE_STALE)
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
