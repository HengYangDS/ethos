"""Typed durable ownerless-closeout reservation persistence."""

from __future__ import annotations

import hashlib
import json
from contextlib import ExitStack
from contextlib import contextmanager
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.records.core import canonical_current_record_bytes
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.core import remove_record
from ethos.adapters.mutation.resolution.records.core import replace_json_atomic
from ethos.adapters.mutation.resolution.records.core import write_json_atomic
from ethos.adapters.mutation.resolution.records.io.core import lock_record
from ethos.adapters.mutation.resolution.records.io.core import read_descriptor_bytes
from ethos.adapters.mutation.resolution.records.io.core import read_record_bytes
from ethos.adapters.mutation.resolution.records.io.core import require_locked_record_identity
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.contracts.resolution.closeout import LaneResolutionReceipt
from ethos.contracts.resolution.closeout import OwnerlessCloseoutBinding
from ethos.contracts.resolution.closeout import OwnerlessCloseoutReservation
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_RESERVATIONS = "reservations"
_OWNERLESS_RESERVATION_INVALID = "lane_resolution_ownerless_reservation_invalid"
_OWNERLESS_RESERVATION_BUSY = "lane_resolution_ownerless_reservation_busy"
_OWNERLESS_RESERVATION_MISMATCH = "lane_resolution_ownerless_reservation_mismatch"
_OWNERLESS_RECOVERY_BINDING_MISMATCH = "lane_resolution_ownerless_recovery_binding_mismatch"
_OWNERLESS_RECOVERY_NOT_FINALIZABLE = "lane_resolution_ownerless_recovery_not_finalizable"
_OWNERLESS_RESERVATION_RELEASE_INVALID = "lane_resolution_ownerless_reservation_release_invalid"
_RESERVATION_STATE_FIELDS = {"phase", "recovery_state", "postcondition_digest"}
_IMMUTABLE_RESERVATION_FIELDS = tuple(
    field
    for field in OwnerlessCloseoutReservation.model_fields
    if field not in _RESERVATION_STATE_FIELDS
)


def _ownerless_reservation_invalid() -> ValueError:
    return ValueError(_OWNERLESS_RESERVATION_INVALID)


def validate_ownerless_closeout_reservation(payload: object) -> dict[str, object]:
    """Return the exact canonical schema-version-2 ownerless reservation payload."""
    try:
        canonical = OwnerlessCloseoutReservation.model_validate(payload).to_payload()
    except (TypeError, ValueError) as error:
        raise _ownerless_reservation_invalid() from error
    if canonical != payload:
        raise _ownerless_reservation_invalid()
    return canonical


def target_digest(lane_ref: str, head: str) -> str:
    """Bind one exact lane ref and head without ambiguous concatenation."""
    return hashlib.sha256(f"{lane_ref}\0{head}".encode()).hexdigest()


def ownerless_closeout_reservation_path(
    root: Path,
    target: str,
    *,
    artifact_root: Path | None = None,
) -> Path:
    """Return the target-scoped durable ownerless-closeout reservation path."""
    return (artifact_root or current_record_root(root)) / _RESERVATIONS / f"{target}.json"


def reserve_ownerless_closeout_target(
    *,
    root: Path,
    reservation: dict[str, object],
    artifact_root: Path | None = None,
) -> Path:
    """Atomically reserve one lane/head target; exact replay is idempotent."""
    payload = _validated_ownerless_reservation(reservation, initial=True)
    record_root = artifact_root or current_record_root(root)
    destination = ownerless_closeout_reservation_path(
        root, str(payload["target_digest"]), artifact_root=record_root
    )
    try:
        write_json_atomic(destination, payload, record_root=record_root)
    except FileExistsError:
        with _locked_ownerless_reservation(record_root, destination) as descriptor:
            current = _read_locked_ownerless_reservation(descriptor)
            if current == payload:
                return destination
            if current.get("decision_id") != payload["decision_id"]:
                raise FileExistsError(destination) from None
            raise ValueError(_OWNERLESS_RESERVATION_MISMATCH) from None
    return destination


