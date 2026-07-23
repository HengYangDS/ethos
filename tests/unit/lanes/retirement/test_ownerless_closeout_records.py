from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.records.inventory import LaneResolutionInventoryReaders
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory

if TYPE_CHECKING:
    from pathlib import Path


def _readers(*artifact_roots: Path) -> LaneResolutionInventoryReaders:
    return LaneResolutionInventoryReaders(
        artifact_roots=lambda _root: artifact_roots,
        manifests_with_conflicts=lambda _root: ({}, set()),
        records_with_conflicts=lambda _root, _category, _schema: ({}, set()),
        unsafe_package_path_present=lambda _root: False,
        unsafe_record_path_present=lambda _root: False,
    )


def test_inventory_blocks_symlinked_ownerless_reservation_category(tmp_path: Path) -> None:
    artifact_root = tmp_path / "records"
    target = tmp_path / "outside-reservations"
    artifact_root.mkdir()
    target.mkdir()
    (artifact_root / "reservations").symlink_to(target, target_is_directory=True)

    inventory = lane_resolution_inventory(root=tmp_path, readers=_readers(artifact_root))

    assert inventory["required_gaps"] == ["lane_resolution_target_reservation_invalid"]
    assert inventory["entries"] == []


def test_inventory_filters_unsafe_or_invalid_legacy_receipt_reservations(
    tmp_path: Path,
) -> None:
    symlink_artifact = tmp_path / "symlink-artifact"
    symlink_target = tmp_path / "outside-receipts"
    symlink_artifact.mkdir()
    symlink_target.mkdir()
    (symlink_artifact / "receipts").symlink_to(symlink_target, target_is_directory=True)

    artifact_root = tmp_path / "records"
    receipts = artifact_root / "receipts"
    receipts.mkdir(parents=True)
    (receipts / ".missing.receipt-reservation").symlink_to(tmp_path / "missing")
    (receipts / ".invalid.receipt-reservation").write_text("invalid\n", encoding="utf-8")
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000003"
    (receipts / ".valid.receipt-reservation").write_text(f"{decision_id}\n", encoding="utf-8")

    inventory = lane_resolution_inventory(
        root=tmp_path,
        readers=_readers(symlink_artifact, artifact_root),
    )

    assert inventory["ok"] is False
    assert inventory["summary"]["inflight_count"] == 1
    assert inventory["summary"]["partial_count"] == 1
    assert [entry["decision_id"] for entry in inventory["entries"]] == [decision_id]
    assert inventory["required_gaps"] == ["lane_resolution_partial_transition_present"]
