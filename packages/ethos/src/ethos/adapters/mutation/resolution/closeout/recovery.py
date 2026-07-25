"""Crash recovery and direct effect orchestration for exceptional lane resolution."""

from __future__ import annotations

import hashlib
from contextlib import ExitStack
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos.adapters.mutation.resolution.closeout.cleanup.core as cleanup
import ethos.adapters.mutation.resolution.closeout.ownerless.receipt.completion as completion
from ethos.adapters.mutation.resolution._effects import prepare_resolution_effect
from ethos.adapters.mutation.resolution._effects import retire_lane
from ethos.adapters.mutation.resolution._shared import accepted_preserve_retire_chronicle
from ethos.adapters.mutation.resolution._shared import transition_gap
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.closeout.effect import pre_admit_ownerless_lane
from ethos.adapters.mutation.resolution.closeout.ownerless.effect import (
    is_ownerless_closeout_candidate,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.effect import retire_ownerless_resolution
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
    claim_effect_receipt_reservation,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
    claim_receipt_reservation,
)
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.core import (
    ownerless_receipt_reservation_token,
)
from ethos.adapters.mutation.resolution.observation import observe_lane
from ethos.adapters.mutation.resolution.receipts import chronicle_event
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.adapters.mutation.resolution.records.roots import accepted_control_root
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutBinding
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
        OwnerlessCloseoutAdmission,
    )

_OWNERLESS_RECEIPT_FIELDS = tuple(OwnerlessCloseoutBinding.model_fields)
_PRESERVED_RETIREMENT_BLOCKED_REASONS = {
    "lane_resolution_chronicle_disposition_mismatch",
    "lane_resolution_chronicle_invalid",
    "lane_resolution_chronicle_missing",
    "lane_resolution_chronicle_stale",
    "lane_resolution_observation_stale",
}


def _block(report: dict[str, object], *gaps: str, state: str = "blocked") -> None:
    report.update(
        ok=False,
        state=state,
        required_gaps=list(dict.fromkeys(gap for gap in gaps if gap)),
    )


def ownerless_recovery_context(
    *, root: Path, decision: dict[str, Any], disposition: str
) -> tuple[dict[str, object], Path | None, Path | None, str]:
    """Return an exact resumable ownerless transition, or its blocking gap."""
    if disposition != "retire" or not decision:
        return {}, None, None, ""
    observation = cast("dict[str, object]", decision.get("observation") or {})
    if (
        not valid_decision_id(str(decision.get("decision_id") or ""))
        or bool(observation.get("dirty"))
        or not bool(observation.get("orphan"))
        or bool(observation.get("holder_ref"))
    ):
        return {}, None, None, ""
    control_root, artifact_root, root_gap = _resolution_roots(root)
    if root_gap or control_root is None or artifact_root is None:
        return {}, control_root, artifact_root, root_gap
    lane_ref = str(observation.get("lane_ref") or "")
    head = str(observation.get("head") or "")
    if not lane_ref or not head:
        return {}, control_root, artifact_root, ""
    lane_observation = LaneObservation.model_validate(observation)
    receipt_recovery, receipt_gap = cleanup.ownerless_receipt_recovery_context(
        control_root=control_root,
        artifact_root=artifact_root,
        decision=decision,
        observation=lane_observation,
    )
    if receipt_gap:
        return {}, control_root, artifact_root, receipt_gap
    reservation, reservation_gap = cleanup.ownerless_reservation_recovery_context(
        control_root=control_root,
        artifact_root=artifact_root,
        decision=decision,
        observation=lane_observation,
        receipt_recovery=receipt_recovery,
    )
    return reservation, control_root, artifact_root, reservation_gap


def recover_ownerless_resolution(  # noqa: PLR0913, RUF100 - exact recovery inputs
    *,
    control_root: Path,
    artifact_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    reservation: dict[str, object],
    report: dict[str, object],
) -> None:
    """Finalize a completed ownerless effect before ordinary target observation."""
    completion.recover_ownerless_resolution(
        control_root=control_root,
        artifact_root=artifact_root,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        reservation=reservation,
        report=report,
        prepare_resolution=_prepare_resolution,
        write_receipt=write_resolution_receipt,
    )


