from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import FrozenInstanceError
from dataclasses import is_dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.resolution.records.clear.core as clear_adapter
import ethos.adapters.mutation.resolution.records.clear.quarantine as quarantine_store
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.current.snapshot as current_snapshot
from ethos.adapters.mutation.resolution.records.clear.core import LaneResolutionClearRequest
from ethos.adapters.mutation.resolution.records.clear.core import clear_lane_resolution_package
from ethos.adapters.mutation.resolution.records.inventory import lane_resolution_inventory
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import orphan_work_lane
from tests.unit.lanes.resolution.records import entry_identity
from tests.unit.lanes.resolution.records import preserve_lane


def test_clear_quarantine_candidates_are_concrete_immutable_facts(tmp_path: Path) -> None:
    assert not hasattr(quarantine_store, "CurrentPackageSource")
    candidate = quarantine_store.ClearQuarantineCandidate(
        path=tmp_path / "candidate",
        payload_sha256={},
        package_names=set(),
        payload_identities={},
        entry_identity=(1, 2, 3),
    )

    assert is_dataclass(candidate)
    with pytest.raises(FrozenInstanceError):
        candidate.path = tmp_path / "replacement"


def test_clear_reports_unsafe_receipt_package_and_manifest_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000100"
    manifest_sha256 = "a" * 64
    manifest = {
        "manifest_sha256": manifest_sha256,
        "package_path": (tmp_path / "package").as_posix(),
        "copy_count": 1,
    }
    current = SimpleNamespace(
        manifests={decision_id: manifest},
        clear_quarantines={},
        clears={},
        receipts={},
        invalid_count=0,
        conflicts=set(),
    )
    record_root = tmp_path / "records"
    receipt_path = record_root / "clears" / "receipt.json"
    monkeypatch.setattr(clear_adapter, "current_record_root", lambda _root: record_root)
    monkeypatch.setattr(
        clear_adapter,
        "read_current_lane_resolution_records",
        lambda **_kwargs: current,
    )
    monkeypatch.setattr(clear_adapter, "unsafe_package_path_present", lambda _root: False)
    monkeypatch.setattr(clear_adapter, "unsafe_record_path_present", lambda _root: False)
    monkeypatch.setattr(
        clear_adapter,
        "_clear_chronicle",
        lambda *_args: ("evidence/chronicle/clear.md", "b" * 64, []),
    )
    monkeypatch.setattr(clear_adapter, "_validate_clear_schema", lambda *_args: None)
    monkeypatch.setattr(clear_adapter, "clear_receipt_path", lambda *_args: receipt_path)
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref="evidence/chronicle/clear.md",
        reason="Clear the exact retained package.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )

    monkeypatch.setattr(clear_adapter, "record_destination_safe", lambda *_args: False)
    unsafe_receipt = clear_lane_resolution_package(root=tmp_path, request=request)
    assert unsafe_receipt["required_gaps"] == ["lane_resolution_clear_receipt_path_unsafe"]

    monkeypatch.setattr(clear_adapter, "record_destination_safe", lambda *_args: True)
    monkeypatch.setattr(clear_adapter, "package_path_safe", lambda *_args: False)
    unsafe_package = clear_lane_resolution_package(root=tmp_path, request=request)
    assert unsafe_package["required_gaps"] == ["lane_resolution_package_path_unsafe"]
    assert not receipt_path.exists()

    manifest["manifest_sha256"] = "c" * 64
    monkeypatch.setattr(clear_adapter, "package_path_safe", lambda *_args: True)
    mismatched = clear_lane_resolution_package(root=tmp_path, request=request)
    assert mismatched["required_gaps"] == ["lane_resolution_clear_manifest_mismatch"]
    assert not receipt_path.exists()


def test_post_quarantine_crash_retries_exact_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    chronicle_ref = write_chronicle_decision(
        repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
    )
    real_remove = clear_adapter.remove_quarantined_package

    def interrupt(**_kwargs: object) -> bool:
        raise KeyboardInterrupt

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", interrupt)
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref=chronicle_ref,
        reason="Resume only the exact quarantined package.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )

    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    assert not package.exists()
    assert quarantine.is_dir()
    assert record_store.clear_receipt_path(repo, decision_id).is_file()
    assert lane_resolution_inventory(root=repo)["entries"][0]["state"] == "partial_transition"

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", real_remove)
    retried = clear_lane_resolution_package(root=repo, request=request)

    assert retried["ok"] is True
    assert retried["state"] == "cleared"
    assert not quarantine.exists()


