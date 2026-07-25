"""Effect-facing admission bridges for clean ownerless lane closeout."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
    OwnerlessCloseoutAdmissionError,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
    admit_ownerless_closeout,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
    admit_ownerless_closeout_facts,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
        OwnerlessCloseoutAdmission,
    )
    from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
        OwnerlessReceiptReservationContext,
    )
    from ethos_core.contracts.resolution.lane import LaneObservation


def _ownerless_gap(suffix: str) -> str:
    return f"lane_resolution_ownerless_{suffix}"


def admit_clean_ownerless_lane(
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
) -> OwnerlessCloseoutAdmission:
    """Translate canonical admission facts into one effect-facing closeout error."""
    try:
        return admit_ownerless_closeout(
            root=root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
        )
    except OwnerlessCloseoutAdmissionError as error:
        raise OwnerlessCloseoutError(error.gap) from error


def admit_ownerless_effect_target(
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
    receipt_reservation: OwnerlessReceiptReservationContext | None,
) -> OwnerlessCloseoutAdmission:
    """Admit one effect attempt while retaining any sidecar identity only locally."""
    try:
        if receipt_reservation is not None:
            return admit_ownerless_closeout_facts(
                root=root,
                decision_path=decision_path,
                decision=decision,
                executor_ref=executor_ref,
                receipt_reservation=receipt_reservation,
            )
        return admit_clean_ownerless_lane(
            root=root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
        )
    except OwnerlessCloseoutAdmissionError as error:
        raise OwnerlessCloseoutError(error.gap) from error
    except OwnerlessCloseoutError:
        raise
    except Exception as error:
        raise OwnerlessCloseoutError(_ownerless_gap("admission_unverifiable")) from error


def pre_admit_ownerless_lane(  # noqa: PLR0913, RUF100 - exact pre-admission facts
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    receipt_reservation: OwnerlessReceiptReservationContext | None = None,
) -> tuple[OwnerlessCloseoutAdmission | None, str]:
    """Admit an ownerless candidate with no sidecar or one local locked context."""
    if (
        disposition != "retire"
        or observation.dirty
        or not observation.orphan
        or observation.holder_ref
    ):
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
    else:
        return admission, ""
