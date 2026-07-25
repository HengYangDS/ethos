"""Receipt-sidecar ownership for complete lane-resolution attempts."""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.records.inventory as inventory
import ethos.adapters.mutation.resolution.records.io.posix as posix
from ethos.adapters.mutation.resolution._shared import transition_gap
from ethos.adapters.mutation.resolution.records.core import claim_resolution_receipt_reservation
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.current.snapshot import open_current_record_snapshot
from ethos.adapters.mutation.resolution.records.io.core import read_descriptor_bytes
from ethos.adapters.mutation.resolution.records.io.core import require_locked_record_identity

if TYPE_CHECKING:
    from collections.abc import Iterator
    from contextlib import ExitStack
    from pathlib import Path
    from typing import Literal

    from ethos.adapters.mutation.resolution.closeout.ownerless.admission.core import (
        OwnerlessCloseoutAdmission,
    )
    from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation

_OWNERLESS_RESERVATION_COMPETING = "lane_resolution_ownerless_reservation_competing"


@dataclass(frozen=True, slots=True)
class OwnerlessReceiptReservationToken:
    """Exact path, bytes, and file identity for one locked receipt sidecar."""

    path: Path
    raw: bytes
    identity: posix.FileIdentity


@dataclass(frozen=True, slots=True)
class OwnerlessReceiptReservationContext:
    """Locally held descriptor and exact sidecar identity for one effect attempt."""

    control_root: Path
    artifact_root: Path
    decision_id: str
    descriptor: int
    token: OwnerlessReceiptReservationToken


class OwnerlessReceiptReservationError(ValueError):
    """The exact self-owned receipt sidecar is absent, replaced, or competing."""


def claim_receipt_reservation(
    stack: ExitStack,
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    *,
    mode: Literal["create", "recover", "recover_completed"],
) -> tuple[bool, int | None, str]:
    """Enter one sidecar claim and map storage failures to stable gaps."""
    try:
        descriptor = stack.enter_context(
            claim_resolution_receipt_reservation(
                root=control_root,
                decision_id=decision_id,
                artifact_root=artifact_root,
                mode=mode,
            )
        )
    except (OSError, ValueError) as error:
        if isinstance(error, ValueError):
            return False, None, transition_gap(error, "lane_resolution_receipt_invalid")
        gap = (
            "lane_resolution_receipt_path_exists"
            if isinstance(error, FileExistsError)
            else "lane_resolution_receipt_path_unsafe"
        )
        return False, None, gap
    return True, descriptor, ""


def claim_effect_receipt_reservation(  # noqa: PLR0913, RUF100 - exact sidecar claim
    stack: ExitStack,
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    *,
    mode: Literal["create", "recover"],
    admission: OwnerlessCloseoutAdmission | None,
) -> tuple[
    OwnerlessCloseoutAdmission | None,
    int | None,
    OwnerlessReceiptReservationContext | None,
    str,
]:
    """Claim one effect writer and return its locally held exact sidecar context."""
    claimed, descriptor, gap = claim_receipt_reservation(
        stack,
        control_root,
        artifact_root,
        decision_id,
        mode=mode,
    )
    if gap or not claimed or descriptor is None:
        return None, descriptor, None, gap
    if admission is None:
        return None, descriptor, None, ""
    try:
        context = ownerless_receipt_reservation_context(
            control_root=control_root,
            artifact_root=artifact_root,
            decision_id=decision_id,
            descriptor=descriptor,
        )
    except (OSError, TypeError, ValueError) as error:
        return None, descriptor, None, transition_gap(error, "lane_resolution_receipt_invalid")
    return admission, descriptor, context, ""


def ownerless_receipt_reservation_token(
    *,
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    descriptor: int,
) -> OwnerlessReceiptReservationToken:
    """Derive one immutable token from the exact locked receipt sidecar."""
    path = _reservation_path(control_root, artifact_root, decision_id)
    expected = _reservation_bytes(decision_id)
    require_locked_record_identity(path, descriptor, record_root=artifact_root)
    identity = posix.file_identity(os.fstat(descriptor))
    if read_descriptor_bytes(descriptor) != expected:
        raise ValueError(_OWNERLESS_RESERVATION_COMPETING)
    require_locked_record_identity(path, descriptor, record_root=artifact_root)
    if posix.file_identity(os.fstat(descriptor)) != identity:
        raise ValueError(_OWNERLESS_RESERVATION_COMPETING)
    token = OwnerlessReceiptReservationToken(path=path, raw=expected, identity=identity)
    require_ownerless_receipt_reservation_token(
        token=token,
        control_root=control_root,
        artifact_root=artifact_root,
        decision_id=decision_id,
    )
    return token


