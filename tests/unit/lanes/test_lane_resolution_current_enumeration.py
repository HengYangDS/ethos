from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.records.current.validators import cross_record_invalid_paths
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.json_store import canonical_current_record_bytes
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from tests.support.lane_helpers import orphan_work_lane
from tests.unit.lanes.resolution.records import preserve_lane

if TYPE_CHECKING:
    from pathlib import Path


def test_inventory_rejects_an_unadmitted_current_node(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    node = current_record_root(repo) / "unadmitted"
    node.parent.mkdir(parents=True, exist_ok=True)
    node.write_text("not admitted\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 1
    assert inventory["required_gaps"] == ["lane_resolution_current_record_invalid"]


def test_inventory_rejects_cross_record_binding_mismatch(tmp_path: Path) -> None:
    decision_id = "lane-decision:123e4567-e89b-12d3-a456-426614174000"
    observation = {"lane_ref": "work/orphan", "head": "a" * 40}
    decision = {
        "observation": observation,
        "observation_digest": "observation",
        "content_sha256": "decision",
        "disposition": "preserve-retire",
        "break_glass": False,
    }
    manifest_path = tmp_path / "manifest.json"
    receipt_path = tmp_path / "receipt.json"
    reservation_path = tmp_path / "reservation.json"
    manifest = {
        "physical_path": manifest_path,
        "lane_ref": observation["lane_ref"],
        "head": observation["head"],
        "observation_digest": "observation",
        "manifest_sha256": "manifest",
        "quarantined": False,
    }
    receipt = {
        "physical_path": receipt_path,
        "lane_ref": observation["lane_ref"],
        "head": observation["head"],
        "observation_digest": "observation",
        "state": "preserved_retirement_blocked",
        "reconciliation_required": False,
        "preservation_manifest_sha256": "manifest",
    }
    reservation = {
        "physical_path": reservation_path,
        "lane_ref": observation["lane_ref"],
        "head": observation["head"],
        "decision_sha256": "decision",
    }

    assert (
        cross_record_invalid_paths(
            decisions={decision_id: decision},
            manifests={decision_id: manifest},
            receipts={decision_id: receipt},
            clears={},
            reservations={decision_id: reservation},
        )
        == []
    )
    assert cross_record_invalid_paths(
        decisions={decision_id: decision},
        manifests={decision_id: {**manifest, "lane_ref": "work/mismatch"}},
        receipts={decision_id: receipt},
        clears={},
        reservations={decision_id: reservation},
    ) == [manifest_path]
    assert cross_record_invalid_paths(
        decisions={decision_id: decision},
        manifests={decision_id: manifest},
        receipts={decision_id: {**receipt, "head": "b" * 40}},
        clears={},
        reservations={decision_id: reservation},
    ) == [receipt_path]
    assert cross_record_invalid_paths(
        decisions={decision_id: decision},
        manifests={decision_id: manifest},
        receipts={decision_id: receipt},
        clears={},
        reservations={decision_id: {**reservation, "decision_sha256": "mismatch"}},
    ) == [reservation_path]

    repo, lane = orphan_work_lane(tmp_path / "inventory")
    preserve_lane(repo, lane)
    record_root = current_record_root(repo)
    stored_manifest = next(record_root.glob("*/manifest.json"))
    payload = json.loads(stored_manifest.read_text(encoding="utf-8"))
    payload["lane_ref"] = "work/mismatch"
    stored_manifest.write_bytes(canonical_current_record_bytes(payload))

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] >= 1
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]
