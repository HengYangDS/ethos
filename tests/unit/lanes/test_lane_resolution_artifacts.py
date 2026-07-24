from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.lane as lane_adapter
import ethos.adapters.mutation.resolution.receipts as receipt_adapter
import ethos.adapters.mutation.resolution.records.clear.core as clear_adapter
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.inventory as record_inventory
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.receipts import read_resolution_receipt
from ethos.adapters.mutation.resolution.receipts import verify_preservation_package
from ethos.adapters.mutation.resolution.receipts import write_resolution_receipt
from ethos.adapters.mutation.resolution.records.clear.core import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.records.clear.core import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.mutation.resolution.records.roots import historical_record_roots
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import orphan_work_lane

_LEGACY_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"
_CARRIER_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000002"
_RESERVATION_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000003"
_OWNERLESS_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000004"
_COMPETING_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000005"


def _ownerless_reservation(*, decision_id: str = _OWNERLESS_DECISION_ID) -> dict[str, object]:
    lane_ref, head = "work/20260722-ownerless", "a" * 40
    return {
        "schema_version": 2,
        "decision_id": decision_id,
        "lane_ref": lane_ref,
        "head": head,
        "executor_ref": "agent:codex:thread:executor",
        "decision_sha256": "b" * 64,
        "accepted_branch": "dev",
        "accepted_head": "c" * 40,
        "target_digest": target_digest(lane_ref, head),
        "target_binding_digest": "e" * 64,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }


def _ownerless_receipt(binding: dict[str, object] | None) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 3,
        "receipt_id": "lane-resolution-receipt:ownerless",
        "decision_id": _OWNERLESS_DECISION_ID,
        "completed": True,
        "state": "retired",
        "observation_digest": "e" * 64,
        "reconciliation_required": False,
        "lane_ref": "work/20260722-ownerless",
        "head": "a" * 40,
        "preservation_package": "",
        "preservation_manifest_sha256": "",
        "mints_authority": False,
    }
    if binding is not None:
        payload["ownerless_closeout_binding"] = binding
    return payload


def _preserve(repo: Path, lane: Path) -> dict[str, object]:
    (lane / "README.md").write_text("# preserved\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve recoverable owner-unknown work.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-artifacts", token="preserve"
        ),
        recovery_plan="Preserve the exact observed state before any later judgment.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    assert planned["ok"] is True
    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )
    assert applied["ok"] is True
    return applied


def _plan_block(repo: Path, decision_path: Path) -> dict[str, object]:
    return plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Block this exact observed lane state.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-artifacts", token="block"
        ),
        recovery_plan="Keep the lane unchanged until a current decision is recorded.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )


