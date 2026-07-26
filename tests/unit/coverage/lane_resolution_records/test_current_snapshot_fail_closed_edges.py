from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.records.current.core as current_store
import ethos.adapters.mutation.resolution.records.current.snapshot as current_snapshot
import ethos.adapters.mutation.resolution.records.current.validation.core as current_validation
import ethos.adapters.mutation.resolution.records.io.posix as record_posix
from ethos.contracts.resolution.closeout import LaneResolutionClearReceipt

if TYPE_CHECKING:
    from pathlib import Path

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000201"
_UNSTABLE = "unstable"


def _clear_receipt() -> dict[str, object]:
    return LaneResolutionClearReceipt(
        schema_version=1,
        clear_receipt_id="lane-resolution-clear-receipt:record-edges",
        decision_id=_DECISION_ID,
        manifest_sha256="f" * 64,
        chronicle_ref="evidence/chronicle/record-edges-clear.md",
        chronicle_digest="d" * 64,
        reason="Clear the exact retained package.",
        completed=True,
        mints_authority=False,
    ).to_payload()


def test_current_topology_manifest_same_digest_and_clear_validation_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    monkeypatch.setattr(
        current_store,
        "open_current_record_snapshot",
        lambda _root: (None, "invalid"),
    )
    topology = current_store._current_record_topology(record_root)  # noqa: SLF001, RUF100
    assert topology.invalid_paths == (record_root,)

    paths = tuple(tmp_path / f"copy-{index}" / _DECISION_ID / "manifest.json" for index in range(2))
    sources = tuple(
        current_store._CurrentPayload(  # noqa: SLF001, RUF100
            path,
            b"{}",
            payload_sha256={},
            package_names=set(),
            payload_identities={},
            entry_identity=(1, index, stat.S_IFDIR),
        )
        for index, path in enumerate(paths)
    )
    payload = {
        "decision_id": _DECISION_ID,
        "lane_ref": "work/example",
        "head": "a" * 40,
        "observation_digest": "b" * 64,
    }
    monkeypatch.setattr(
        current_store,
        "_read_current_payload",
        lambda *_args: (payload, "c" * 64),
    )
    monkeypatch.setattr(current_store, "preservation_payloads_match", lambda *_args: True)
    records, conflicts, invalid = current_store._manifests_with_conflicts(  # noqa: SLF001, RUF100
        tmp_path,
        sources,
        {},
    )
    assert records == {}
    assert conflicts == set()
    assert invalid == [*paths]

    with monkeypatch.context() as scoped:
        scoped.setattr(current_validation, "_require_schema", lambda *_args: None)
        scoped.setattr(current_validation, "valid_decision_id", lambda *_args: False)
        with pytest.raises(ValueError, match="lane_resolution_current_record_invalid"):
            current_validation.validate_clear_receipt(tmp_path, _clear_receipt())


def test_current_snapshot_directory_open_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    category = record_root / "receipts"
    category.mkdir(parents=True)
    (category / "receipt.json").write_text("{}\n", encoding="utf-8")

    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)
    assert state == "valid"
    assert snapshot is not None
    with snapshot:
        assert snapshot.open_directory("receipts") == (("receipt.json",), "valid")
        assert snapshot.open_directory("receipts") == (("receipt.json",), "valid")

    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)
    assert state == "valid"
    assert snapshot is not None
    with snapshot, monkeypatch.context() as scoped:
        scoped.setattr(
            current_snapshot.posix,
            "open_directory_child",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("rebound")),
        )
        assert snapshot.open_directory("receipts") == ((), "invalid")

    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)
    assert state == "valid"
    assert snapshot is not None
    with snapshot, monkeypatch.context() as scoped:
        scoped.setattr(
            snapshot,
            "_require_directory",
            lambda *_args: (_ for _ in ()).throw(OSError("rebound")),
        )
        assert snapshot.open_directory("receipts") == ((), "invalid")

    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)
    assert state == "valid"
    assert snapshot is not None
    with snapshot, monkeypatch.context() as scoped:
        scoped.setattr(
            current_snapshot.posix, "file_identity", lambda _metadata: (0, 0, 0, 0, 0, 0)
        )
        assert snapshot.open_directory("receipts") == ((), "invalid")

    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)
    assert state == "valid"
    assert snapshot is not None
    with snapshot, monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot, "_entries", lambda _descriptor: None)
        assert snapshot.open_directory("receipts") == ((), "invalid")