def apply_resolution(  # noqa: PLR0913, RUF100 - exact effect inputs
    *,
    root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    report: dict[str, object],
    recover_receipt_reservation: bool = False,
) -> None:
    """Apply one bounded resolution effect and retain partial-transition evidence."""
    control_root, artifact_root, root_gap = _resolution_roots(root)
    if root_gap or control_root is None or artifact_root is None:
        _block(report, root_gap)
        return
    if disposition == "preserve-retire" and (
        chronicle_gap := _preserve_retire_chronicle_gap(
            control_root=control_root,
            decision=decision,
            observation=observation,
        )
    ):
        _block(report, chronicle_gap)
        return
    decision_id = str(decision.get("decision_id") or "")
    reservation_stack = ExitStack()
    ownerless_admission, reservation_descriptor, claim_gaps = _claim_effect_attempt(
        stack=reservation_stack,
        control_root=control_root,
        artifact_root=artifact_root,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        disposition=disposition,
        recover=recover_receipt_reservation,
    )
    if claim_gaps or reservation_descriptor is None:
        reservation_stack.close()
        _block(report, *(claim_gaps or ("lane_resolution_receipt_invalid",)))
        return
    retain_reservation = False
    receipt_written = False
    release_descriptor: int | None = reservation_descriptor
    try:
        package, receipt, state, effect_gaps = _prepare_resolution(
            control_root=control_root,
            artifact_root=artifact_root,
            decision=decision,
            observation=observation,
            disposition=disposition,
        )
        if effect_gaps:
            _block(report, *effect_gaps)
            return
        report.update(state=state, preservation_package=package)
        retain_reservation, retire_gap, ownerless_binding = _retire_resolution(
            root=root,
            control_root=control_root,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            disposition=disposition,
            artifact_root=artifact_root,
            ownerless_admission=ownerless_admission,
        )
        release_descriptor = None if retain_reservation else reservation_descriptor
        requires_ownerless_binding = _attach_ownerless_receipt_binding(
            receipt=receipt,
            report=report,
            binding=ownerless_binding,
        )
        if retire_gap:
            if _report_retire_gap(
                control_root=control_root,
                artifact_root=artifact_root,
                decision=decision,
                disposition=disposition,
                package=package,
                receipt=receipt,
                retire_gap=retire_gap,
                report=report,
            ):
                receipt_written = True
                release_descriptor = reservation_descriptor
            return
        destructive_effect = disposition in {"retire", "preserve-retire"}
        try:
            receipt_path = write_resolution_receipt(
                root=control_root,
                receipt=receipt,
                artifact_root=artifact_root,
                require_ownerless_closeout_binding=requires_ownerless_binding,
            )
        except (OSError, ValueError):
            _block(
                report,
                "lane_resolution_receipt_write_failed_after_effect"
                if destructive_effect
                else "lane_resolution_receipt_write_failed",
                state="partial_transition" if destructive_effect else "blocked",
            )
            return
        receipt_written = True
        release_descriptor = reservation_descriptor
        report.update(
            receipt=receipt,
            receipt_path=receipt_path,
            chronicle_event=chronicle_event(decision, receipt),
        )
        if requires_ownerless_binding and (
            cleanup_gap := cleanup.release_ownerless_closeout_resources(
                control_root=control_root,
                artifact_root=artifact_root,
                decision=decision,
                observation=observation,
                binding=ownerless_binding,
            )
        ):
            _block(report, cleanup_gap, state="partial_transition")
    finally:
        try:
            cleanup_gap = cleanup.release_receipt_reservation(
                control_root=control_root,
                artifact_root=artifact_root,
                decision_id=decision_id,
                locked_descriptor=release_descriptor,
            )
        finally:
            reservation_stack.close()
        if cleanup_gap:
            current_gaps = cast("list[str]", report["required_gaps"])
            _block(
                report,
                *current_gaps,
                cleanup_gap,
                state="partial_transition" if receipt_written else "blocked",
            )