def test_plan_rejects_traversal_spelled_historical_decision_path(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    historical = historical_record_roots(repo)[0] / "decisions/traversal-plan.json"
    traversal = current_record_root(repo) / ".." / "lane-resolution/decisions/traversal-plan.json"

    report = _plan_block(repo, traversal)

    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_decision_path_not_local_artifact"]
    assert not historical.exists()


def test_read_and_apply_reject_traversal_spelled_historical_decision(
    tmp_path: Path,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    current_decision = _default_decision_path(repo, "work/orphan")
    planned = _plan_block(repo, current_decision)
    assert planned["ok"] is True
    historical = historical_record_roots(repo)[0] / "decisions/traversal-apply.json"
    historical.parent.mkdir(parents=True, exist_ok=True)
    historical.write_bytes(current_decision.read_bytes())
    traversal = current_record_root(repo) / ".." / "lane-resolution/decisions/traversal-apply.json"

    decision, gaps = lane_adapter._read_decision(traversal, root=repo)  # noqa: SLF001, RUF100 - regression covers the private reader boundary
    report = apply_lane_resolution(
        root=repo,
        decision_path=traversal,
        confirm_irreversible=False,
        apply=False,
    )

    assert decision == {}
    assert gaps == ["lane_resolution_decision_path_not_local_artifact"]
    assert report["ok"] is False
    assert "lane_resolution_decision_path_not_local_artifact" in report["required_gaps"]


def test_resolution_materializes_immutable_receipt_and_inventory(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)

    receipt = applied["receipt"]
    receipt_path = repo / str(applied["receipt_path"])
    assert receipt_path.is_file()
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is True
    assert inventory["summary"] == {
        "package_count": 1,
        "receipt_count": 1,
        "clear_count": 0,
        "inflight_count": 0,
        "partial_count": 0,
        "decision_count": 1,
        "pending_decision_count": 0,
        "invalid_current_record_count": 0,
    }
    assert inventory["entries"] == [
        {
            "decision_id": receipt["decision_id"],
            "lane_ref": "work/orphan",
            "head": receipt["head"],
            "state": "retained",
            "receipt_path": str(applied["receipt_path"]),
            "package_path": str(applied["preservation_package"]["path"]),
            "manifest_sha256": receipt["preservation_manifest_sha256"],
        }
    ]


def test_inventory_exposes_decision_only_as_pending(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _plan_block(repo, decision_path)

    inventory = lane_resolution_inventory(root=repo)

    assert planned["ok"] is True
    assert inventory["ok"] is True
    assert inventory["summary"] == {
        "package_count": 0,
        "receipt_count": 0,
        "clear_count": 0,
        "inflight_count": 0,
        "partial_count": 0,
        "decision_count": 1,
        "pending_decision_count": 1,
        "invalid_current_record_count": 0,
    }
    assert inventory["entries"] == [
        {
            "decision_id": planned["decision"]["decision_id"],
            "lane_ref": "work/orphan",
            "head": planned["decision"]["observation"]["head"],
            "state": "decision_pending",
            "receipt_path": "",
            "package_path": "",
            "manifest_sha256": "",
        }
    ]


def test_resolution_receipt_refuses_to_overwrite_existing_decision(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)

    with pytest.raises(FileExistsError):
        write_resolution_receipt(root=repo, receipt=applied["receipt"])


def test_resolution_receipt_reservation_reports_an_exact_existing_owner_as_busy(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")

    reservation = record_store.reserve_resolution_receipt(
        root=repo,
        decision_id=_RESERVATION_DECISION_ID,
    )

    assert reservation.is_file()
    assert reservation.name.startswith(".")
    assert reservation.name.endswith(".receipt-reservation")
    with pytest.raises(FileExistsError):
        record_store.reserve_resolution_receipt(
            root=repo,
            decision_id=_RESERVATION_DECISION_ID,
        )
    assert reservation.is_file()

    record_store.release_resolution_receipt_reservation(
        root=repo,
        decision_id=_RESERVATION_DECISION_ID,
    )
    assert not reservation.exists()


def test_resolution_receipt_reservation_rejects_drifted_existing_sidecar(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = record_store.reserve_resolution_receipt(
        root=repo,
        decision_id=_RESERVATION_DECISION_ID,
    )
    reservation.write_text(f"{_COMPETING_DECISION_ID}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        record_store.reserve_resolution_receipt(
            root=repo,
            decision_id=_RESERVATION_DECISION_ID,
        )


def test_resolution_receipt_reservation_rejects_symlinked_existing_sidecar(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    reservation = record_store.reserve_resolution_receipt(
        root=repo,
        decision_id=_RESERVATION_DECISION_ID,
    )
    reservation.unlink()
    reservation.symlink_to(tmp_path / "missing-sidecar")

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.reserve_resolution_receipt(
            root=repo,
            decision_id=_RESERVATION_DECISION_ID,
        )


def test_current_inventory_ignores_historical_manifests(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    carrier = tmp_path / "repo-work-carrier"
    git(repo, "worktree", "add", "-b", "work/carrier", carrier.as_posix(), "dev")

    for index, record_root in enumerate(historical_record_roots(repo), start=1):
        package = record_root / f"historical-{index}"
        package.mkdir(parents=True)
        manifest = {
            "decision_id": f"lane-decision:00000000-0000-4000-8000-{index:012d}",
            "lane_ref": f"work/historical-{index}",
            "head": "a" * 40,
            "observation_digest": "b" * 64,
            "bundle_sha256": "c" * 64,
            "patch_sha256": "d" * 64,
            "untracked_archive_sha256": "",
            "source_lease_transferred": False,
        }
        (package / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is True
    assert inventory["entries"] == []
    assert inventory["summary"]["invalid_current_record_count"] == 0


def test_current_inventory_ignores_invalid_historical_payloads(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    for index, record_root in enumerate(historical_record_roots(repo), start=1):
        invalid = record_root / "receipts" / f"invalid-{index}.json"
        invalid.parent.mkdir(parents=True, exist_ok=True)
        invalid.write_text("not json", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is True
    assert inventory["entries"] == []
    assert inventory["summary"]["invalid_current_record_count"] == 0


@pytest.mark.parametrize(
    "relative_path",
    [
        "receipts/nonregular.json",
        f"receipts/.{_RESERVATION_DECISION_ID}.receipt-reservation",
    ],
)
def test_current_inventory_rejects_non_regular_payload_without_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
) -> None:
    repo = init_repo(tmp_path / "repo")
    payload_path = current_record_root(repo) / relative_path
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(payload_path)
    real_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if path == payload_path:
            pytest.fail("non-regular current payload must not be opened")
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 1
    assert inventory["invalid_current_record_paths"] == [payload_path.absolute().as_posix()]
    assert inventory["required_gaps"] == ["lane_resolution_current_record_invalid"]


def test_current_inventory_ignores_conflicting_historical_manifest(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    manifest = dict(applied["preservation_package"]["manifest"])
    manifest["head"] = "f" * 40
    historical = historical_record_roots(repo)[-1] / "conflicting/manifest.json"
    historical.parent.mkdir(parents=True)
    historical.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is True
    assert inventory["conflicting_decision_ids"] == []
    assert [entry["decision_id"] for entry in inventory["entries"]] == [
        applied["receipt"]["decision_id"]
    ]


def test_exact_invalid_receipt_blocks_apply_before_recovery_or_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _plan_block(repo, decision_path)
    decision_id = str(planned["decision"]["decision_id"])
    invalid = record_store.receipt_path(repo, decision_id)
    invalid.parent.mkdir(parents=True)
    invalid.write_text("not json", encoding="utf-8")
    calls = {"recovery": 0, "effect": 0}

    def record_recovery(*_args: object, **_kwargs: object):
        calls["recovery"] += 1
        return {}, None, None, ""

    def record_effect(*_args: object, **_kwargs: object) -> None:
        calls["effect"] += 1

    monkeypatch.setattr(lane_adapter, "ownerless_recovery_context", record_recovery)
    monkeypatch.setattr(lane_adapter, "apply_resolution", record_effect)

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert report["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert calls == {"recovery": 0, "effect": 0}
    assert lane.is_dir()


def test_exact_noncanonical_decision_blocks_apply_before_recovery_or_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _plan_block(repo, decision_path)
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    calls = {"recovery": 0, "effect": 0}

    def record_recovery(
        *_args: object, **_kwargs: object
    ) -> tuple[dict[str, object], Path | None, Path | None, str]:
        calls["recovery"] += 1
        return {}, None, None, ""

    def record_effect(*_args: object, **_kwargs: object) -> None:
        calls["effect"] += 1

    monkeypatch.setattr(lane_adapter, "ownerless_recovery_context", record_recovery)
    monkeypatch.setattr(lane_adapter, "apply_resolution", record_effect)

    inventory = lane_resolution_inventory(root=repo)
    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert planned["ok"] is True
    assert inventory["summary"]["invalid_current_record_count"] == 1
    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert calls == {"recovery": 0, "effect": 0}
    assert lane.is_dir()


def test_exact_non_regular_decision_blocks_apply_without_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = _plan_block(repo, decision_path)
    decision_path.unlink()
    os.mkfifo(decision_path)
    real_read_bytes = Path.read_bytes
    calls = {"recovery": 0, "effect": 0}

    def guarded_read_bytes(path: Path) -> bytes:
        if path == decision_path:
            pytest.fail("non-regular decision must not be opened")
        return real_read_bytes(path)

    def record_recovery(
        *_args: object, **_kwargs: object
    ) -> tuple[dict[str, object], Path | None, Path | None, str]:
        calls["recovery"] += 1
        return {}, None, None, ""

    def record_effect(*_args: object, **_kwargs: object) -> None:
        calls["effect"] += 1

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(lane_adapter, "ownerless_recovery_context", record_recovery)
    monkeypatch.setattr(lane_adapter, "apply_resolution", record_effect)

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert planned["ok"] is True
    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert calls == {"recovery": 0, "effect": 0}
    assert lane.is_dir()


def test_current_receipt_reader_does_not_fallback_to_history(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    carrier = tmp_path / "repo-work-carrier"
    git(repo, "worktree", "add", "-b", "work/carrier", carrier.as_posix(), "dev")
    receipt = _ownerless_receipt(None)

    for record_root in historical_record_roots(repo):
        destination = record_store.receipt_path(
            repo,
            _OWNERLESS_DECISION_ID,
            artifact_root=record_root,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    assert read_resolution_receipt(root=repo, decision_id=_OWNERLESS_DECISION_ID) is None


def test_clear_does_not_select_or_delete_historical_package(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    package = historical_record_roots(repo)[0] / _LEGACY_DECISION_ID
    package.mkdir(parents=True)
    manifest = {
        "decision_id": _LEGACY_DECISION_ID,
        "lane_ref": "work/historical",
        "head": "a" * 40,
        "observation_digest": "b" * 64,
        "bundle_sha256": "c" * 64,
        "patch_sha256": "d" * 64,
        "untracked_archive_sha256": "",
        "source_lease_transferred": False,
    }
    manifest_path = package / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=_LEGACY_DECISION_ID,
            expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-artifacts", token="clear-preservation"
            ),
            reason="Historical bytes never authorize current clear.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["ok"] is False
    assert "lane_resolution_clear_package_missing" in report["required_gaps"]
    assert package.is_dir()


@pytest.mark.parametrize("invalid_location", ["unrelated", "exact_receipt"])
def test_clear_blocks_any_invalid_current_payload_before_delete(
    tmp_path: Path,
    invalid_location: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    invalid = (
        record_store.receipt_path(repo, decision_id)
        if invalid_location == "exact_receipt"
        else current_record_root(repo) / "receipts" / "unrelated-invalid.json"
    )
    invalid.parent.mkdir(parents=True, exist_ok=True)
    invalid.write_text("not json", encoding="utf-8")

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-artifacts", token="clear-preservation"
            ),
            reason="Current-record corruption blocks irreversible package deletion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert package.is_dir()
    assert not record_store.clear_receipt_path(repo, decision_id).exists()


def test_inventory_and_verify_bind_actual_manifest_to_immutable_receipt(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered["head"] = "f" * 40
    manifest_path.write_text(
        json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["required_gaps"] == [
        "lane_resolution_manifest_receipt_mismatch",
        "lane_resolution_current_record_invalid",
    ]
    with pytest.raises(ValueError, match="lane_resolution_preservation_package_invalid"):
        verify_preservation_package(root=repo, package=applied["preservation_package"])


def test_inventory_and_clear_block_symlinked_current_package(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package_link = Path(str(applied["preservation_package"]["path"]))
    outside = tmp_path / "current-outside"
    package_link.rename(outside)
    link_target = outside
    manifest_path = outside / "manifest.json"
    package_link.symlink_to(link_target, target_is_directory=True)
    marker = link_target / "must-survive.txt"
    marker.write_text("retained\n", encoding="utf-8")
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    inventory = lane_resolution_inventory(root=repo)
    cleared = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-artifacts", token="clear-preservation"
            ),
            reason="A symlinked package must never authorize external deletion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert inventory["ok"] is False
    assert set(inventory["required_gaps"]) == {
        "lane_resolution_package_path_unsafe",
        "lane_resolution_current_record_invalid",
    }
    assert "lane_resolution_current_record_invalid" in cleared["required_gaps"]
    assert package_link.is_symlink()
    assert marker.read_text(encoding="utf-8") == "retained\n"


def test_clear_blocks_receipt_with_empty_manifest_digest(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    receipt_path = Path(str(applied["receipt_path"]))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["preservation_manifest_sha256"] = ""
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=str(applied["receipt"]["decision_id"]),
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-artifacts", token="clear-preservation"
            ),
            reason="An empty receipt digest cannot authorize deletion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert package.is_dir()


def test_resolution_receipt_write_blocks_symlinked_record_category(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    (lane / "README.md").write_text("# preserve safely\n", encoding="utf-8")
    artifact_root = current_record_root(repo)
    artifact_root.mkdir(parents=True)
    outside = tmp_path / "receipt-outside"
    outside.mkdir()
    (artifact_root / "receipts").symlink_to(outside, target_is_directory=True)
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Record destinations must not follow symlinks.",
        evidence_refs=("evidence:review",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-artifacts", token="preserve"
        ),
        recovery_plan="Block before writing a receipt outside the records owner.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    applied = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert planned["ok"] is True
    assert applied["ok"] is False
    assert applied["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert list(outside.iterdir()) == []


def test_manual_clear_requires_exact_chronicle_and_manifest_binding(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = repo / str(applied["preservation_package"]["path"])
    manifest_path = package / "manifest.json"
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    decision_id = str(applied["receipt"]["decision_id"])

    blocked = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-artifacts", token="clear-preservation"
            ),
            reason="",
            break_glass=False,
            confirm_irreversible=False,
            apply=True,
        ),
    )

    assert blocked["ok"] is False
    assert set(blocked["required_gaps"]) >= {
        "lane_resolution_clear_reason_required",
        "lane_resolution_clear_requires_break_glass",
        "irreversible_confirmation_required",
    }
    assert package.is_dir()

    cleared = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref="evidence/chronicle/lane-resolution-artifacts/clear-preservation.md",
            reason="Retention review accepted deletion of this exact package.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert cleared["ok"] is True
    assert cleared["state"] == "cleared"
    assert not package.exists()
    assert (repo / str(cleared["clear_receipt_path"])).is_file()
    inventory = lane_resolution_inventory(root=repo)
    assert inventory["summary"] == {
        "package_count": 0,
        "receipt_count": 1,
        "clear_count": 1,
        "inflight_count": 0,
        "partial_count": 0,
        "decision_count": 1,
        "pending_decision_count": 0,
        "invalid_current_record_count": 0,
    }
    assert inventory["entries"][0]["state"] == "cleared"


def test_manual_clear_reports_missing_package_and_manifest_mismatch(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id="lane-decision:missing",
            expect_manifest_sha256="a" * 64,
            chronicle_ref="evidence/chronicle/missing.md",
            reason="Preservation review requires an exact retained package.",
            break_glass=True,
            confirm_irreversible=True,
            apply=False,
        ),
    )

    assert set(report["required_gaps"]) >= {
        "lane_resolution_clear_package_missing",
        "lane_resolution_clear_manifest_mismatch",
    }


def test_manual_clear_removal_failure_keeps_quarantine_and_clear_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = repo / str(applied["preservation_package"]["path"])
    metadata = package.stat(follow_symlinks=False)
    package_identity = metadata.st_dev, metadata.st_ino, metadata.st_mode
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    decision_id = str(applied["receipt"]["decision_id"])
    chronicle_ref = write_chronicle_decision(
        repo, topic="lane-resolution-artifacts", token="clear-preservation"
    )

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", lambda **_kwargs: False)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=chronicle_ref,
            reason="The removal path is deliberately exercised before promotion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["required_gaps"] == ["lane_resolution_clear_remove_failed"]
    assert report["state"] == "partial_transition"
    assert not package.exists()
    assert record_store.clear_quarantine_path(repo, decision_id, package_identity).is_dir()
    assert record_store.clear_receipt_path(repo, decision_id).is_file()


def test_receipt_schema_validator_rejects_invalid_schema(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        receipt_adapter._validate_schema(  # noqa: RUF100, SLF001 - coverage exercises schema refusal
            repo, "lane-resolution-receipt.schema.json", {}
        )


def test_inventory_and_clear_block_when_records_owner_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = ValueError("lane_resolution_accepted_control_root_unavailable")
    for module in (clear_adapter, record_inventory):
        monkeypatch.setattr(
            module, "current_record_root", lambda _root: (_ for _ in ()).throw(error)
        )

    inventory = lane_resolution_inventory(root=tmp_path)
    cleared = clear_lane_resolution_package(
        root=tmp_path,
        request=LaneResolutionClearRequest(
            decision_id=_LEGACY_DECISION_ID,
            expect_manifest_sha256="a" * 64,
            chronicle_ref="evidence/chronicle/missing.md",
            reason="Bounded owner-unavailable check.",
            break_glass=True,
            confirm_irreversible=True,
            apply=False,
        ),
    )

    assert inventory["required_gaps"] == ["lane_resolution_accepted_control_root_unavailable"]
    assert cleared["required_gaps"] == ["lane_resolution_accepted_control_root_unavailable"]

    for module in (clear_adapter, record_inventory):
        monkeypatch.setattr(
            module,
            "current_record_root",
            lambda _root: (_ for _ in ()).throw(ValueError("unexpected")),
        )
    with pytest.raises(ValueError, match="unexpected"):
        lane_resolution_inventory(root=tmp_path)


def test_clear_chronicle_rejects_outside_missing_and_mismatched_records(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    outside = tmp_path / "outside.md"
    outside.write_text("decision: lane_resolution/clear-preservation\n", encoding="utf-8")
    mismatch = repo / "evidence/chronicle/lane-resolution-artifacts/mismatch.md"
    mismatch.parent.mkdir(parents=True)
    mismatch.write_text("decision: lane_resolution/preserve\n", encoding="utf-8")

    assert clear_adapter._clear_chronicle(  # noqa: RUF100, SLF001 - coverage exercises Chronicle boundary refusal
        repo, outside.as_posix()
    )[2] == ["lane_resolution_clear_chronicle_outside_repository"]
    assert clear_adapter._clear_chronicle(  # noqa: RUF100, SLF001 - coverage exercises missing Chronicle refusal
        repo, "evidence/chronicle/missing.md"
    )[2] == ["lane_resolution_clear_chronicle_missing"]
    assert clear_adapter._clear_chronicle(  # noqa: RUF100, SLF001 - coverage exercises Chronicle token refusal
        repo, "evidence/chronicle/lane-resolution-artifacts/mismatch.md"
    )[2] == ["lane_resolution_clear_chronicle_disposition_mismatch"]
