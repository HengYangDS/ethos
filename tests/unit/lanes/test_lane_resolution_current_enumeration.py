from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.lane as lane_adapter
import ethos.adapters.mutation.resolution.records.clear.core as clear_adapter
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.current.snapshot as current_snapshot
from ethos.adapters.mutation.resolution.lane import apply_lane_resolution
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.records.clear.core import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.records.clear.core import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import orphan_work_lane

_PACKAGE_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000401"


def _entry_identity(path: Path) -> tuple[int, int, int]:
    metadata = path.stat(follow_symlinks=False)
    return metadata.st_dev, metadata.st_ino, metadata.st_mode


def _plan_block(repo: Path) -> tuple[Path, dict[str, object]]:
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Keep this exact lane unchanged.",
        evidence_refs=("evidence:current-enumeration",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="block"
        ),
        recovery_plan="Block until every current physical payload is valid.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )
    assert planned["ok"] is True
    return decision_path, planned


def _preserve(repo: Path, lane: Path) -> dict[str, object]:
    (lane / "README.md").write_text("# preserve\n", encoding="utf-8")
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="preserve",
        reason="Preserve this exact lane state.",
        evidence_refs=("evidence:current-enumeration",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="preserve"
        ),
        recovery_plan="Retain the exact observed bytes.",
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


def _plan_ownerless_retire(repo: Path) -> tuple[Path, dict[str, object]]:
    decision_path = _default_decision_path(repo, "work/orphan")
    planned = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="retire",
        reason="Retire this exact clean ownerless lane.",
        evidence_refs=("evidence:current-enumeration",),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="retire"
        ),
        recovery_plan="Bind the exact ownerless closeout before effect.",
        decision_path=decision_path,
        break_glass=True,
        apply=True,
    )
    assert planned["ok"] is True
    return decision_path, planned


def _install_unadmitted_node(record_root: Path, layout: str) -> Path:
    if layout in {"category_file", "category_fifo", "category_symlink"}:
        path = record_root / "reservations"
    elif layout in {"wrong_suffix", "nested_record"}:
        path = record_root / "receipts" / ("bad.txt" if layout == "wrong_suffix" else "nested")
    elif layout in {"stray_file", "stray_fifo"}:
        path = record_root / "stray"
    else:
        package = record_root / _PACKAGE_DECISION_ID
        path = (
            package
            if layout == "missing_manifest"
            else package / ("manifest.txt" if layout == "wrong_manifest_name" else "manifest.json")
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    if layout in {"category_fifo", "stray_fifo", "manifest_fifo"}:
        os.mkfifo(path)
    elif layout == "category_symlink":
        target = record_root.parent / "outside-category"
        target.mkdir(parents=True)
        path.symlink_to(target, target_is_directory=True)
    elif layout in {"nested_record", "missing_manifest"}:
        path.mkdir()
    else:
        path.write_text("not admitted\n", encoding="utf-8")
    return path


@pytest.mark.timeout(5)
@pytest.mark.parametrize(
    "layout",
    [
        "category_file",
        "category_fifo",
        "category_symlink",
        "wrong_suffix",
        "nested_record",
        "stray_file",
        "stray_fifo",
        "missing_manifest",
        "wrong_manifest_name",
        "manifest_fifo",
    ],
)
def test_inventory_blocks_every_unadmitted_current_physical_node(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    layout: str,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    node = _install_unadmitted_node(current_record_root(repo), layout)
    real_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if path == node and not path.is_file():
            pytest.fail("non-regular current nodes must not be opened")
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 1
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]


@pytest.mark.timeout(5)
def test_no_follow_reader_rejects_regular_file_swapped_to_fifo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    path = record_root / "decisions" / "current.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    real_open = os.open

    def swapping_open(
        candidate: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ):
        if candidate == path.name and dir_fd is not None:
            path.unlink()
            os.mkfifo(path)
        return real_open(candidate, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(current_snapshot.os, "open", swapping_open)

    assert current_snapshot.read_current_record_path(record_root, path) == (None, "invalid")


@pytest.mark.timeout(5)
def test_unadmitted_wrong_name_blocks_apply_before_recovery_or_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path, _planned = _plan_block(repo)
    _install_unadmitted_node(current_record_root(repo), "wrong_suffix")
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

    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert calls == {"recovery": 0, "effect": 0}
    assert lane.is_dir()


@pytest.mark.timeout(5)
@pytest.mark.parametrize("layout", ["category_fifo", "missing_manifest", "wrong_suffix"])
def test_every_unadmitted_current_node_blocks_irreversible_clear(
    tmp_path: Path,
    layout: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    _install_unadmitted_node(current_record_root(repo), layout)

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo,
                topic="lane-resolution-current-enumeration",
                token="clear-preservation",
            ),
            reason="Invalid current state cannot authorize deletion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["ok"] is False
    assert "lane_resolution_current_record_invalid" in report["required_gaps"]
    assert package.is_dir()
    assert not record_store.clear_receipt_path(repo, decision_id).exists()


def test_renamed_current_package_blocks_inventory_and_irreversible_clear(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    renamed = package.with_name("arbitrary-package-name")
    package.rename(renamed)
    manifest_path = renamed / "manifest.json"

    inventory = lane_resolution_inventory(root=repo)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo,
                topic="lane-resolution-current-enumeration",
                token="clear-preservation",
            ),
            reason="Only the canonical decision-id package may be deleted.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 2
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]
    assert report["ok"] is False
    assert "lane_resolution_current_record_invalid" in report["required_gaps"]
    assert renamed.is_dir()
    assert not record_store.clear_receipt_path(repo, decision_id).exists()


def test_relocated_current_receipt_blocks_inventory_and_irreversible_clear(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    receipt = record_store.receipt_path(repo, decision_id)
    relocated = receipt.with_name("arbitrary.json")
    receipt.rename(relocated)

    inventory = lane_resolution_inventory(root=repo)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo,
                topic="lane-resolution-current-enumeration",
                token="clear-preservation",
            ),
            reason="Only the deterministic receipt path may authorize deletion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 2
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]
    assert report["ok"] is False
    assert "lane_resolution_current_record_invalid" in report["required_gaps"]
    assert package.is_dir()
    assert relocated.is_file()
    assert not record_store.clear_receipt_path(repo, decision_id).exists()