def test_current_snapshot_move_and_quarantine_open_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "records"
    root.mkdir()
    package = root / "package"
    package.mkdir()
    expected = (package.stat().st_dev, package.stat().st_ino, package.stat().st_mode)

    assert (
        current_snapshot.move_current_package_to_quarantine(
            root=tmp_path / "missing",
            source_name="package",
            quarantine_name="quarantine",
            expected_identity=expected,
        )
        == "root_invalid"
    )

    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "directory_descriptor_is_live", lambda *_args: False)
        assert (
            current_snapshot.move_current_package_to_quarantine(
                root=root,
                source_name="package",
                quarantine_name="quarantine",
                expected_identity=expected,
            )
            == "root_invalid"
        )

    for error, state in ((FileExistsError(), "collision"), (OSError(), "rename_failed")):
        with monkeypatch.context() as scoped:
            scoped.setattr(
                current_snapshot.posix,
                "rename_no_replace",
                lambda *_args, error=error: (_ for _ in ()).throw(error),
            )
            assert (
                current_snapshot.move_current_package_to_quarantine(
                    root=root,
                    source_name="package",
                    quarantine_name="quarantine",
                    expected_identity=expected,
                )
                == state
            )

    tokens = iter((expected, None, (0, 0, stat.S_IFDIR)))
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "directory_descriptor_is_live", lambda *_args: True)
        scoped.setattr(current_snapshot, "_entry_token_at", lambda *_args: next(tokens))
        scoped.setattr(current_snapshot.posix, "rename_no_replace", lambda *_args: None)
        assert (
            current_snapshot.move_current_package_to_quarantine(
                root=root,
                source_name="package",
                quarantine_name="quarantine",
                expected_identity=expected,
            )
            == "identity_mismatch"
        )

    binding = current_snapshot.QuarantinedPackageBinding(
        identity=(0, 0, stat.S_IFDIR),
        names=set(),
        sha256={},
        file_identities={},
    )
    assert (
        current_snapshot.remove_quarantined_package(
            root=tmp_path / "missing",
            quarantine_name="missing",
            binding=binding,
        )
        is False
    )
    assert (
        current_snapshot.remove_quarantined_package(
            root=root,
            quarantine_name="missing",
            binding=binding,
        )
        is False
    )

    descriptor = os.open(root, record_posix.directory_flags())
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(current_snapshot, "_entry_token_at", lambda *_args: expected)
            scoped.setattr(
                current_snapshot,
                "_identity_token",
                lambda _metadata: (expected[0], expected[1] + 1, expected[2]),
            )
            assert (
                current_snapshot._open_quarantined_package(  # noqa: SLF001, RUF100
                    descriptor,
                    package.name,
                    expected,
                )
                is None
            )
    finally:
        os.close(descriptor)

    descriptor = os.open(root, record_posix.directory_flags())
    try:
        original_fstat = current_snapshot.os.fstat
        fstat_calls = 0

        def fail_after_open(_descriptor: int) -> object:
            nonlocal fstat_calls
            fstat_calls += 1
            if fstat_calls == 2:
                raise RuntimeError(_UNSTABLE)
            return original_fstat(_descriptor)

        with monkeypatch.context() as scoped:
            scoped.setattr(current_snapshot.os, "fstat", fail_after_open)
            with pytest.raises(RuntimeError, match=_UNSTABLE):
                current_snapshot._open_quarantined_package(  # noqa: SLF001, RUF100
                    descriptor,
                    package.name,
                    expected,
                )
    finally:
        os.close(descriptor)


def _remove_bound_child(
    tmp_path: Path,
    directory_identity: tuple[int, ...],
    identity: tuple[int, ...],
) -> bool:
    return current_snapshot._remove_bound_child(  # noqa: SLF001, RUF100
        tmp_path,
        1,
        directory_identity,
        2,
        "quarantine",
        directory_identity,
        "payload",
        identity,
        "a" * 64,
    )


