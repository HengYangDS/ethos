"""Fail-closed native effects and recovery for clean ownerless Work Lanes."""

from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution._effects import ref_head
from ethos.adapters.mutation.resolution._effects import retire_clean_ownerless_cas
from ethos.adapters.mutation.resolution._effects import verify_ownerless_postconditions
from ethos.adapters.mutation.resolution._shared import current_chronicle_matches
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
    OwnerlessCloseoutAdmission,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
    OwnerlessCloseoutAdmissionError,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
    admit_ownerless_closeout,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
    reobserve_ownerless_closeout_under_fence,
)
from ethos.adapters.mutation.resolution.closeout.retry import reset_reserved_no_effect_retry
from ethos.adapters.mutation.resolution.receipts import canonical_resolution_decision_snapshot
from ethos.adapters.mutation.resolution.receipts import canonical_resolution_payload_digest
from ethos.adapters.mutation.resolution.receipts import exact_ownerless_resolution_receipt
from ethos.adapters.mutation.resolution.records.reservations import (
    reserve_ownerless_closeout_target,
)
from ethos.adapters.mutation.resolution.records.reservations import (
    transition_ownerless_closeout_reservation,
)
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.store.state.closeout import acquire_closeout_fence
from ethos.adapters.store.state.closeout import probe_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutBinding
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
        OwnerlessReceiptReservationToken,
    )

_OWNERLESS_ACCEPTED_HEAD_STALE = "lane_resolution_ownerless_accepted_head_stale"
_OWNERLESS_CHRONICLE_STALE = "lane_resolution_ownerless_chronicle_stale"
_OWNERLESS_DECISION_STALE = "lane_resolution_ownerless_decision_stale"
_OWNERLESS_FENCE_STALE = "lane_resolution_ownerless_fence_stale"
_OWNERLESS_FENCE_UNVERIFIABLE = "lane_resolution_ownerless_fence_unverifiable"
_OWNERLESS_RECEIPT_MISMATCH = "lane_resolution_ownerless_receipt_mismatch"


def _ownerless_gap(suffix: str) -> str:
    return f"lane_resolution_ownerless_{suffix}"


def admit_clean_ownerless_lane(
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
    receipt_reservation_token: OwnerlessReceiptReservationToken | None = None,
) -> OwnerlessCloseoutAdmission:
    try:
        return admit_ownerless_closeout(
            root=root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
            receipt_reservation_token=receipt_reservation_token,
        )
    except OwnerlessCloseoutAdmissionError as error:
        raise OwnerlessCloseoutError(error.gap) from error


def pre_admit_ownerless_lane(  # noqa: PLR0913, RUF100 - exact pre-admission facts
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    receipt_reservation_token: OwnerlessReceiptReservationToken | None = None,
) -> tuple[OwnerlessCloseoutAdmission | None, str]:
    """Admit an ownerless candidate with no sidecar or one exact locked token."""
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
        return (
            admit_clean_ownerless_lane(
                root=root,
                decision_path=decision_path,
                decision=decision,
                executor_ref=executor_ref,
                receipt_reservation_token=receipt_reservation_token,
            ),
            "",
        )
    except OwnerlessCloseoutError as error:
        return None, str(error)


def retire_clean_ownerless_lane(  # noqa: PLR0913, RUF100 - exact effect bindings
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
    artifact_root: Path | None = None,
    admission: OwnerlessCloseoutAdmission | None = None,
) -> dict[str, object]:
    """Admit, fence, reobserve, reserve, retire, and bind one exact target."""
    if admission is None:
        admission = admit_clean_ownerless_lane(
            root=root,
            decision_path=decision_path,
            decision=decision,
            executor_ref=executor_ref,
        )
    record_root = artifact_root or current_record_root(admission.root)
    database = state_database(admission.root)
    if admission.existing_reservation is not None:
        try:
            reset_reserved_no_effect_retry(
                admission=admission,
                database=database,
                record_root=record_root,
            )
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            gap = str(error).strip()
            raise OwnerlessCloseoutError(
                gap
                if gap.startswith(("lane_resolution_", "lane_closeout_"))
                else _ownerless_gap("retry_reset_failed"),
                phase="reserved",
                recovery_state="reserved_no_effect",
            ) from error
        admission = replace(
            admission,
            existing_reservation=None,
            retry_fence_acquisition_id=None,
        )
    fence = _acquire_fresh_fence(admission, database)
    try:
        admission = reobserve_ownerless_closeout_under_fence(
            admission=admission,
            fence=fence,
        )
    except OwnerlessCloseoutAdmissionError as error:
        _release_unreserved_fence(admission, database, fence)
        raise OwnerlessCloseoutError(error.gap) from error
    reservation = _reservation(admission, fence)
    try:
        reserve_ownerless_closeout_target(
            root=admission.root,
            reservation=reservation,
            artifact_root=record_root,
        )
    except (OSError, TypeError, ValueError) as error:
        _release_unreserved_fence(admission, database, fence)
        raise OwnerlessCloseoutError(_ownerless_gap("reservation_failed")) from error
    try:
        retire_clean_ownerless_cas(
            root=admission.root,
            observation=admission.observation,
            accepted_branch=admission.accepted_branch,
            accepted_head=admission.accepted_head,
        )
        postconditions = verify_ownerless_postconditions(
            root=admission.root,
            database=database,
            decision_path=admission.decision_path,
            decision_sha256=admission.decision_sha256,
            observation=admission.observation,
            accepted_branch=admission.accepted_branch,
            accepted_head=admission.accepted_head,
            fence=fence,
        )
    except OwnerlessCloseoutError as error:
        _record_ownerless_partial(
            root=admission.root,
            artifact_root=record_root,
            reservation=reservation,
            error=error,
        )
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        transition = OwnerlessCloseoutError(
            _ownerless_gap("transition_unknown"),
            phase="unknown",
            recovery_state="transition_unknown",
        )
        _record_ownerless_partial(
            root=admission.root,
            artifact_root=record_root,
            reservation=reservation,
            error=transition,
        )
        raise transition from error
    postcondition_digest = canonical_resolution_payload_digest(postconditions)
    try:
        transition_ownerless_closeout_reservation(
            root=admission.root,
            expected=reservation,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
            postcondition_digest=postcondition_digest,
            artifact_root=record_root,
        )
    except (OSError, TypeError, ValueError) as error:
        raise OwnerlessCloseoutError(
            _ownerless_gap("reservation_update_failed"),
            phase="unknown",
            recovery_state="transition_unknown",
        ) from error
    return OwnerlessCloseoutBinding(
        executor_ref=admission.executor_ref,
        decision_sha256=admission.decision_sha256,
        accepted_branch=admission.accepted_branch,
        accepted_head=admission.accepted_head,
        target_digest=admission.target_digest,
        target_binding_digest=str(fence["target_binding_digest"]),
        postcondition_digest=postcondition_digest,
    ).model_dump(mode="json")