def test_receipt_with_noncanonical_package_binding_blocks_irreversible_clear(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    receipt_path = record_store.receipt_path(repo, decision_id)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["preservation_package"] = "/tmp/wrong-package"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    inventory = lane_resolution_inventory(root=repo)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo,
                topic="lane-resolution-current-enumeration",
                token="clear-preservation",
            ),
            reason="Only the canonical package binding may authorize deletion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 2
    assert report["ok"] is False
    assert "lane_resolution_current_record_invalid" in report["required_gaps"]
    assert package.is_dir()


def test_fd_snapshot_keeps_category_bound_after_path_replacement(tmp_path: Path) -> None:
    record_root = tmp_path / "records"
    receipts = record_root / "receipts"
    receipts.mkdir(parents=True)
    name = "record.json"
    (receipts / name).write_bytes(b"original\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / name).write_bytes(b"outside\n")

    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)
    assert state == "valid"
    assert snapshot is not None
    with snapshot:
        _names, category_state = snapshot.open_directory("receipts")
        assert category_state == "valid"
        saved = tmp_path / "saved-receipts"
        receipts.rename(saved)
        receipts.symlink_to(outside, target_is_directory=True)

        assert snapshot.read_file("receipts", name) == b"original\n"


def test_inventory_blocks_coherent_records_that_disagree_with_decision(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(lane_ref="work/other", head="f" * 40, observation_digest="a" * 64)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    receipt_path = record_store.receipt_path(repo, decision_id)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.update(
        lane_ref="work/other",
        head="f" * 40,
        observation_digest="a" * 64,
        preservation_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    )
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 2
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]