def _claim_effect_attempt(  # noqa: PLR0913, RUF100 - exact claim/admission inputs
    *,
    stack: ExitStack,
    control_root: Path,
    artifact_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    recover: bool,
) -> tuple[OwnerlessCloseoutAdmission | None, int | None, tuple[str, ...]]:
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
            return None, descriptor, (gap or "lane_resolution_receipt_invalid",)
        try:
            token = ownerless_receipt_reservation_token(
                control_root=control_root,
                artifact_root=artifact_root,
                decision_id=decision_id,
                descriptor=descriptor,
            )
        except (OSError, TypeError, ValueError) as error:
            return (
                None,
                descriptor,
                (transition_gap(error, "lane_resolution_receipt_invalid"),),
            )
        admission, admission_gap = pre_admit_ownerless_lane(
            root=control_root,
            decision_path=decision_path,
            decision=decision,
            observation=observation,
            disposition=disposition,
            receipt_reservation_token=token,
        )
        return admission, descriptor, ((admission_gap,) if admission_gap else ())
    admission, admission_gap = pre_admit_ownerless_lane(
        root=control_root,
        decision_path=decision_path,
        decision=decision,
        observation=observation,
        disposition=disposition,
        receipt_reservation_token=None,
    )
    if admission_gap:
        return None, None, (admission_gap,)
    admission, descriptor, claim_gap = claim_effect_receipt_reservation(
        stack,
        control_root,
        artifact_root,
        decision_id,
        mode="create",
        admission=admission,
    )
    if not claim_gap:
        return admission, descriptor, ()
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
    return None, descriptor, tuple(gap for gap in (claim_gap, release_gap) if gap)


def _resolution_roots(root: Path) -> tuple[Path | None, Path | None, str]:
    try:
        return accepted_control_root(root), current_record_root(root), ""
    except ValueError as error:
        return None, None, transition_gap(error, "lane_resolution_control_root_unavailable")


def _prepare_resolution(
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
) -> tuple[dict[str, object], dict[str, object], str, tuple[str, ...]]:
    try:
        package, receipt, state, effect_gap = prepare_resolution_effect(
            control_root=control_root,
            artifact_root=artifact_root,
            decision=decision,
            observation=observation,
            disposition=disposition,
        )
    except (OSError, ValueError) as error:
        return {}, {}, "blocked", (transition_gap(error, "lane_resolution_effect_failed"),)
    if effect_gap:
        return package, receipt, state, (effect_gap,)
    return package, receipt, state, ()


def _attach_ownerless_receipt_binding(
    *, receipt: dict[str, object], report: dict[str, object], binding: dict[str, object]
) -> bool:
    """Attach the exact ownerless postcondition binding when one exists."""
    if not binding:
        return False
    receipt_binding = {field: binding[field] for field in _OWNERLESS_RECEIPT_FIELDS}
    receipt["ownerless_closeout_binding"] = receipt_binding
    report["ownerless_closeout_binding"] = receipt_binding
    return True


def _report_retire_gap(  # noqa: PLR0913, RUF100 - exact retained-preservation bindings
    *,
    control_root: Path,
    artifact_root: Path,
    decision: dict[str, Any],
    disposition: str,
    package: dict[str, object],
    receipt: dict[str, object],
    retire_gap: str,
    report: dict[str, object],
) -> bool:
    """Report a blocked retirement and persist any verified preservation state."""
    if not _retained_preservation_gap(disposition, retire_gap):
        _block(report, retire_gap, state=retire_gap.removeprefix("lane_resolution_"))
        return False
    retained_receipt, receipt_path, receipt_gap = _write_retained_preservation_receipt(
        control_root=control_root,
        artifact_root=artifact_root,
        receipt=receipt,
        retire_gap=retire_gap,
    )
    if receipt_gap:
        _block(report, receipt_gap, state="partial_transition")
        return False
    report.update(
        state="preserved_retirement_blocked",
        preservation_package=package,
        receipt=retained_receipt,
        receipt_path=receipt_path,
        chronicle_event=chronicle_event(decision, retained_receipt),
    )
    _block(report, retire_gap, state="preserved_retirement_blocked")
    return True


