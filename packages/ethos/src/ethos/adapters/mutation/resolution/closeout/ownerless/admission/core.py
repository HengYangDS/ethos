"""Canonical native admission API for clean ownerless Work Lane closeout."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.core as admission_facts
import ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.fence as admission_fence  # noqa: E501

if TYPE_CHECKING:
    from pathlib import Path


def admit_ownerless_closeout(
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
) -> admission_fence.OwnerlessCloseoutAdmission:
    """Admit one exact clean ownerless target using native repository facts."""
    try:
        return admission_facts.admit_ownerless_closeout_facts(
            root=root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
            receipt_reservation=None,
        )
    except admission_fence.OwnerlessCloseoutAdmissionError:
        raise
    except Exception as error:
        raise admission_fence.OwnerlessCloseoutAdmissionError(
            "lane_resolution_ownerless_admission_unverifiable", error.__class__.__name__
        ) from error


def reobserve_ownerless_closeout_under_fence(
    *, admission: admission_fence.OwnerlessCloseoutAdmission, fence: dict[str, object]
) -> admission_fence.OwnerlessCloseoutAdmission:
    """Require the exact fence before and after complete native re-observation."""
    try:
        return admission_facts.reobserve_ownerless_closeout_facts(
            admission=admission,
            fence=fence,
            receipt_reservation=None,
        )
    except admission_fence.OwnerlessCloseoutAdmissionError:
        raise
    except Exception as error:
        raise admission_fence.OwnerlessCloseoutAdmissionError(
            "lane_resolution_ownerless_admission_unverifiable", error.__class__.__name__
        ) from error