def test_quarantine_open_fstat_failure_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    quarantine = record_root / "quarantine"
    quarantine.mkdir(parents=True)
    identity = entry_identity(quarantine)
    real_open = current_snapshot.os.open
    real_fstat = current_snapshot.os.fstat
    opened: dict[str, int] = {}

    def tracking_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path == quarantine.name and dir_fd is not None:
            opened["descriptor"] = descriptor
        return descriptor

    def fail_package_fstat(descriptor: int):
        if descriptor == opened.get("descriptor"):
            return real_fstat(-1)
        return real_fstat(descriptor)

    monkeypatch.setattr(current_snapshot.os, "open", tracking_open)
    monkeypatch.setattr(current_snapshot.os, "fstat", fail_package_fstat)

    removed = current_snapshot.remove_quarantined_package(
        root=record_root,
        quarantine_name=quarantine.name,
        binding=current_snapshot.QuarantinedPackageBinding(
            identity=identity,
            names=set(),
            sha256={},
            file_identities={},
        ),
    )

    assert removed is False
    with pytest.raises(OSError, match="Bad file descriptor"):
        real_fstat(opened["descriptor"])


def test_quarantine_unlink_crash_keeps_manifest_until_payloads_are_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
        ),
        reason="Resume the exact directory after a partial unlink sequence.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )
    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    real_remove = clear_adapter.remove_quarantined_package
    real_listdir = current_snapshot.os.listdir
    real_unlink = current_snapshot.os.unlink
    unlink_calls = 0
    unlinked_names: list[str] = []

    def interrupt_after_one_unlink(**kwargs: object) -> bool:
        nonlocal unlink_calls

        def manifest_listed_first(directory: int) -> list[str]:
            names = list(real_listdir(directory))
            return ["manifest.json", *(name for name in names if name != "manifest.json")]

        def unlink_once(
            path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            *,
            dir_fd: int | None = None,
        ) -> None:
            nonlocal unlink_calls
            unlink_calls += 1
            unlinked_names.append(str(path))
            if unlink_calls == 2:
                raise KeyboardInterrupt
            real_unlink(path, dir_fd=dir_fd)

        monkeypatch.setattr(current_snapshot.os, "listdir", manifest_listed_first)
        monkeypatch.setattr(current_snapshot.os, "unlink", unlink_once)
        try:
            return real_remove(**kwargs)
        finally:
            monkeypatch.setattr(current_snapshot.os, "listdir", real_listdir)
            monkeypatch.setattr(current_snapshot.os, "unlink", real_unlink)

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", interrupt_after_one_unlink)

    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    assert unlink_calls == 2
    assert unlinked_names[0] != "manifest.json"
    assert quarantine.is_dir()
    assert (quarantine / "manifest.json").is_file()
    assert list(quarantine.iterdir())
    inventory = lane_resolution_inventory(root=repo)
    assert inventory["summary"]["invalid_current_record_count"] == 0
    assert inventory["entries"][0]["state"] == "partial_transition"

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", real_remove)
    retried = clear_lane_resolution_package(root=repo, request=request)

    assert retried["ok"] is True
    assert retried["state"] == "cleared"
    assert not quarantine.exists()