def transition_ownerless_closeout_reservation(  # noqa: PLR0913, RUF100 - exact transition CAS
    *,
    root: Path,
    expected: dict[str, object],
    phase: str,
    recovery_state: str,
    postcondition_digest: str = "",
    artifact_root: Path | None = None,
) -> dict[str, object]:
    """Replace one exact current reservation with a valid recovery classification."""
    expected_payload = _validated_ownerless_reservation(expected)
    if recovery_state == "reserved_no_effect":
        raise ValueError(_OWNERLESS_RESERVATION_INVALID)
    record_root = artifact_root or current_record_root(root)
    destination = ownerless_closeout_reservation_path(
        root, str(expected_payload["target_digest"]), artifact_root=record_root
    )
    with _locked_ownerless_reservation(record_root, destination) as descriptor:
        current = _read_locked_ownerless_reservation(descriptor)
        if current != expected_payload:
            raise ValueError(_OWNERLESS_RESERVATION_MISMATCH)
        updated = _validated_ownerless_reservation(
            {
                **current,
                "phase": phase,
                "recovery_state": recovery_state,
                "postcondition_digest": postcondition_digest,
            }
        )
        require_locked_record_identity(
            destination,
            descriptor,
            record_root=record_root,
        )
        replace_json_atomic(
            destination,
            updated,
            expected=current,
            record_root=record_root,
            locked_descriptor=descriptor,
        )
    return updated


def ownerless_closeout_recovery_binding(
    *,
    root: Path,
    expected: dict[str, object],
    artifact_root: Path | None = None,
) -> dict[str, object]:
    """Return receipt binding only for the same exact completed-effect decision."""
    expected_payload = _validated_ownerless_reservation(expected, initial=True)
    record_root = artifact_root or current_record_root(root)
    destination = ownerless_closeout_reservation_path(
        root, str(expected_payload["target_digest"]), artifact_root=record_root
    )
    current = _read_ownerless_reservation(record_root, destination)
    return _ownerless_closeout_recovery_binding(
        current=current,
        expected=expected_payload,
    )


def read_ownerless_closeout_reservation(*, record_root: Path, path: Path) -> dict[str, object]:
    """Read and validate one inventory-visible ownerless reservation."""
    return _read_ownerless_reservation(record_root, path)


def release_ownerless_closeout_reservation(
    *,
    root: Path,
    expected: dict[str, object],
    artifact_root: Path | None = None,
) -> None:
    """Release only after an exact immutable ownerless completion receipt exists."""
    expected_payload = _validated_ownerless_reservation(expected, initial=True)
    record_root = artifact_root or current_record_root(root)
    reservation = ownerless_closeout_reservation_path(
        root,
        str(expected_payload["target_digest"]),
        artifact_root=record_root,
    )
    with _locked_ownerless_reservation(record_root, reservation) as descriptor:
        current = _read_locked_ownerless_reservation(descriptor)
        binding = _ownerless_closeout_recovery_binding(
            current=current,
            expected=expected_payload,
        )
        completion = receipt_path(
            root,
            str(expected_payload["decision_id"]),
            artifact_root=record_root,
        )
        try:
            receipt_bytes = read_record_bytes(completion, record_root=record_root)
            receipt = json.loads(receipt_bytes)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(_OWNERLESS_RESERVATION_RELEASE_INVALID) from error
        _validate_ownerless_completion_receipt(
            root=root,
            receipt=receipt,
            receipt_bytes=receipt_bytes,
            expected=expected_payload,
            binding=binding,
        )
        require_locked_record_identity(
            reservation,
            descriptor,
            record_root=record_root,
        )
        remove_record(
            reservation,
            expected=current,
            record_root=record_root,
            locked_descriptor=descriptor,
        )


def release_ownerless_no_effect_reservation(
    *,
    root: Path,
    expected: dict[str, object],
    artifact_root: Path | None = None,
) -> None:
    """Release only one exact reservation whose destructive effect never started."""
    expected_payload = _validated_ownerless_reservation(expected, initial=True)
    record_root = artifact_root or current_record_root(root)
    reservation = ownerless_closeout_reservation_path(
        root,
        str(expected_payload["target_digest"]),
        artifact_root=record_root,
    )
    with _locked_ownerless_reservation(record_root, reservation) as descriptor:
        current = _read_locked_ownerless_reservation(descriptor)
        if current != expected_payload:
            raise ValueError(_OWNERLESS_RESERVATION_MISMATCH)
        require_locked_record_identity(
            reservation,
            descriptor,
            record_root=record_root,
        )
        remove_record(
            reservation,
            expected=current,
            record_root=record_root,
            locked_descriptor=descriptor,
        )


