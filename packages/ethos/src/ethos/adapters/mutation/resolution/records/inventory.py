"""Read-only reconciliation inventory for immutable lane-resolution records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.records.clear.quarantine import unsafe_package_path_present
from ethos.adapters.mutation.resolution.records.clear.quarantine import unsafe_record_path_present
from ethos.adapters.mutation.resolution.records.current.core import (
    read_current_lane_resolution_records,
)
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation

if TYPE_CHECKING:
    from pathlib import Path


_CURRENT_RECORD_INVALID = "lane_resolution_current_record_invalid"
_DECISION_RECORD_CONFLICT = "lane_resolution_decision_record_conflict"
_OWNERLESS_DECISION_STALE = "lane_resolution_ownerless_decision_stale"
_OWNERLESS_RESERVATION_COMPETING = "lane_resolution_ownerless_reservation_competing"


def _lane_resolution_inventory(*, root: Path) -> dict[str, object]:
    """Build the reconciliation view from the sole current record root."""
    record_root = current_record_root(root)
    current = read_current_lane_resolution_records(root=root, record_root=record_root)
    decisions = current.decisions
    manifests = current.manifests
    receipts = current.receipts
    clears = current.clears
    clear_quarantines = current.clear_quarantines
    reservations = current.reservations
    receipt_reservations = current.receipt_reservations
    receipt_reservations = {
        decision_id: payload
        for decision_id, payload in receipt_reservations.items()
        if decision_id not in reservations
    }
    conflicts = sorted(current.conflicts)
    invalid_current_record_count = current.invalid_count
    package_ids = set(manifests) | set(clear_quarantines)
    artifact_ids = package_ids | set(receipts) | set(clears) | set(reservations)
    artifact_ids.update(receipt_reservations)
    pending_decision_ids = set(decisions) - artifact_ids
    integrity_ids: list[str] = []
    entries = []
    all_decision_ids = set(decisions) | artifact_ids
    for decision_id in sorted(all_decision_ids):
        decision, manifest, quarantine, receipt, clear = (
            decisions.get(decision_id, {}),
            manifests.get(decision_id, {}),
            clear_quarantines.get(decision_id, {}),
            receipts.get(decision_id, {}),
            clears.get(decision_id, {}),
        )
        reservation = reservations.get(decision_id, {}) or receipt_reservations.get(decision_id, {})
        manifest_sha256 = str(manifest.get("manifest_sha256") or "")
        receipt_manifest_sha256 = str(receipt.get("preservation_manifest_sha256") or "")
        receipt_state = str(receipt.get("state") or "")
        preserved = receipt_state in {
            "preserved",
            "preserved_retirement_blocked",
            "preserved_and_retired",
        }
        has_package = bool(manifest or quarantine)
        inconsistent = bool(
            receipt
            and (
                (preserved and not has_package and not clear)
                or (manifest and manifest_sha256 != receipt_manifest_sha256)
            )
        )
        if inconsistent:
            integrity_ids.append(decision_id)
        recovery_state = str(reservation.get("recovery_state") or "")
        state = (
            "partial_transition"
            if clear and has_package
            else "inconsistent"
            if inconsistent
            else "cleared"
            if clear
            else "partial_transition"
            if reservation and recovery_state != "reserved_no_effect"
            else "inflight"
            if reservation
            else "preserved_retirement_blocked"
            if receipt_state == "preserved_retirement_blocked"
            else "retained"
            if manifest and receipt
            else "receipt_only"
            if receipt
            else "decision_pending"
            if decision_id in pending_decision_ids
            else "unindexed"
        )
        decision_observation = decision.get("observation")
        observation = decision_observation if isinstance(decision_observation, dict) else {}
        entry: dict[str, object] = {
            "decision_id": decision_id,
            "lane_ref": str(
                manifest.get("lane_ref")
                or receipt.get("lane_ref")
                or reservation.get("lane_ref")
                or observation.get("lane_ref")
                or ""
            ),
            "head": str(
                manifest.get("head")
                or receipt.get("head")
                or reservation.get("head")
                or observation.get("head")
                or ""
            ),
            "state": state,
            "receipt_path": str(receipt.get("record_path") or ""),
            "package_path": str(
                manifest.get("package_path")
                or quarantine.get("package_path")
                or receipt.get("preservation_package")
                or ""
            ),
            "manifest_sha256": (
                manifest_sha256
                or str(quarantine.get("manifest_sha256") or "")
                or receipt_manifest_sha256
            ),
        }
        if reservation:
            entry.update(
                reservation_path=str(
                    reservation.get("reservation_path") or reservation.get("record_path") or ""
                ),
                target_digest=str(reservation.get("target_digest") or ""),
                phase=str(reservation.get("phase") or "unknown"),
                recovery_state=recovery_state or "transition_unknown",
            )
        if receipt_state == "preserved_retirement_blocked":
            entry["retirement_blocked_reason"] = str(receipt.get("retirement_blocked_reason") or "")
        entries.append(entry)
    inflight_count = len(reservations) + len(receipt_reservations)
    partial_count = sum(
        str(payload.get("recovery_state") or "") != "reserved_no_effect"
        for payload in [*reservations.values(), *receipt_reservations.values()]
    ) + len(set(clears) & package_ids)
    unsafe_package_path = unsafe_package_path_present(root)
    unsafe_record_path = unsafe_record_path_present(root)
    required_gaps = [
        *(["lane_resolution_decision_record_conflict"] if conflicts else []),
        *(["lane_resolution_manifest_receipt_mismatch"] if integrity_ids else []),
        *(["lane_resolution_package_path_unsafe"] if unsafe_package_path else []),
        *(["lane_resolution_record_path_unsafe"] if unsafe_record_path else []),
        *([_CURRENT_RECORD_INVALID] if invalid_current_record_count else []),
        *(
            ["lane_resolution_partial_transition_present"]
            if partial_count
            else ["lane_resolution_inflight_reservation_present"]
            if inflight_count
            else []
        ),
    ]
    return {
        "ok": not required_gaps,
        "state": "blocked" if required_gaps else "ready",
        "summary": {
            "package_count": len(package_ids),
            "receipt_count": len(receipts),
            "clear_count": len(clears),
            "inflight_count": inflight_count,
            "partial_count": partial_count,
            "decision_count": len(decisions),
            "pending_decision_count": len(pending_decision_ids),
            "invalid_current_record_count": invalid_current_record_count,
        },
        "entries": entries,
        "conflicting_decision_ids": conflicts,
        "integrity_decision_ids": integrity_ids,
        "invalid_current_record_paths": [
            path.absolute().as_posix() for path in current.invalid_paths
        ],
        "required_gaps": required_gaps,
    }


def lane_resolution_inventory(*, root: Path) -> dict[str, object]:
    """Return a read-only reconciliation view over current resolution records."""
    try:
        return _lane_resolution_inventory(root=root)
    except ValueError as error:
        gap = str(error).strip()
        if gap != "lane_resolution_accepted_control_root_unavailable":
            raise
        return {
            "ok": False,
            "state": "blocked",
            "summary": {
                "package_count": 0,
                "receipt_count": 0,
                "clear_count": 0,
                "inflight_count": 0,
                "partial_count": 0,
                "decision_count": 0,
                "pending_decision_count": 0,
                "invalid_current_record_count": 0,
            },
            "entries": [],
            "conflicting_decision_ids": [],
            "integrity_decision_ids": [],
            "invalid_current_record_paths": [],
            "required_gaps": [gap],
        }


def ownerless_closeout_reservation_admission(  # noqa: PLR0913, RUF100 - exact record binding
    *,
    root: Path,
    record_root: Path,
    decision_path: Path,
    decision_sha256: str,
    expected: OwnerlessCloseoutReservation,
    receipt_reservation_decision_id: str | None = None,
) -> OwnerlessCloseoutReservation | None:
    """Classify absence or one exact zero-effect retry reservation."""
    try:
        records = read_current_lane_resolution_records(root=root, record_root=record_root)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise ValueError(_CURRENT_RECORD_INVALID) from error
    if records.invalid_count:
        raise ValueError(_CURRENT_RECORD_INVALID)
    if records.conflicts:
        raise ValueError(_DECISION_RECORD_CONFLICT)
    current = records.decisions.get(expected.decision_id)
    if (
        not current
        or current.get("content_sha256") != decision_sha256
        or current.get("physical_path") != decision_path.absolute()
    ):
        raise ValueError(_OWNERLESS_DECISION_STALE)
    receipt_reservation_ids = set(records.receipt_reservations)
    if (
        receipt_reservation_ids
        if receipt_reservation_decision_id is None
        else receipt_reservation_ids != {receipt_reservation_decision_id}
    ):
        raise ValueError(_OWNERLESS_RESERVATION_COMPETING)
    exact: OwnerlessCloseoutReservation | None = None
    compared = (
        "decision_id",
        "lane_ref",
        "head",
        "executor_ref",
        "decision_sha256",
        "accepted_branch",
        "target_digest",
        "phase",
        "recovery_state",
        "postcondition_digest",
    )
    for projected in records.reservations.values():
        payload = {field: projected[field] for field in OwnerlessCloseoutReservation.model_fields}
        reservation = OwnerlessCloseoutReservation.model_validate(payload, strict=True)
        if reservation.lane_ref != expected.lane_ref:
            continue
        if exact is not None or any(
            getattr(reservation, field) != getattr(expected, field) for field in compared
        ):
            raise ValueError(_OWNERLESS_RESERVATION_COMPETING)
        exact = reservation
    return exact