def test_remaining_quarantine_payload_replacement_blocks_retry_without_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
        ),
        reason="A same-name payload replacement cannot inherit clear authority.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )
    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    real_remove = clear_adapter.remove_quarantined_package
    real_listdir = current_snapshot.os.listdir
    real_unlink = current_snapshot.os.unlink
    unlink_calls = 0

    def interrupt_after_one_payload(**kwargs: object) -> bool:
        nonlocal unlink_calls

        def manifest_listed_first(directory: int) -> list[str]:
            names = list(real_listdir(directory))
            return ["manifest.json", *(name for name in names if name != "manifest.json")]

        def unlink_once(
            path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            *,
            dir_fd: int | None = None,
        ) -> None:
            nonlocal unlink_calls
            unlink_calls += 1
            if unlink_calls == 2:
                raise KeyboardInterrupt
            real_unlink(path, dir_fd=dir_fd)

        monkeypatch.setattr(current_snapshot.os, "listdir", manifest_listed_first)
        monkeypatch.setattr(current_snapshot.os, "unlink", unlink_once)
        try:
            return real_remove(**kwargs)
        finally:
            monkeypatch.setattr(current_snapshot.os, "listdir", real_listdir)
            monkeypatch.setattr(current_snapshot.os, "unlink", real_unlink)

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", interrupt_after_one_payload)
    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    remaining = next(
        path for path in quarantine.iterdir() if path.name != "manifest.json" and path.is_file()
    )
    remaining.unlink()
    remaining.write_bytes(b"same-name replacement\n")

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", real_remove)
    retried = clear_lane_resolution_package(root=repo, request=request)

    assert retried["ok"] is False
    assert retried["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert remaining.read_bytes() == b"same-name replacement\n"
    assert quarantine.is_dir()


def test_payload_swap_during_remove_is_not_deleted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    real_remove = clear_adapter.remove_quarantined_package
    real_listdir = current_snapshot.os.listdir
    real_unlink = current_snapshot.os.unlink
    replacement = b"replacement during removal\n"
    swapped = False

    def swap_before_later_payload(**kwargs: object) -> bool:
        def payloads_then_manifest(directory: int) -> list[str]:
            names = list(real_listdir(directory))
            payloads = sorted(name for name in names if name != "manifest.json")
            return [*payloads, "manifest.json"]

        def unlink_and_swap(
            path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
            *,
            dir_fd: int | None = None,
        ) -> None:
            nonlocal swapped
            real_unlink(path, dir_fd=dir_fd)
            if swapped or str(path) == "tracked.patch":
                return
            real_unlink("tracked.patch", dir_fd=dir_fd)
            descriptor = os.open(
                "tracked.patch",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=dir_fd,
            )
            try:
                os.write(descriptor, replacement)
            finally:
                os.close(descriptor)
            swapped = True

        monkeypatch.setattr(current_snapshot.os, "listdir", payloads_then_manifest)
        monkeypatch.setattr(current_snapshot.os, "unlink", unlink_and_swap)
        try:
            return real_remove(**kwargs)
        finally:
            monkeypatch.setattr(current_snapshot.os, "listdir", real_listdir)
            monkeypatch.setattr(current_snapshot.os, "unlink", real_unlink)

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", swap_before_later_payload)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
            ),
            reason="A later payload replacement must survive a raced clear.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert swapped is True
    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_clear_remove_failed"]
    assert (quarantine / "tracked.patch").read_bytes() == replacement


