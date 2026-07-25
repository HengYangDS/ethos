"""Read-only reconciliation inventory for lane-resolution records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution._shared import display_path
from ethos.adapters.mutation.resolution._shared import valid_decision_id

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_DECISIONS = "decisions"
_RECEIPTS = "receipts"
_CLEARS = "clears"


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
    """Build one compact reconciliation view from immutable record sources."""
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
    pending, invalid_pending = _pending_receipts(root, readers.artifact_roots)
    conflicts = sorted(
        manifest_conflicts | decision_conflicts | receipt_conflicts | clear_conflicts
    )
    integrity_ids: list[str] = []
    entries = []
    for decision_id in sorted(set(manifests) | set(receipts) | set(clears) | set(pending)):
        manifest = manifests.get(decision_id, {})
        receipt = receipts.get(decision_id, {})
        clear = clears.get(decision_id, {})
        manifest_sha256 = str(manifest.get("manifest_sha256") or "")
        receipt_manifest_sha256 = str(receipt.get("preservation_manifest_sha256") or "")
        inconsistent = bool(manifest and receipt and manifest_sha256 != receipt_manifest_sha256)
        if inconsistent:
            integrity_ids.append(decision_id)
        state = (
            "cleared"
            if clear
            else "inconsistent"
            if inconsistent
            else "pending_receipt"
            if decision_id in pending
            else "retained"
            if manifest and receipt
            else "receipt_only"
            if receipt
            else "unindexed"
        )
        entry: dict[str, object] = {
            "decision_id": decision_id,
            "lane_ref": str(manifest.get("lane_ref") or receipt.get("lane_ref") or ""),
            "head": str(manifest.get("head") or receipt.get("head") or ""),
            "state": state,
            "receipt_path": str(receipt.get("record_path") or ""),
            "package_path": str(
                manifest.get("package_path") or receipt.get("preservation_package") or ""
            ),
            "manifest_sha256": manifest_sha256 or receipt_manifest_sha256,
        }
        if decision_id in pending:
            entry["pending_receipt_path"] = pending[decision_id]
        entries.append(entry)
    unsafe_package_path = readers.unsafe_package_path_present(root)
    unsafe_record_path = readers.unsafe_record_path_present(root)
    required_gaps = [
        *(["lane_resolution_decision_record_conflict"] if conflicts else []),
        *(["lane_resolution_manifest_receipt_mismatch"] if integrity_ids else []),
        *(["lane_resolution_package_path_unsafe"] if unsafe_package_path else []),
        *(["lane_resolution_record_path_unsafe"] if unsafe_record_path or invalid_pending else []),
        *(["lane_resolution_receipt_pending"] if pending else []),
    ]
    return {
        "ok": not required_gaps,
        "state": "blocked" if required_gaps else "ready",
        "summary": {
            "package_count": len(manifests),
            "receipt_count": len(receipts),
            "clear_count": len(clears),
            "pending_count": len(pending),
        },
        "entries": entries,
        "conflicting_decision_ids": conflicts,
        "integrity_decision_ids": integrity_ids,
        "required_gaps": required_gaps,
    }


def _pending_receipts(
    root: Path, artifact_roots: Callable[[Path], tuple[Path, ...]]
) -> tuple[dict[str, str], bool]:
    records: dict[str, str] = {}
    invalid = False
    for artifact_root in artifact_roots(root):
        receipt_root = artifact_root / _RECEIPTS
        if receipt_root.is_symlink():
            invalid = True
            continue
        for path in sorted(receipt_root.glob(".*.receipt-reservation")):
            if path.is_symlink():
                invalid = True
                continue
            try:
                decision_id = path.read_text(encoding="utf-8").strip()
            except OSError:
                invalid = True
                continue
            if not valid_decision_id(decision_id):
                invalid = True
                continue
            records.setdefault(decision_id, display_path(root, path))
    return records, invalid