def test_current_snapshot_remove_bound_child_rejects_unsafe_preconditions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    directory_identity = (1, 2, stat.S_IFDIR)
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "child_directory_is_live", lambda *_args: False)
        assert _remove_bound_child(tmp_path, directory_identity, identity) is False
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "child_directory_is_live", lambda *_args: True)
        scoped.setattr(current_snapshot, "_entry_identity_at", lambda *_args: identity)
        assert _remove_bound_child(tmp_path, directory_identity, identity) is False


def test_current_snapshot_remove_bound_child_closes_after_rename_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    directory_identity = (1, 2, stat.S_IFDIR)
    closed: list[int] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "child_directory_is_live", lambda *_args: True)
        scoped.setattr(current_snapshot, "_entry_identity_at", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "open_identity_bound_file", lambda *_args: 7)
        scoped.setattr(
            current_snapshot.posix,
            "rename_no_replace",
            lambda *_args: (_ for _ in ()).throw(OSError("rename")),
        )
        scoped.setattr(current_snapshot.os, "close", closed.append)
        assert _remove_bound_child(tmp_path, directory_identity, identity) is False
    assert closed == [7]


def test_current_snapshot_remove_bound_child_restores_on_identity_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    directory_identity = (1, 2, stat.S_IFDIR)
    restored: list[tuple[object, ...]] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "child_directory_is_live", lambda *_args: True)
        scoped.setattr(current_snapshot, "_entry_identity_at", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "open_identity_bound_file", lambda *_args: 7)
        scoped.setattr(current_snapshot.posix, "rename_no_replace", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "file_identity", lambda _metadata: identity)
        scoped.setattr(
            current_snapshot.posix,
            "entry_file_identity",
            lambda *_args: (9, 9, stat.S_IFREG, 3, 4, 5),
        )
        scoped.setattr(
            current_snapshot,
            "_restore_staged_entry",
            lambda *args: restored.append(args),
        )
        scoped.setattr(current_snapshot.os, "fstat", lambda _descriptor: object())
        scoped.setattr(current_snapshot.os, "close", lambda _descriptor: None)
        assert _remove_bound_child(tmp_path, directory_identity, identity) is False
    assert restored


def test_current_snapshot_remove_bound_child_restores_on_content_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    directory_identity = (1, 2, stat.S_IFDIR)
    restored: list[tuple[object, ...]] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "child_directory_is_live", lambda *_args: True)
        scoped.setattr(current_snapshot, "_entry_identity_at", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "open_identity_bound_file", lambda *_args: 7)
        scoped.setattr(current_snapshot.posix, "rename_no_replace", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "file_identity", lambda _metadata: identity)
        scoped.setattr(current_snapshot.posix, "entry_file_identity", lambda *_args: identity)
        scoped.setattr(current_snapshot, "_file_matches", lambda *_args: False)
        scoped.setattr(
            current_snapshot,
            "_restore_staged_entry",
            lambda *args: restored.append(args),
        )
        scoped.setattr(current_snapshot.os, "fstat", lambda _descriptor: object())
        scoped.setattr(current_snapshot.os, "close", lambda _descriptor: None)
        assert _remove_bound_child(tmp_path, directory_identity, identity) is False
    assert restored


def test_current_snapshot_remove_bound_child_restores_then_propagates_removal_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    directory_identity = (1, 2, stat.S_IFDIR)
    restored: list[tuple[object, ...]] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "child_directory_is_live", lambda *_args: True)
        scoped.setattr(current_snapshot, "_entry_identity_at", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "open_identity_bound_file", lambda *_args: 7)
        scoped.setattr(current_snapshot.posix, "rename_no_replace", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "file_identity", lambda _metadata: identity)
        scoped.setattr(current_snapshot.posix, "entry_file_identity", lambda *_args: identity)
        scoped.setattr(current_snapshot, "_file_matches", lambda *_args: True)
        scoped.setattr(
            current_snapshot.posix,
            "remove_owned_entry",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("remove")),
        )
        scoped.setattr(
            current_snapshot,
            "_restore_staged_entry",
            lambda *args: restored.append(args),
        )
        scoped.setattr(current_snapshot.os, "fstat", lambda _descriptor: object())
        scoped.setattr(current_snapshot.os, "close", lambda _descriptor: None)
        with pytest.raises(RuntimeError, match="remove"):
            _remove_bound_child(tmp_path, directory_identity, identity)
    assert restored