def ownerless_receipt_reservation_context(
    *,
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    descriptor: int,
) -> OwnerlessReceiptReservationContext:
    """Build one local context from an already claimed exact receipt sidecar."""
    control = control_root.absolute()
    records = artifact_root.absolute()
    token = ownerless_receipt_reservation_token(
        control_root=control,
        artifact_root=records,
        decision_id=decision_id,
        descriptor=descriptor,
    )
    return OwnerlessReceiptReservationContext(
        control_root=control,
        artifact_root=records,
        decision_id=decision_id,
        descriptor=descriptor,
        token=token,
    )


def require_ownerless_receipt_reservation_context(
    context: OwnerlessReceiptReservationContext,
) -> None:
    """Require the exact context descriptor, bytes, and identity to remain current."""
    try:
        require_locked_record_identity(
            context.token.path,
            context.descriptor,
            record_root=context.artifact_root,
        )
        require_ownerless_receipt_reservation_token(
            token=context.token,
            control_root=context.control_root,
            artifact_root=context.artifact_root,
            decision_id=context.decision_id,
        )
        require_locked_record_identity(
            context.token.path,
            context.descriptor,
            record_root=context.artifact_root,
        )
    except (OSError, TypeError, ValueError) as error:
        raise OwnerlessReceiptReservationError(_OWNERLESS_RESERVATION_COMPETING) from error


@contextmanager
def ownerless_receipt_reservation_guard(
    context: OwnerlessReceiptReservationContext | None,
) -> Iterator[None]:
    """Probe one locally held exact sidecar before and after fence-held work."""
    if context is None:
        yield
        return
    require_ownerless_receipt_reservation_context(context)
    try:
        yield
    finally:
        require_ownerless_receipt_reservation_context(context)


def ownerless_reservation_admission_or_gap(  # noqa: PLR0913, RUF100 - exact retry binding
    *,
    root: Path,
    record_root: Path,
    decision_path: Path,
    decision_sha256: str,
    expected: OwnerlessCloseoutReservation,
    receipt_reservation: OwnerlessReceiptReservationContext | None,
) -> tuple[OwnerlessCloseoutReservation | None, str]:
    """Classify a typed retry reservation with exact self-sidecar awareness."""
    try:
        if receipt_reservation is not None:
            _require_ownerless_receipt_reservation_scope(
                context=receipt_reservation,
                root=root,
                record_root=record_root,
                decision_id=expected.decision_id,
            )
            require_ownerless_receipt_reservation_context(receipt_reservation)
        return (
            inventory.ownerless_closeout_reservation_admission(
                root=root,
                record_root=record_root,
                decision_path=decision_path,
                decision_sha256=decision_sha256,
                expected=expected,
                receipt_reservation_decision_id=(
                    expected.decision_id if receipt_reservation is not None else None
                ),
            ),
            "",
        )
    except (OSError, TypeError, ValueError) as error:
        return None, transition_gap(error, _OWNERLESS_RESERVATION_COMPETING)


def _require_ownerless_receipt_reservation_scope(
    *,
    context: OwnerlessReceiptReservationContext,
    root: Path,
    record_root: Path,
    decision_id: str,
) -> None:
    if (
        context.control_root != root.absolute()
        or context.artifact_root != record_root.absolute()
        or context.decision_id != decision_id
    ):
        raise ValueError(_OWNERLESS_RESERVATION_COMPETING)


def require_ownerless_receipt_reservation_token(
    *,
    token: OwnerlessReceiptReservationToken,
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
) -> None:
    """Require the token's exact sidecar path, bytes, and identity to remain live."""
    expected_path = _reservation_path(control_root, artifact_root, decision_id)
    expected = _reservation_bytes(decision_id)
    if token.path != expected_path or token.raw != expected:
        raise ValueError(_OWNERLESS_RESERVATION_COMPETING)
    snapshot, state = open_current_record_snapshot(artifact_root)
    if snapshot is None or state != "valid":
        raise ValueError(_OWNERLESS_RESERVATION_COMPETING)
    with snapshot:
        names, category_state = snapshot.open_directory("receipts")
        identity = snapshot.file_identity("receipts", token.path.name)
        raw = snapshot.read_file("receipts", token.path.name)
    if (
        category_state != "valid"
        or token.path.name not in names
        or identity != token.identity
        or raw != token.raw
    ):
        raise ValueError(_OWNERLESS_RESERVATION_COMPETING)


def _reservation_path(control_root: Path, artifact_root: Path, decision_id: str) -> Path:
    destination = receipt_path(control_root, decision_id, artifact_root=artifact_root)
    return destination.with_name(f".{destination.stem}.receipt-reservation").absolute()


def _reservation_bytes(decision_id: str) -> bytes:
    return f"{decision_id}\n".encode()