def _acquire_fresh_fence(
    admission: OwnerlessCloseoutAdmission, database: Path
) -> dict[str, object]:
    try:
        return acquire_closeout_fence(
            database,
            subject=admission.observation.lane_ref,
            expected_head=admission.observation.head,
            decision_id=admission.decision.decision_id,
            executor_ref=admission.executor_ref,
            accepted_branch=admission.accepted_branch,
            accepted_head=admission.accepted_head,
            target_path=admission.observation.path,
            lane_incarnation_id=admission.observation.lane_incarnation_id,
            observation_digest=admission.observation.digest(),
            decision_sha256=admission.decision_sha256,
            chronicle_digest=admission.decision.chronicle_digest,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        gap = str(error).strip()
        raise OwnerlessCloseoutError(
            gap if gap.startswith("lane_closeout_") else _ownerless_gap("fence_failed")
        ) from error


def _release_unreserved_fence(
    admission: OwnerlessCloseoutAdmission,
    database: Path,
    fence: dict[str, object],
) -> None:
    try:
        release_closeout_fence(
            database,
            subject=admission.observation.lane_ref,
            decision_id=admission.decision.decision_id,
            target_binding_digest=str(fence["target_binding_digest"]),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise OwnerlessCloseoutError(_ownerless_gap("transition_unknown")) from error


def _reservation(
    admission: OwnerlessCloseoutAdmission, fence: dict[str, object]
) -> dict[str, object]:
    return OwnerlessCloseoutReservation(
        schema_version=2,
        decision_id=admission.decision.decision_id,
        lane_ref=admission.observation.lane_ref,
        head=admission.observation.head,
        executor_ref=admission.executor_ref,
        decision_sha256=admission.decision_sha256,
        accepted_branch=admission.accepted_branch,
        accepted_head=admission.accepted_head,
        target_digest=admission.target_digest,
        target_binding_digest=str(fence["target_binding_digest"]),
        phase="reserved",
        recovery_state="reserved_no_effect",
        postcondition_digest="",
    ).to_payload()


def recover_completed_ownerless_closeout(  # noqa: PLR0913, RUF100 - exact recovery bindings
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    executor_ref: str,
    reservation: dict[str, object],
    receipt: dict[str, object] | None = None,
    decision_bytes: bytes | None = None,
) -> dict[str, object]:
    """Validate decision and Chronicle before completed-effect postconditions."""
    if decision_bytes is None:
        try:
            decision_bytes = decision_path.read_bytes()
        except OSError as error:
            raise OwnerlessCloseoutError(
                _OWNERLESS_DECISION_STALE,
                phase="receipt",
                recovery_state="effect_complete_receipt_missing",
            ) from error
    snapshot, gap = canonical_resolution_decision_snapshot(
        decision_bytes=decision_bytes,
        decision=decision,
    )
    if gap:
        raise OwnerlessCloseoutError(
            gap,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )
    decision = cast("dict[str, Any]", snapshot)
    if not current_chronicle_matches(root, decision):
        raise OwnerlessCloseoutError(
            _OWNERLESS_CHRONICLE_STALE,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )
    observation = LaneObservation.model_validate(decision["observation"])
    decision_sha256 = hashlib.sha256(decision_bytes).hexdigest()
    _verify_completed_binding(
        decision=decision,
        decision_sha256=decision_sha256,
        observation=observation,
        executor_ref=executor_ref,
        reservation=reservation,
    )
    accepted_branch = str(reservation["accepted_branch"])
    accepted_head = str(reservation["accepted_head"])
    if ref_head(root, accepted_branch) != accepted_head:
        raise OwnerlessCloseoutError(
            _OWNERLESS_ACCEPTED_HEAD_STALE,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )
    database = state_database(root)
    fence_state, fence = probe_closeout_fence(database, subject=observation.lane_ref)
    expected_fence = _completed_fence(
        decision=decision,
        decision_sha256=decision_sha256,
        observation=observation,
        reservation=reservation,
        fence=fence,
    )
    expected_binding = {
        field: reservation[field] for field in OwnerlessCloseoutBinding.model_fields
    }
    exact_receipt = exact_ownerless_resolution_receipt(
        receipt=receipt,
        decision=decision,
        observation=observation,
        expected_binding=expected_binding,
    )
    if receipt is not None and not exact_receipt:
        raise OwnerlessCloseoutError(
            _OWNERLESS_RECEIPT_MISMATCH,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )
    if fence_state == "unverifiable":
        raise OwnerlessCloseoutError(
            _OWNERLESS_FENCE_UNVERIFIABLE,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )
    if (fence_state == "present" and fence != expected_fence) or (
        fence_state == "absent" and not exact_receipt
    ):
        raise OwnerlessCloseoutError(
            _OWNERLESS_FENCE_STALE,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )
    postconditions = verify_ownerless_postconditions(
        root=root,
        database=database,
        decision_path=decision_path,
        decision_sha256=decision_sha256,
        observation=observation,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        fence=fence,
        decision_bytes=decision_bytes,
    )
    if canonical_resolution_payload_digest(postconditions) != reservation.get(
        "postcondition_digest"
    ):
        raise OwnerlessCloseoutError(
            _ownerless_gap("postcondition_failed:postcondition_digest"),
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )
    return OwnerlessCloseoutBinding.model_validate(expected_binding).model_dump(mode="json")


def _verify_completed_binding(
    *,
    decision: dict[str, Any],
    decision_sha256: str,
    observation: LaneObservation,
    executor_ref: str,
    reservation: dict[str, object],
) -> None:
    expected = {
        "decision_id": decision.get("decision_id"),
        "lane_ref": observation.lane_ref,
        "head": observation.head,
        "executor_ref": executor_ref,
        "decision_sha256": decision_sha256,
        "phase": "receipt",
        "recovery_state": "effect_complete_receipt_missing",
    }
    mismatch = next(
        (field for field, value in expected.items() if reservation.get(field) != value),
        "",
    )
    if mismatch:
        gap = (
            _OWNERLESS_DECISION_STALE
            if mismatch in {"decision_id", "lane_ref", "head", "decision_sha256"}
            else _ownerless_gap(f"recovery_binding_mismatch:{mismatch}")
        )
        raise OwnerlessCloseoutError(
            gap,
            phase="receipt",
            recovery_state="effect_complete_receipt_missing",
        )


def _completed_fence(
    *,
    decision: dict[str, Any],
    decision_sha256: str,
    observation: LaneObservation,
    reservation: dict[str, object],
    fence: dict[str, object] | None,
) -> dict[str, object]:
    payload = fence.get("payload") if isinstance(fence, dict) else None
    acquisition_id = payload.get("acquisition_id") if isinstance(payload, dict) else ""
    return {
        "subject": observation.lane_ref,
        "expected_head": observation.head,
        "decision_id": str(decision.get("decision_id") or ""),
        "executor_ref": str(reservation["executor_ref"]),
        "accepted_branch": str(reservation["accepted_branch"]),
        "accepted_head": str(reservation["accepted_head"]),
        "target_binding_digest": str(reservation["target_binding_digest"]),
        "payload": {
            "target_path": Path(observation.path).resolve(strict=False).as_posix(),
            "lane_incarnation_id": observation.lane_incarnation_id,
            "observation_digest": observation.digest(),
            "decision_sha256": decision_sha256,
            "chronicle_digest": str(decision.get("chronicle_digest") or ""),
            "acquisition_id": acquisition_id,
        },
    }


def _record_ownerless_partial(
    *,
    root: Path,
    artifact_root: Path,
    reservation: dict[str, object],
    error: OwnerlessCloseoutError,
) -> None:
    if error.phase is None or error.recovery_state is None:
        return
    if (
        error.phase == reservation["phase"]
        and error.recovery_state == reservation["recovery_state"]
    ):
        return
    try:
        transition_ownerless_closeout_reservation(
            root=root,
            expected=reservation,
            phase=error.phase,
            recovery_state=error.recovery_state,
            artifact_root=artifact_root,
        )
    except (OSError, TypeError, ValueError) as transition_error:
        raise OwnerlessCloseoutError(
            _ownerless_gap("reservation_update_failed"),
            phase="unknown",
            recovery_state="transition_unknown",
        ) from transition_error