def test_identical_replacement_quarantine_is_not_deleted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
        ),
        reason="Never delete a replacement at the prior quarantine name.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )
    real_remove = clear_adapter.remove_quarantined_package
    monkeypatch.setattr(
        clear_adapter,
        "remove_quarantined_package",
        lambda **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    saved = repo.parent / "saved-original-quarantine"
    quarantine.rename(saved)
    shutil.copytree(saved, quarantine)
    assert entry_identity(quarantine) != package_identity

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", real_remove)
    inventory = lane_resolution_inventory(root=repo)
    retried = clear_lane_resolution_package(root=repo, request=request)

    assert inventory["summary"]["invalid_current_record_count"] >= 1
    assert retried["ok"] is False
    assert retried["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert quarantine.is_dir()
    assert saved.is_dir()


def test_valid_clear_receipt_swap_blocks_before_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    real_move = clear_adapter.move_current_package_to_quarantine

    def move_then_swap_clear(**kwargs: object) -> str:
        state = real_move(**kwargs)
        assert state == "moved"
        clear_path = record_store.clear_receipt_path(repo, decision_id)
        clear = json.loads(clear_path.read_text(encoding="utf-8"))
        clear["clear_receipt_id"] = "lane-resolution-clear-receipt:swapped"
        clear["reason"] = "A different valid clear must not inherit authorization."
        clear_path.unlink()
        clear_path.write_text(
            json.dumps(clear, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return state

    monkeypatch.setattr(clear_adapter, "move_current_package_to_quarantine", move_then_swap_clear)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
            ),
            reason="Only the exact durable clear may authorize deletion.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_clear_receipt_mismatch"]
    assert quarantine.is_dir()


def test_late_unknown_quarantine_entry_blocks_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    real_remove = clear_adapter.remove_quarantined_package

    def add_late_entry(**kwargs: object) -> bool:
        quarantine = current_record_root(repo) / str(kwargs["quarantine_name"])
        (quarantine / "late.marker").write_text("retain\n", encoding="utf-8")
        return real_remove(**kwargs)

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", add_late_entry)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
            ),
            reason="Late unknown files are outside the reviewed deletion set.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    assert report["ok"] is False
    assert report["required_gaps"] == ["lane_resolution_clear_remove_failed"]
    assert (quarantine / "late.marker").read_text(encoding="utf-8") == "retain\n"


def test_malformed_identity_quarantine_blocks_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
        ),
        reason="Malformed quarantine identity cannot authorize retry.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )
    real_remove = clear_adapter.remove_quarantined_package
    monkeypatch.setattr(
        clear_adapter,
        "remove_quarantined_package",
        lambda **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    digest = hashlib.sha256(decision_id.encode()).hexdigest()
    malformed = quarantine.with_name(f".{digest}.not-an-identity.clear-quarantine")
    quarantine.rename(malformed)

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", real_remove)
    inventory = lane_resolution_inventory(root=repo)
    retried = clear_lane_resolution_package(root=repo, request=request)

    assert inventory["summary"]["invalid_current_record_count"] >= 1
    assert retried["ok"] is False
    assert retried["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert malformed.is_dir()


def test_multiple_identity_quarantines_block_before_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref=write_chronicle_decision(
            repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
        ),
        reason="Only one exact quarantine may participate in retry.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )
    real_remove = clear_adapter.remove_quarantined_package
    monkeypatch.setattr(
        clear_adapter,
        "remove_quarantined_package",
        lambda **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    temporary = current_record_root(repo) / "second-quarantine"
    temporary.mkdir()
    second = record_store.clear_quarantine_path(repo, decision_id, entry_identity(temporary))
    temporary.rename(second)

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", real_remove)
    inventory = lane_resolution_inventory(root=repo)
    retried = clear_lane_resolution_package(root=repo, request=request)

    assert inventory["summary"]["invalid_current_record_count"] >= 1
    assert retried["ok"] is False
    assert retried["required_gaps"] == ["lane_resolution_current_record_invalid"]
    assert quarantine.is_dir()
    assert second.is_dir()


def test_post_delete_crash_is_terminal_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    chronicle_ref = write_chronicle_decision(
        repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
    )
    real_remove = clear_adapter.remove_quarantined_package

    def remove_then_interrupt(**kwargs: object) -> bool:
        assert real_remove(**kwargs) is True
        raise KeyboardInterrupt

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", remove_then_interrupt)
    request = LaneResolutionClearRequest(
        decision_id=decision_id,
        expect_manifest_sha256=manifest_sha256,
        chronicle_ref=chronicle_ref,
        reason="The durable receipt makes post-delete retry idempotent.",
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )

    with pytest.raises(KeyboardInterrupt):
        clear_lane_resolution_package(root=repo, request=request)

    inventory = lane_resolution_inventory(root=repo)
    assert inventory["ok"] is True
    assert inventory["entries"][0]["state"] == "cleared"

    monkeypatch.setattr(clear_adapter, "remove_quarantined_package", real_remove)
    retried = clear_lane_resolution_package(root=repo, request=request)

    assert retried["ok"] is True
    assert retried["state"] == "cleared"


def test_clear_package_identity_swap_blocks_without_deleting_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    saved = repo.parent / "saved-reviewed-package"
    real_move = clear_adapter.move_current_package_to_quarantine

    def swap_then_move(**kwargs: object) -> str:
        package.rename(saved)
        package.mkdir()
        (package / "replacement.marker").write_text("retain\n", encoding="utf-8")
        return real_move(**kwargs)

    monkeypatch.setattr(clear_adapter, "move_current_package_to_quarantine", swap_then_move)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
            ),
            reason="Only the reviewed package inode may be quarantined.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["ok"] is False
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_clear_package_identity_mismatch"]
    assert (package / "replacement.marker").read_text(encoding="utf-8") == "retain\n"
    assert saved.is_dir()


def test_clear_quarantine_collision_never_overwrites_existing_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    applied = preserve_lane(repo, lane)
    decision_id = str(applied["receipt"]["decision_id"])
    package = Path(str(applied["preservation_package"]["path"]))
    package_identity = entry_identity(package)
    manifest_sha256 = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
    quarantine = record_store.clear_quarantine_path(repo, decision_id, package_identity)
    real_move = clear_adapter.move_current_package_to_quarantine

    def collide_then_move(**kwargs: object) -> str:
        quarantine.mkdir()
        (quarantine / "collision.marker").write_text("retain\n", encoding="utf-8")
        return real_move(**kwargs)

    monkeypatch.setattr(clear_adapter, "move_current_package_to_quarantine", collide_then_move)
    report = clear_lane_resolution_package(
        root=repo,
        request=LaneResolutionClearRequest(
            decision_id=decision_id,
            expect_manifest_sha256=manifest_sha256,
            chronicle_ref=write_chronicle_decision(
                repo, topic="lane-resolution-current-enumeration", token="clear-preservation"
            ),
            reason="A deterministic quarantine collision blocks without overwrite.",
            break_glass=True,
            confirm_irreversible=True,
            apply=True,
        ),
    )

    assert report["ok"] is False
    assert report["state"] == "partial_transition"
    assert report["required_gaps"] == ["lane_resolution_clear_quarantine_collision"]
    assert package.is_dir()
    assert (quarantine / "collision.marker").read_text(encoding="utf-8") == "retain\n"