def _retained_preservation_gap(disposition: str, gap: str) -> bool:
    """Return whether one verified package must be recorded without retirement."""
    return disposition == "preserve-retire" and gap in _PRESERVED_RETIREMENT_BLOCKED_REASONS


def _write_retained_preservation_receipt(
    *,
    control_root: Path,
    artifact_root: Path,
    receipt: dict[str, object],
    retire_gap: str,
) -> tuple[dict[str, object], str, str]:
    """Write the valid preservation-only record after a pre-retirement block."""
    retained = {
        **receipt,
        "state": "preserved_retirement_blocked",
        "retirement_blocked_reason": retire_gap,
    }
    try:
        receipt_path = write_resolution_receipt(
            root=control_root,
            receipt=retained,
            artifact_root=artifact_root,
        )
    except (OSError, ValueError):
        return retained, "", "lane_resolution_receipt_write_failed"
    return retained, receipt_path, ""


def _preserve_retire_chronicle_gap(
    *, control_root: Path, decision: dict[str, Any], observation: LaneObservation
) -> str:
    chronicle, gap = accepted_preserve_retire_chronicle(
        control_root,
        chronicle_ref=str(decision.get("chronicle_ref") or ""),
        target_branch=observation.lane_ref,
        target_head=observation.head,
    )
    if gap or chronicle is None:
        return gap or "lane_resolution_chronicle_invalid"
    return (
        ""
        if hashlib.sha256(chronicle).hexdigest() == str(decision.get("chronicle_digest") or "")
        else "lane_resolution_chronicle_stale"
    )


def _retire_resolution(  # noqa: PLR0913, RUF100 - exact resolution context
    *,
    root: Path,
    control_root: Path,
    decision_path: Path,
    decision: dict[str, Any],
    observation: LaneObservation,
    disposition: str,
    artifact_root: Path,
    ownerless_admission: OwnerlessCloseoutAdmission | None = None,
) -> tuple[bool, str, dict[str, object]]:
    if disposition not in {"retire", "preserve-retire"}:
        return False, "", {}
    if disposition == "preserve-retire" and (
        preservation_gap := _preserve_retire_pre_retirement_gap(
            control_root=control_root,
            decision=decision,
            observation=observation,
        )
    ):
        return False, preservation_gap, {}
    if is_ownerless_closeout_candidate(disposition, observation):
        return retire_ownerless_resolution(
            control_root=control_root,
            decision_path=decision_path,
            decision=decision,
            artifact_root=artifact_root,
            ownerless_admission=ownerless_admission,
        )
    try:
        retire_lane(
            root=root,
            observation=observation,
            force=disposition == "preserve-retire" and observation.dirty,
        )
    except ValueError as error:
        gap = transition_gap(error, "lane_resolution_branch_delete_failed")
        return (
            gap
            in {
                "lane_resolution_branch_delete_failed_after_worktree_removed",
                "lane_resolution_branch_delete_state_uncertain",
            },
            gap,
            {},
        )
    return True, "", {}


def _preserve_retire_pre_retirement_gap(
    *, control_root: Path, decision: dict[str, Any], observation: LaneObservation
) -> str:
    """Recheck source and Chronicle immediately before destructive retirement."""
    current, current_gaps = observe_lane(control_root, observation.lane_ref)
    if current_gaps or current.digest() != observation.digest():
        return "lane_resolution_observation_stale"
    return _preserve_retire_chronicle_gap(
        control_root=control_root,
        decision=decision,
        observation=observation,
    )
