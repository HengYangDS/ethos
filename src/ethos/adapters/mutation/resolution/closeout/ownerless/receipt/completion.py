"""Decision-bound finalization for completed ownerless closeout effects."""

from __future__ import annotations

import os
from contextlib import ExitStack
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn
from typing import Protocol
from typing import cast

import ethos.adapters.mutation.resolution.closeout.receipt_recovery as cleanup
import ethos.adapters.mutation.resolution.records.io.descriptor_store as descriptor_store
from ethos.adapters.mutation.resolution._effects import OwnerlessCloseoutError
from ethos.adapters.mutation.resolution.closeout.effect import recover_completed_ownerless_closeout
from ethos.adapters.mutation.resolution.closeout.failure import classify_closeout_failure
from ethos.adapters.mutation.resolution.closeout.ownerless.receipt.reservation import (
    claim_receipt_reservation,
)
from ethos.adapters.mutation.resolution.receipts import chronicle_event
from ethos.contracts.resolution.closeout import OwnerlessCloseoutBinding

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.adapters.mutation.resolution.closeout.ownerless.effect import (
        OwnerlessCloseoutEffectContext,
    )
    from ethos.contracts.resolution.lane import LaneObservation

_OWNERLESS_RECEIPT_FIELDS = tuple(OwnerlessCloseoutBinding.model_fields)
_OWNERLESS_DECISION_STALE = "lane_resolution_ownerless_decision_stale"


@dataclass(frozen=True, slots=True)
class CompletedDecisionBinding:
    """Held bytes and descriptor identity for one current decision path."""

    path: Path
    record_root: Path
    raw: bytes
    descriptor: int

    def require_current(self) -> None:
        """Require the held bytes to remain the exact visible decision path."""
        try:
            descriptor_store.require_locked_record_identity(
                self.path,
                self.descriptor,
                record_root=self.record_root,
            )
            current = descriptor_store.read_descriptor_bytes(self.descriptor)
            descriptor_store.require_locked_record_identity(
                self.path,
                self.descriptor,
                record_root=self.record_root,
            )
        except (OSError, TypeError, ValueError) as error:
            _raise_stale(error)
        if current != self.raw:
            _raise_stale()

    def current_gap(self) -> str:
        """Return the stable stale gap instead of releasing bound resources."""
        try:
            self.require_current()
        except OwnerlessCloseoutError as error:
            return str(error)
        return ""


@contextmanager
def bind_completed_decision(
    *, decision_path: Path, record_root: Path
) -> Iterator[CompletedDecisionBinding]:
    """Hold one decision record across completed recovery boundaries."""
    try:
        with descriptor_store.lock_record(decision_path, record_root=record_root) as descriptor:
            binding = CompletedDecisionBinding(
                path=decision_path.absolute(),
                record_root=record_root,
                raw=descriptor_store.read_descriptor_bytes(descriptor),
                descriptor=descriptor,
            )
            binding.require_current()
            yield binding
    except OwnerlessCloseoutError:
        raise
    except (OSError, TypeError, ValueError) as error:
        _raise_stale(error)


def enter_completed_decision(
    stack: ExitStack, *, decision_path: Path, record_root: Path
) -> tuple[CompletedDecisionBinding | None, str]:
    """Enter one binding in the caller stack and return a stable gap on failure."""
    try:
        return (
            stack.enter_context(
                bind_completed_decision(
                    decision_path=decision_path,
                    record_root=record_root,
                )
            ),
            "",
        )
    except OwnerlessCloseoutError as error:
        return None, str(error)


class _PrepareResolution(Protocol):
    def __call__(
        self,
        *,
        control_root: Path,
        artifact_root: Path,
        decision: dict[str, Any],
        observation: LaneObservation,
        disposition: str,
    ) -> tuple[dict[str, object], dict[str, object], str, tuple[str, ...]]: ...


class _WriteReceipt(Protocol):
    def __call__(
        self,
        *,
        root: Path,
        receipt: dict[str, object],
        artifact_root: Path | None = None,
        require_ownerless_closeout_binding: bool = False,
    ) -> str: ...


