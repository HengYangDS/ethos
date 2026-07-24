from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.records.inventory as inventory_store
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _patch_inventory_root(monkeypatch: pytest.MonkeyPatch, record_root: Path) -> None:
    monkeypatch.setattr(inventory_store, "current_record_root", lambda _root: record_root)
    monkeypatch.setattr(inventory_store, "unsafe_package_path_present", lambda _root: False)
    monkeypatch.setattr(
        inventory_store,
        "unsafe_record_path_present",
        lambda _root: any(
            (record_root / category).is_symlink()
            for category in ("decisions", "receipts", "clears", "reservations")
        ),
    )


def test_inventory_public_api_has_no_runtime_reader_bag() -> None:
    assert not hasattr(inventory_store, "LaneResolutionInventoryReaders")
    assert tuple(inspect.signature(lane_resolution_inventory).parameters) == ("root",)


def test_inventory_blocks_symlinked_ownerless_reservation_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = tmp_path / "records"
    target = tmp_path / "outside-reservations"
    artifact_root.mkdir()
    target.mkdir()
    (artifact_root / "reservations").symlink_to(target, target_is_directory=True)
    _patch_inventory_root(monkeypatch, artifact_root)

    inventory = lane_resolution_inventory(root=tmp_path)

    assert inventory["required_gaps"] == [
        "lane_resolution_record_path_unsafe",
        "lane_resolution_current_record_invalid",
    ]
    assert inventory["summary"]["invalid_current_record_count"] == 1
    assert inventory["entries"] == []


def test_inventory_filters_unsafe_or_invalid_receipt_reservations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = tmp_path / "records"
    receipts = artifact_root / "receipts"
    receipts.mkdir(parents=True)
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000003"
    outside = tmp_path / "outside-sidecar"
    outside.write_text(f"{decision_id}\n", encoding="utf-8")
    (receipts / ".linked.receipt-reservation").symlink_to(outside)
    (receipts / ".invalid.receipt-reservation").write_text("invalid\n", encoding="utf-8")
    completion = receipt_path(tmp_path, decision_id, artifact_root=artifact_root)
    completion.with_name(f".{completion.stem}.receipt-reservation").write_text(
        f"{decision_id}\n", encoding="utf-8"
    )
    _patch_inventory_root(monkeypatch, artifact_root)

    inventory = lane_resolution_inventory(root=tmp_path)

    assert inventory["ok"] is False
    assert inventory["summary"]["inflight_count"] == 1
    assert inventory["summary"]["partial_count"] == 1
    assert inventory["summary"]["invalid_current_record_count"] == 2
    assert [entry["decision_id"] for entry in inventory["entries"]] == [decision_id]
    assert inventory["required_gaps"] == [
        "lane_resolution_current_record_invalid",
        "lane_resolution_partial_transition_present",
    ]
