"""Read-only reconciliation inventory for immutable lane-resolution records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import valid_decision_id
from ethos.adapters.mutation.resolution.records.core import read_ownerless_closeout_reservation

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


_DECISIONS = "decisions"
_RECEIPTS = "receipts"
_CLEARS = "clears"
_RESERVATIONS = "reservations"


@dataclass(frozen=True, slots=True)
class LaneResolutionInventoryReaders:
    """Filesystem readers used to build one lane-resolution inventory."""

    artifact_roots: Callable[[Path], tuple[Path, ...]]
    manifests_with_conflicts: Callable[[Path], tuple[dict[str, dict[str, object]], set[str]]]
    records_with_conflicts: Callable[[Path, str, str], tuple[dict[str, dict[str, str]], set[str]]]
    unsafe_package_path_present: Callable[[Path], bool]
    unsafe_record_path_present: Callable[[Path], bool]


def lane_resolution_inventory(
    *, root: Path, readers: LaneResolutionInventoryReaders
) -> dict[str, object]:
    """Build the reconciliation view from the current immutable record sources."""
    manifests, manifest_conflicts = readers.manifests_with_conflicts(root)
    _decisions, decision_conflicts = readers.records_with_conflicts(
        root, _DECISIONS, "lane-resolution-decision.schema.json"
    )
    receipts, receipt_conflicts = readers.records_with_conflicts(
        root, _RECEIPTS, "lane-resolution-receipt.schema.json"
    )
    clears, clear_conflicts = readers.records_with_conflicts(
        root, _CLEARS, "lane-resolution-clear-receipt.schema.json"
    )
    reservations, reservation_conflicts, invalid_reservations = (
        _ownerless_reservations_with_conflicts(root, readers.artifact_roots)
    )
    legacy_reservations = {
        decision_id: payload
        for decision_id, payload in _legacy_receipt_reservations(
            root, readers.artifact_roots
        ).items()
        if decision_id not in reservations
    }
    conflicts = sorted(
        manifest_conflicts
        | decision_conflicts
        | receipt_conflicts
        | clear_conflicts
        | reservation_conflicts
    )
    integrity_ids: list[str] = []
    entries = []
    all_decision_ids = (
        set(manifests) | set(receipts) | set(clears) | set(reservations) | set(legacy_reservations)
    )
    for decision_id in sorted(all_decision_ids):
        manifest, receipt, clear = (
            manifests.get(decision_id, {}),
            receipts.get(decision_id, {}),
            clears.get(decision_id, {}),
        )
        reservation = reservations.get(decision_id, {}) or legacy_reservations.get(decision_id, {})
        manifest_sha256 = str(manifest.get("manifest_sha256") or "")
        receipt_manifest_sha256 = str(receipt.get("preservation_manifest_sha256") or "")
        inconsistent = bool(manifest and receipt and manifest_sha256 != receipt_manifest_sha256)
        if inconsistent:
            integrity_ids.append(decision_id)
        recovery_state = str(reservation.get("recovery_state") or "")
        state = (
            "cleared"
            if clear
            else "inconsistent"
            if inconsistent
            else "partial_transition"
            if reservation and recovery_state != "reserved_no_effect"
            else "inflight"
            if reservation
            else "retained"
            if manifest and receipt
            else "receipt_only"
            if receipt
            else "unindexed"
        )
        entry: dict[str, object] = {
            "decision_id": decision_id,
            "lane_ref": str(
                manifest.get("lane_ref")
                or receipt.get("lane_ref")
                or reservation.get("lane_ref")
                or ""
            ),
            "head": str(
                manifest.get("head") or receipt.get("head") or reservation.get("head") or ""
            ),
            "state": state,
            "receipt_path": str(receipt.get("record_path") or ""),
            "package_path": str(
                manifest.get("package_path") or receipt.get("preservation_package") or ""
            ),
            "manifest_sha256": manifest_sha256 or receipt_manifest_sha256,
        }
        if reservation:
            entry.update(
                reservation_path=str(reservation.get("reservation_path") or ""),
                target_digest=str(reservation.get("target_digest") or ""),
                phase=str(reservation.get("phase") or "unknown"),
                recovery_state=recovery_state or "transition_unknown",
            )
        entries.append(entry)
    inflight_count = len(reservations) + len(legacy_reservations)
    partial_count = sum(
        str(payload.get("recovery_state") or "") != "reserved_no_effect"
        for payload in [*reservations.values(), *legacy_reservations.values()]
    )
    unsafe_package_path = readers.unsafe_package_path_present(root)
    unsafe_record_path = readers.unsafe_record_path_present(root)
    required_gaps = [
        *(["lane_resolution_decision_record_conflict"] if conflicts else []),
        *(["lane_resolution_manifest_receipt_mismatch"] if integrity_ids else []),
        *(["lane_resolution_package_path_unsafe"] if unsafe_package_path else []),
        *(["lane_resolution_record_path_unsafe"] if unsafe_record_path else []),
        *(["lane_resolution_target_reservation_invalid"] if invalid_reservations else []),
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
            "package_count": len(manifests),
            "receipt_count": len(receipts),
            "clear_count": len(clears),
            "inflight_count": inflight_count,
            "partial_count": partial_count,
        },
        "entries": entries,
        "conflicting_decision_ids": conflicts,
        "integrity_decision_ids": integrity_ids,
        "required_gaps": required_gaps,
    }


def _ownerless_reservations_with_conflicts(
    root: Path, artifact_roots: Callable[[Path], tuple[Path, ...]]
) -> tuple[dict[str, dict[str, object]], set[str], list[str]]:
    records: dict[str, dict[str, object]] = {}
    conflicts: set[str] = set()
    invalid: list[str] = []
    for artifact_root in artifact_roots(root):
        category_root = artifact_root / _RESERVATIONS
        if category_root.is_symlink():
            invalid.append(display_path(root, category_root))
            continue
        for path in sorted(category_root.glob("*.json")):
            try:
                payload = read_ownerless_closeout_reservation(record_root=artifact_root, path=path)
            except (OSError, TypeError, ValueError):
                invalid.append(display_path(root, path))
                continue
            decision_id = str(payload["decision_id"])
            projected = {**payload, "reservation_path": display_path(root, path)}
            existing = records.get(decision_id)
            existing_payload = (
                {field: value for field, value in existing.items() if field != "reservation_path"}
                if existing
                else None
            )
            if existing_payload is not None and existing_payload != payload:
                conflicts.add(decision_id)
                continue
            records.setdefault(decision_id, projected)
    return records, conflicts, invalid


def _legacy_receipt_reservations(
    root: Path, artifact_roots: Callable[[Path], tuple[Path, ...]]
) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for artifact_root in artifact_roots(root):
        receipt_root = artifact_root / _RECEIPTS
        if receipt_root.is_symlink():
            continue
        for path in sorted(receipt_root.glob(".*.receipt-reservation")):
            try:
                decision_id = path.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if not valid_decision_id(decision_id):
                continue
            records.setdefault(
                decision_id,
                {
                    "decision_id": decision_id,
                    "reservation_path": display_path(root, path),
                    "phase": "unknown",
                    "recovery_state": "transition_unknown",
                },
            )
    return records