def test_current_snapshot_remove_bound_child_rejects_lost_liveness_without_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    directory_identity = (1, 2, stat.S_IFDIR)
    restored: list[tuple[object, ...]] = []
    live_checks = iter((True, True, False))
    with monkeypatch.context() as scoped:
        scoped.setattr(
            current_snapshot.posix,
            "child_directory_is_live",
            lambda *_args: next(live_checks),
        )
        scoped.setattr(current_snapshot, "_entry_identity_at", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "open_identity_bound_file", lambda *_args: 7)
        scoped.setattr(current_snapshot.posix, "rename_no_replace", lambda *_args: None)
        scoped.setattr(current_snapshot.posix, "file_identity", lambda _metadata: identity)
        scoped.setattr(current_snapshot.posix, "entry_file_identity", lambda *_args: identity)
        scoped.setattr(current_snapshot, "_file_matches", lambda *_args: True)
        scoped.setattr(current_snapshot.posix, "remove_owned_entry", lambda *_args: None)
        scoped.setattr(
            current_snapshot,
            "_restore_staged_entry",
            lambda *args: restored.append(args),
        )
        scoped.setattr(current_snapshot.os, "fstat", lambda _descriptor: object())
        scoped.setattr(current_snapshot.os, "fsync", lambda _descriptor: None)
        scoped.setattr(current_snapshot.os, "close", lambda _descriptor: None)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            _remove_bound_child(tmp_path, directory_identity, identity)
    assert restored == []


def test_current_snapshot_delete_utility_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory_identity = (1, 2, stat.S_IFDIR)
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        current_snapshot._require_safe(condition=False)  # noqa: SLF001, RUF100
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.os, "fsync", lambda _descriptor: None)
        scoped.setattr(current_snapshot.posix, "child_directory_is_live", lambda *_args: False)
        assert (
            current_snapshot._remove_quarantine_directory(  # noqa: SLF001, RUF100
                tmp_path,
                1,
                directory_identity,
                2,
                "quarantine",
                directory_identity,
            )
            is False
        )
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "payload").write_text("payload", encoding="utf-8")
    descriptor = os.open(entries, record_posix.directory_flags())
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(current_snapshot, "_MAX_CURRENT_DIRECTORY_ENTRIES", 0)
            assert current_snapshot._entries(descriptor) is None  # noqa: SLF001, RUF100
    finally:
        os.close(descriptor)


def test_current_snapshot_restore_staged_entry_handles_missing_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "entry_file_identity", lambda *_args: None)
        current_snapshot._restore_staged_entry(  # noqa: SLF001, RUF100
            1,
            "staging",
            "payload",
            identity,
        )


@pytest.mark.parametrize(
    "canonical_identity",
    [None, (1, 2, stat.S_IFREG, 3, 4, 5)],
)
def test_current_snapshot_restore_staged_entry_rejects_conflicting_canonical(
    monkeypatch: pytest.MonkeyPatch,
    canonical_identity: tuple[int, ...] | None,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    staged = (9, 2, stat.S_IFREG, 3, 4, 5)
    renamed: list[tuple[object, ...]] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "entry_file_identity", lambda *_args: staged)
        scoped.setattr(
            current_snapshot,
            "_entry_identity_at",
            lambda *_args: canonical_identity,
        )
        scoped.setattr(
            current_snapshot.posix,
            "rename_no_replace",
            lambda *args: renamed.append(args),
        )
        scoped.setattr(current_snapshot.os, "fsync", lambda _descriptor: None)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            current_snapshot._restore_staged_entry(  # noqa: SLF001, RUF100
                1,
                "staging",
                "payload",
                identity,
            )
    assert bool(renamed) == (canonical_identity is None)


def test_current_snapshot_restore_staged_entry_removes_matching_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    removed: list[tuple[object, ...]] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(current_snapshot.posix, "entry_file_identity", lambda *_args: identity)
        scoped.setattr(current_snapshot, "_entry_identity_at", lambda *_args: identity)
        scoped.setattr(
            current_snapshot.posix,
            "remove_owned_entry",
            lambda *args, **_kwargs: removed.append(args),
        )
        scoped.setattr(current_snapshot.os, "fsync", lambda _descriptor: None)
        current_snapshot._restore_staged_entry(  # noqa: SLF001, RUF100
            1,
            "staging",
            "payload",
            identity,
        )
    assert removed