def _validate_ownerless_completion_receipt(
    *,
    root: Path,
    receipt: object,
    receipt_bytes: bytes,
    expected: dict[str, object],
    binding: dict[str, object],
) -> None:
    try:
        payload = LaneResolutionReceipt.model_validate(receipt).to_payload()
        schema_ok = validate_schema_instance(
            "lane-resolution-receipt.schema.json",
            payload,
            root=root,
        )["ok"]
    except (OSError, TypeError, ValueError) as error:
        raise ValueError(_OWNERLESS_RESERVATION_RELEASE_INVALID) from error
    valid = (
        receipt == payload
        and receipt_bytes == canonical_current_record_bytes(payload)
        and schema_ok
        and payload["state"] == "retired"
        and payload["preservation_package"] == ""
        and payload["preservation_manifest_sha256"] == ""
        and payload["decision_id"] == expected["decision_id"]
        and payload["lane_ref"] == expected["lane_ref"]
        and payload["head"] == expected["head"]
        and payload.get("ownerless_closeout_binding") == binding
    )
    if not valid:
        raise ValueError(_OWNERLESS_RESERVATION_RELEASE_INVALID)


def _validated_ownerless_reservation(
    payload: dict[str, object], *, initial: bool = False
) -> dict[str, object]:
    canonical = validate_ownerless_closeout_reservation(payload)
    if initial and canonical["recovery_state"] != "reserved_no_effect":
        raise ValueError(_OWNERLESS_RESERVATION_INVALID)
    return canonical


def _require_exact_ownerless_binding(
    current: dict[str, object], expected: dict[str, object], error: str
) -> None:
    if any(current.get(field) != expected.get(field) for field in _IMMUTABLE_RESERVATION_FIELDS):
        raise ValueError(error)


def _ownerless_closeout_recovery_binding(
    *, current: dict[str, object], expected: dict[str, object]
) -> dict[str, object]:
    _require_exact_ownerless_binding(current, expected, _OWNERLESS_RECOVERY_BINDING_MISMATCH)
    if current.get("recovery_state") != "effect_complete_receipt_missing":
        raise ValueError(_OWNERLESS_RECOVERY_NOT_FINALIZABLE)
    return OwnerlessCloseoutBinding(
        executor_ref=str(current["executor_ref"]),
        decision_sha256=str(current["decision_sha256"]),
        accepted_branch=str(current["accepted_branch"]),
        accepted_head=str(current["accepted_head"]),
        target_digest=str(current["target_digest"]),
        target_binding_digest=str(current["target_binding_digest"]),
        postcondition_digest=str(current["postcondition_digest"]),
    ).model_dump(mode="json")


@contextmanager
def _locked_ownerless_reservation(record_root: Path, destination: Path) -> Iterator[int]:
    with ExitStack() as stack:
        try:
            descriptor = stack.enter_context(lock_record(destination, record_root=record_root))
        except BlockingIOError as error:
            raise ValueError(_OWNERLESS_RESERVATION_BUSY) from error
        except FileNotFoundError as error:
            raise _ownerless_reservation_invalid() from error
        yield descriptor


def _read_locked_ownerless_reservation(descriptor: int) -> dict[str, object]:
    try:
        content = read_descriptor_bytes(descriptor)
        payload = json.loads(content)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise _ownerless_reservation_invalid() from error
    canonical = validate_ownerless_closeout_reservation(payload)
    if content != canonical_current_record_bytes(canonical):
        raise _ownerless_reservation_invalid()
    return canonical


def _read_ownerless_reservation(record_root: Path, destination: Path) -> dict[str, object]:
    try:
        content = read_record_bytes(destination, record_root=record_root)
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(_OWNERLESS_RESERVATION_INVALID) from error
    canonical = validate_ownerless_closeout_reservation(payload)
    if content != canonical_current_record_bytes(canonical):
        raise ValueError(_OWNERLESS_RESERVATION_INVALID)
    return canonical