def test_inventory_blocks_preserved_receipt_when_package_is_missing(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = Path(str(applied["preservation_package"]["path"]))
    shutil.rmtree(package)

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["entries"][0]["state"] == "inconsistent"
    assert inventory["entries"][0]["package_path"] == str(applied["preservation_package"]["path"])
    assert "lane_resolution_manifest_receipt_mismatch" in inventory["required_gaps"]


def test_clear_rescans_current_records_immediately_before_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = _entry_identity(package)
    manifest_path = package / "manifest.json"
    real_read = clear_adapter.read_current_lane_resolution_records
    calls = 0

    def inject_late_invalid(**kwargs: object):
        nonlocal calls
        current = real_read(**kwargs)
        calls += 1
        if calls == 1:
            invalid = current_record_root(repo) / "receipts" / "late-invalid.txt"
            invalid.write_text("late invalid\n", encoding="utf-8")
        return current

    monkeypatch.setattr(clear_adapter, "read_current_lane_resolution_records", inject_late_invalid)

    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            chronicle_ref=write_chronicle_decision(
                repo,
                topic="lane-resolution-current-enumeration",
                token="clear-preservation",
            ),
            reason="Late invalid state must block deletion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert calls >= 2
    assert report["ok"] is False
    assert "lane_resolution_current_record_invalid" in report["required_gaps"]
    assert record_store.clear_quarantine_path(repo, decision_id, package_identity).is_dir()


def test_apply_blocks_conflicting_canonical_decisions_before_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    decision_path, planned = _plan_block(repo)
    duplicate = dict(planned["decision"])
    duplicate["reason"] = "Conflicting canonical decision bytes."
    decision_path.with_name("duplicate.json").write_text(
        json.dumps(duplicate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    effects = 0

    def record_effect(**_kwargs: object) -> None:
        nonlocal effects
        effects += 1

    monkeypatch.setattr(lane_adapter, "apply_resolution", record_effect)

    report = apply_lane_resolution(
        root=repo,
        decision_path=decision_path,
        confirm_irreversible=False,
        apply=True,
    )

    assert report["ok"] is False
    assert "lane_resolution_decision_record_conflict" in report["required_gaps"]
    assert effects == 0
    assert lane.is_dir()


def test_clear_receipt_before_move_retry_fails_closed_without_durable_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    real_move = clear_adapter.move_current_package_to_quarantine

    def interrupt(**_kwargs: object) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(clear_adapter, "move_current_package_to_quarantine", interrupt)

    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(
            root=repo,
            request=LaneResolutionClearRequest(
                decision_id=decision_id,
                expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                chronicle_ref=write_chronicle_decision(
                    repo,
                    topic="lane-resolution-current-enumeration",
                    token="clear-preservation",
                ),
                reason="An interrupted no-effect clear cannot mint terminal truth.",
                break_glass=True,
                confirm_irreversible=True,
                apply=True,
            ),
        )

    assert package.is_dir()
    assert record_store.clear_receipt_path(repo, decision_id).is_file()
    inventory = lane_resolution_inventory(root=repo)
    assert inventory["entries"][0]["state"] == "partial_transition"
    assert "lane_resolution_partial_transition_present" in inventory["required_gaps"]

    monkeypatch.setattr(clear_adapter, "move_current_package_to_quarantine", real_move)
    retried = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            chronicle_ref="evidence/chronicle/lane-resolution-current-enumeration/clear-preservation.md",
            reason="An interrupted no-effect clear cannot mint terminal truth.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert retried["ok"] is False
    assert retried["state"] == "blocked"
    assert retried["required_gaps"] == ["lane_resolution_clear_canonical_retry_unsafe"]
    assert package.is_dir()


def test_pre_move_identical_canonical_replacement_is_not_deleted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    original_identity = _entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
        ),
        reason="A clear receipt cannot authenticate a later canonical inode.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )
    real_move = clear_adapter.move_current_package_to_quarantine
    monkeypatch.setattr(
        clear_adapter,
        "move_current_package_to_quarantine",
        lambda **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    saved = repo.parent / "saved-original-canonical-package"
    package.rename(saved)
    shutil.copytree(saved, package)
    assert _entry_identity(package) != original_identity

    monkeypatch.setattr(clear_adapter, "move_current_package_to_quarantine", real_move)
    retried = clear_lane_resolution_package(root=repo, request=request)

    assert retried["ok"] is False
    assert retried["required_gaps"] == ["lane_resolution_clear_canonical_retry_unsafe"]
    assert package.is_dir()
    assert saved.is_dir()
    assert not record_store.clear_quarantine_path(repo, decision_id, original_identity).exists()


def test_inventory_verifies_preservation_payload_files(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = Path(str(applied["preservation_package"]["path"]))
    (package / "repository.bundle").unlink()

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]


def test_inventory_rejects_extra_preservation_payload(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    package = Path(str(applied["preservation_package"]["path"]))
    (package / "unexpected.bin").write_bytes(b"unexpected")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]


def test_inventory_rejects_undeclared_preservation_archive(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = _preserve(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (package / "untracked.tar").write_bytes(b"undeclared archive")
    manifest["untracked_archive_sha256"] = ""
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    receipt_path = record_store.receipt_path(repo, decision_id)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["preservation_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]


@pytest.mark.parametrize("binding_state", ["missing", "forged-decision"])
def test_ownerless_retired_receipt_requires_exact_decision_binding(
    tmp_path: Path,
    binding_state: str,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path, planned = _plan_ownerless_retire(repo)
    decision = dict(planned["decision"])
    observation = dict(decision["observation"])
    decision_sha256 = hashlib.sha256(decision_path.read_bytes()).hexdigest()
    binding = None
    if binding_state == "forged-decision":
        binding = {
            "executor_ref": "agent:codex:thread:current-enumeration",
            "decision_sha256": "f" * 64 if decision_sha256 != "f" * 64 else "e" * 64,
            "accepted_branch": "dev",
            "accepted_head": str(observation["head"]),
            "target_digest": record_store.target_digest(
                str(observation["lane_ref"]), str(observation["head"])
            ),
            "target_binding_digest": "d" * 64,
            "postcondition_digest": "c" * 64,
        }
    receipt: dict[str, object] = {
        "schema_version": 3,
        "receipt_id": f"lane-resolution-receipt:{binding_state}",
        "decision_id": decision["decision_id"],
        "completed": True,
        "state": "retired",
        "observation_digest": decision["observation_digest"],
        "reconciliation_required": True,
        "lane_ref": observation["lane_ref"],
        "head": observation["head"],
        "preservation_package": "",
        "preservation_manifest_sha256": "",
        "mints_authority": False,
    }
    if binding is not None:
        receipt["ownerless_closeout_binding"] = binding
    receipt_path = record_store.receipt_path(repo, str(decision["decision_id"]))
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert "lane_resolution_current_record_invalid" in inventory["required_gaps"]


def test_deep_bounded_json_is_counted_invalid_instead_of_crashing(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    record = current_record_root(repo) / "decisions" / "deep.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_bytes(b"[" * 500_000 + b"0" + b"]" * 500_000)

    inventory = lane_resolution_inventory(root=repo)

    assert inventory["ok"] is False
    assert inventory["summary"]["invalid_current_record_count"] == 1
    assert inventory["required_gaps"] == ["lane_resolution_current_record_invalid"]
