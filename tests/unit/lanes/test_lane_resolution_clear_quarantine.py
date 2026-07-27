from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.records.clear.preservation_clear as clear_adapter
import ethos.adapters.mutation.resolution.records.current.snapshot as current_snapshot
from ethos.adapters.mutation.resolution.records.clear.preservation_clear import (
    LaneResolutionClearRequest,
)
from ethos.adapters.mutation.resolution.records.clear.preservation_clear import (
    clear_lane_resolution_package,
)
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import orphan_work_lane
from tests.unit.lanes.resolution.records import entry_identity
from tests.unit.lanes.resolution.records import preserve_lane


def test_quarantine_stage_fsync_failure_restores_payload_without_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    quarantine = record_root / "quarantine"
    quarantine.mkdir(parents=True)
    payload = quarantine / "tracked.patch"
    content = b"tracked patch\n"
    payload.write_bytes(content)
    metadata = payload.stat()
    identity = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )
    original_fsync = current_snapshot.os.fsync
    failed = False

    def fail_staged_directory_fsync(descriptor: int) -> None:
        nonlocal failed
        descriptor_metadata = current_snapshot.os.fstat(descriptor)
        directory_metadata = quarantine.stat()
        staged = tuple(quarantine.glob("*.clear-delete"))
        if (
            (descriptor_metadata.st_dev, descriptor_metadata.st_ino)
            == (directory_metadata.st_dev, directory_metadata.st_ino)
            and staged
            and not payload.exists()
            and not failed
        ):
            failed = True
            msg = "quarantine stage fsync interrupted"
            raise OSError(msg)
        original_fsync(descriptor)

    monkeypatch.setattr(current_snapshot.os, "fsync", fail_staged_directory_fsync)
    removed = current_snapshot.remove_quarantined_package(
        root=record_root,
        quarantine_name=quarantine.name,
        binding=current_snapshot.QuarantinedPackageBinding(
            identity=entry_identity(quarantine),
            names={payload.name},
            sha256={payload.name: hashlib.sha256(content).hexdigest()},
            file_identities={payload.name: identity},
        ),
    )

    assert failed is True
    assert removed is False
    assert payload.read_bytes() == content
    assert not tuple(quarantine.glob("*.clear-delete"))


def test_post_delete_crash_is_terminal_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest(),
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
        ),
        reason="The durable receipt makes post-delete retry idempotent.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )
    remove = clear_adapter.remove_quarantined_package

    def remove_then_interrupt(**kwargs: object) -> bool:
        assert remove(**kwargs) is True
        raise KeyboardInterrupt

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", remove_then_interrupt)
    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    assert lane_resolution_inventory(root=repo)["entries"][0]["state"] == "cleared"
    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", remove)
    retried = clear_lane_resolution_package(root=repo, request=request)
    assert (retried["ok"], retried["state"]) == (True, "cleared")