def recover_ownerless_resolution(
    *,
    context: OwnerlessCloseoutEffectContext,
    report: dict[str, object],
    prepare_resolution: _PrepareResolution,
    write_receipt: _WriteReceipt,
) -> None:
    """Finalize a completed ownerless effect under one exact decision binding."""
    decision_id = str(context.decision.get("decision_id") or "")
    reservation_stack = ExitStack()
    reservation_claimed, reservation_descriptor, reservation_gap = claim_receipt_reservation(
        reservation_stack,
        context.control_root,
        context.artifact_root,
        decision_id,
        mode="recover_completed",
    )
    if reservation_gap or not reservation_claimed:
        reservation_stack.close()
        _block(report, reservation_gap, state="partial_transition")
        return
    current_decision, decision_gap = enter_completed_decision(
        reservation_stack,
        decision_path=context.decision_path,
        record_root=context.artifact_root,
    )
    if current_decision is None:
        reservation_stack.close()
        _block(report, decision_gap, state="partial_transition")
        return
    receipt_written = False
    release_descriptor: int | None = None
    try:
        if cleanup.recover_existing_ownerless_receipt(
            context=context,
            report=report,
            decision_bytes=current_decision.raw,
            require_decision_current=current_decision.require_current,
        ):
            receipt_written = bool(report.get("receipt"))
            release_descriptor = reservation_descriptor if receipt_written else None
            return
        executor_ref = os.environ.get("ETHOS_ACTOR", "").strip()
        if reservation_descriptor is None or not executor_ref:
            gap = (
                "lane_resolution_ownerless_receipt_mismatch"
                if reservation_descriptor is None
                else "lane_resolution_ownerless_executor_required"
            )
            _block(report, gap, state="partial_transition")
            return
        try:
            binding = recover_completed_ownerless_closeout(
                root=context.control_root,
                decision_path=context.decision_path,
                decision=context.decision,
                executor_ref=executor_ref,
                reservation=context.reservation or {},
                decision_bytes=current_decision.raw,
            )
        except OwnerlessCloseoutError as error:
            _block(
                report,
                classify_closeout_failure(
                    error, "lane_resolution_ownerless_recovery_not_finalizable"
                ),
                state="partial_transition",
            )
            return
        receipt_written = _write_completed_receipt(
            context=context,
            report=report,
            binding=binding,
            current_decision=current_decision,
            prepare_resolution=prepare_resolution,
            write_receipt=write_receipt,
        )
        release_descriptor = reservation_descriptor if receipt_written else None
    finally:
        try:
            cleanup_gap = cleanup.release_receipt_reservation(
                control_root=context.control_root,
                artifact_root=context.artifact_root,
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


def _write_completed_receipt(
    *,
    context: OwnerlessCloseoutEffectContext,
    report: dict[str, object],
    binding: dict[str, object],
    current_decision: CompletedDecisionBinding,
    prepare_resolution: _PrepareResolution,
    write_receipt: _WriteReceipt,
) -> bool:
    package, receipt, state, effect_gaps = prepare_resolution(
        control_root=context.control_root,
        artifact_root=context.artifact_root,
        decision=context.decision,
        observation=context.observation,
        disposition="retire",
    )
    if effect_gaps:
        _block(report, *effect_gaps, state="partial_transition")
        return False
    if decision_gap := current_decision.current_gap():
        _block(report, decision_gap, state="partial_transition")
        return False
    receipt_binding = {field: binding[field] for field in _OWNERLESS_RECEIPT_FIELDS}
    receipt["ownerless_closeout_binding"] = receipt_binding
    try:
        receipt_path = write_receipt(
            root=context.control_root,
            receipt=receipt,
            artifact_root=context.artifact_root,
            require_ownerless_closeout_binding=True,
        )
    except (OSError, ValueError):
        _block(
            report,
            "lane_resolution_receipt_write_failed_after_effect",
            state="partial_transition",
        )
        return False
    report.update(
        state=state,
        preservation_package=package,
        receipt=receipt,
        receipt_path=receipt_path,
        ownerless_closeout_binding=receipt_binding,
        chronicle_event=chronicle_event(context.decision, receipt),
    )
    if decision_gap := current_decision.current_gap():
        _block(report, decision_gap, state="partial_transition")
        return True
    if cleanup_gap := cleanup.release_ownerless_closeout_resources(
        context=context,
        binding=binding,
    ):
        _block(report, cleanup_gap, state="partial_transition")
    return True


def _block(report: dict[str, object], *gaps: str, state: str) -> None:
    report.update(
        ok=False,
        state=state,
        required_gaps=list(dict.fromkeys(gap for gap in gaps if gap)),
    )


def _raise_stale(cause: BaseException | None = None) -> NoReturn:
    error = OwnerlessCloseoutError(
        _OWNERLESS_DECISION_STALE,
        phase="receipt",
        recovery_state="effect_complete_receipt_missing",
    )
    if cause is None:
        raise error
    raise error from cause
