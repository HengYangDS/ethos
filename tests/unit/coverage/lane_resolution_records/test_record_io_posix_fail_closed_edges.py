from __future__ import annotations

import errno
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.records.io.core as record_io
import ethos.adapters.mutation.resolution.records.io.posix as record_posix
import ethos.adapters.mutation.resolution.records.roots as resolution_roots

if TYPE_CHECKING:
    from collections.abc import Iterator

_BINDING_LOST = "binding lost"
_CLOSE_FAILURE = "close"
_DIRECTORY_SYNC_FAILURE = "directory sync"


def _sidecar_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"expected")
    reservation = record_root / "receipts" / ".receipt.receipt-reservation"
    blocker = record_root / "receipts" / "receipt.json"
    reservation.parent.mkdir(exist_ok=True)
    reservation.write_bytes(b"expected")
    return record_root, destination, reservation, blocker


def _record_parent(record_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        parent_descriptor=1,
        destination=Path("record.json"),
        name="record.json",
        record_root=record_root,
        category="receipts",
        root_identity=(1, 2, stat.S_IFDIR),
        parent_identity=(1, 3, stat.S_IFDIR),
    )


@contextmanager
def _opened_parent(parent: SimpleNamespace) -> Iterator[SimpleNamespace]:
    yield parent


@contextmanager
def _open_record_directory(tmp_path: Path) -> Iterator[tuple[Path, int]]:
    directory = tmp_path / "records"
    directory.mkdir()
    descriptor = os.open(directory, record_posix.directory_flags())
    try:
        yield directory, descriptor
    finally:
        os.close(descriptor)


def test_record_io_read_lock_and_reserve_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation, blocker = _sidecar_paths(tmp_path)
    with monkeypatch.context() as scoped:
        scoped.setattr(record_posix, "descriptor_matches_entry", lambda *_args: False)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_io.read_record_bytes(destination, record_root=record_root)

    with monkeypatch.context() as scoped:
        scoped.setattr(record_posix, "descriptor_matches_entry", lambda *_args: False)
        with (
            pytest.raises(OSError, match="lane_resolution_record_path_unsafe"),
            record_io.lock_record(destination, record_root=record_root),
        ):
            pass
    with monkeypatch.context() as scoped:
        scoped.setattr(
            record_io,
            "_read_bound_bytes",
            lambda *_args: (_ for _ in ()).throw(OSError("unreadable")),
        )
        with pytest.raises(OSError, match="unreadable"):
            record_io.reserve_record_sidecar(
                reservation,
                blocker,
                expected=b"expected",
                record_root=record_root,
            )


def test_record_io_sidecar_recovery_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, _destination, reservation, blocker = _sidecar_paths(tmp_path)
    locked = tmp_path / "locked"
    locked.write_bytes(b"locked")
    descriptor = os.open(locked, os.O_RDONLY)
    original_identity = record_posix.entry_file_identity
    removed: list[tuple[object, ...]] = []
    try:
        for mode, expected_error in (("recover", FileExistsError), ("recover_completed", None)):
            calls = 0

            def blocker_state(directory: int, name: str) -> object:
                nonlocal calls
                if name == blocker.name:
                    calls += 1
                    return None if calls == 1 else (1, 2, stat.S_IFREG, 3, 4, 5)
                return original_identity(directory, name)

            with monkeypatch.context() as scoped:
                scoped.setattr(record_posix, "entry_file_identity", blocker_state)
                scoped.setattr(record_io, "_create_locked_bound_bytes", lambda *_args: descriptor)
                scoped.setattr(
                    record_posix,
                    "remove_owned_entry",
                    lambda *args, **_kwargs: removed.append(args),
                )
                scoped.setattr(record_posix, "unlock_close", lambda _descriptor: None)
                manager = record_io.claim_record_sidecar(
                    reservation,
                    blocker,
                    expected=b"expected",
                    record_root=record_root,
                    mode=mode,
                )
                if expected_error is not None:
                    with pytest.raises(expected_error), manager:
                        pass
                else:
                    with manager as held:
                        assert held == descriptor

    finally:
        os.close(descriptor)
    assert removed


def test_record_io_sidecar_collision_and_recovery_cleanup_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, _destination, reservation, blocker = _sidecar_paths(tmp_path)
    locked = tmp_path / "locked"
    locked.write_bytes(b"locked")
    descriptor = os.open(locked, os.O_RDONLY)
    sidecar_identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(
                record_posix,
                "entry_file_identity",
                lambda _directory, name: sidecar_identity if name == blocker.name else None,
            )
            with (
                pytest.raises(FileExistsError),
                record_io.claim_record_sidecar(
                    reservation,
                    blocker,
                    expected=b"expected",
                    record_root=record_root,
                    mode="recover",
                ),
            ):
                pass
        with monkeypatch.context() as scoped:
            scoped.setattr(record_posix, "entry_file_identity", lambda *_args: None)
            scoped.setattr(
                record_io,
                "_create_locked_bound_bytes",
                lambda *_args: (_ for _ in ()).throw(FileExistsError()),
            )
            with (
                pytest.raises(FileExistsError),
                record_io.claim_record_sidecar(
                    reservation,
                    blocker,
                    expected=b"expected",
                    record_root=record_root,
                    mode="create",
                ),
            ):
                pass
        blocker_checks = 0

        def blocker_after_create(_directory: int, name: str) -> object:
            nonlocal blocker_checks
            if name != blocker.name:
                return None
            blocker_checks += 1
            return None if blocker_checks == 1 else sidecar_identity

        skipped_removals: list[tuple[object, ...]] = []
        with monkeypatch.context() as scoped:
            scoped.setattr(record_posix, "entry_file_identity", blocker_after_create)
            scoped.setattr(
                record_io,
                "_create_locked_bound_bytes",
                lambda *_args: (_ for _ in ()).throw(FileExistsError()),
            )
            scoped.setattr(record_io, "_lock_existing_bound_record", lambda *_args: descriptor)
            scoped.setattr(
                record_posix,
                "remove_owned_entry",
                lambda *args, **_kwargs: skipped_removals.append(args),
            )
            scoped.setattr(record_posix, "unlock_close", lambda _descriptor: None)
            with (
                pytest.raises(FileExistsError),
                record_io.claim_record_sidecar(
                    reservation,
                    blocker,
                    expected=b"expected",
                    record_root=record_root,
                    mode="recover",
                ),
            ):
                pass
    finally:
        os.close(descriptor)
    assert skipped_removals == []


def test_record_io_write_bytes_failure_cleanup_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "receipts" / "record.json"
    destination.parent.mkdir(parents=True)

    with monkeypatch.context() as scoped:
        scoped.setattr(
            record_io,
            "_require_record",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("verify")),
        )
        with pytest.raises(RuntimeError, match="verify"):
            record_io.write_record_bytes(destination, b"content", record_root=record_root)
    assert not destination.exists()

    with monkeypatch.context() as scoped:
        scoped.setattr(
            record_io.os,
            "link",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("link")),
        )
        with pytest.raises(OSError, match="link"):
            record_io.write_record_bytes(destination, b"content", record_root=record_root)
    assert list(destination.parent.glob("*.tmp")) == []


def test_record_io_create_locked_cleanup_and_content_validation_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    parent = _record_parent(record_root)
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    removed: list[tuple[object, ...]] = []
    unlocked: list[int] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(resolution_roots, "require_parent_identity", lambda *_args: None)
        scoped.setattr(record_posix, "entry_file_identity", lambda *_args: None)
        scoped.setattr(record_posix, "create_locked_file_link", lambda *_args: (7, identity))
        scoped.setattr(
            record_io,
            "_require_record",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("verify")),
        )
        scoped.setattr(
            record_posix,
            "remove_owned_entry",
            lambda *args, **_kwargs: removed.append(args),
        )
        scoped.setattr(record_posix, "unlock_close", unlocked.append)
        with pytest.raises(RuntimeError, match="verify"):
            record_io._create_locked_bound_bytes(parent, b"content")  # noqa: SLF001, RUF100
    assert removed == [(1, "record.json", identity)]
    assert unlocked == [7]

    with monkeypatch.context() as scoped:
        scoped.setattr(record_io, "read_descriptor_bytes", lambda _descriptor: b"wrong")
        scoped.setattr(record_posix, "descriptor_matches_entry", lambda *_args: True)
        with pytest.raises(ValueError, match="lane_resolution_current_record_changed"):
            record_io._require_locked_record_content(parent, 7, b"expected")  # noqa: SLF001, RUF100


def test_record_io_replace_cleans_up_when_parent_binding_is_lost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    parent = _record_parent(record_root)
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    calls = 0

    def require_parent(_parent: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError(_BINDING_LOST)

    cleanup: list[tuple[object, ...]] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(
            resolution_roots,
            "open_record_parent",
            lambda *_args, **_kwargs: _opened_parent(parent),
        )
        scoped.setattr(record_posix, "prepare_bound_file", lambda *_args: ("temporary", identity))
        scoped.setattr(record_posix, "staging_name", lambda *_args: "staging")
        scoped.setattr(record_io, "_stage_expected_record", lambda *_args: identity)
        scoped.setattr(record_io.os, "link", lambda *_args, **_kwargs: None)
        scoped.setattr(
            resolution_roots,
            "require_entry_identity",
            lambda *_args, **_kwargs: identity,
        )
        scoped.setattr(resolution_roots, "require_parent_identity", require_parent)
        scoped.setattr(record_io, "_require_record", lambda *_args, **_kwargs: None)
        scoped.setattr(record_io.os, "fsync", lambda _descriptor: None)
        scoped.setattr(
            record_posix,
            "remove_owned_entry",
            lambda *args, **_kwargs: cleanup.append(args),
        )
        scoped.setattr(resolution_roots, "directory_binding_matches", lambda *_args: False)
        with pytest.raises(RuntimeError, match=_BINDING_LOST):
            record_io._replace_record_bytes(  # noqa: SLF001, RUF100
                Path("record.json"),
                b"replacement",
                expected=b"expected",
                record_root=record_root,
                locked_descriptor=7,
            )
    assert any(args[1] == "record.json" for args in cleanup)


def test_record_io_remove_cleans_up_when_parent_binding_is_lost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    parent = _record_parent(record_root)
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            resolution_roots,
            "open_record_parent",
            lambda *_args, **_kwargs: _opened_parent(parent),
        )
        scoped.setattr(record_io, "_stage_expected_record", lambda *_args: identity)
        scoped.setattr(resolution_roots, "require_parent_identity", lambda *_args: None)
        scoped.setattr(record_posix, "remove_owned_entry", lambda *_args, **_kwargs: None)
        scoped.setattr(record_posix, "entry_file_identity", lambda *_args: identity)
        with pytest.raises(ValueError, match="lane_resolution_current_record_changed"):
            record_io._remove_record_bytes(  # noqa: SLF001, RUF100
                Path("record.json"),
                expected=b"expected",
                record_root=record_root,
                locked_descriptor=7,
            )

    parent_identity_checks = 0

    def fail_after_delete(_parent: object) -> None:
        nonlocal parent_identity_checks
        parent_identity_checks += 1
        if parent_identity_checks == 2:
            raise RuntimeError(_BINDING_LOST)

    removed_after_delete: list[tuple[object, ...]] = []
    restored_after_delete: list[tuple[object, ...]] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(
            resolution_roots,
            "open_record_parent",
            lambda *_args, **_kwargs: _opened_parent(parent),
        )
        scoped.setattr(record_io, "_stage_expected_record", lambda *_args: identity)
        scoped.setattr(resolution_roots, "require_parent_identity", fail_after_delete)
        scoped.setattr(
            record_posix,
            "remove_owned_entry",
            lambda *args, **_kwargs: removed_after_delete.append(args),
        )
        scoped.setattr(
            record_posix,
            "restore_staged_file",
            lambda *args: restored_after_delete.append(args),
        )
        with pytest.raises(RuntimeError, match=_BINDING_LOST):
            record_io._remove_record_bytes(  # noqa: SLF001, RUF100
                Path("record.json"),
                expected=b"expected",
                record_root=record_root,
                locked_descriptor=7,
            )
    assert removed_after_delete
    assert restored_after_delete == []


def test_record_io_stage_rejects_changed_record_and_restores_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    parent = _record_parent(record_root)
    identity = (1, 2, stat.S_IFREG, 3, 4, 5)
    with monkeypatch.context() as scoped:
        scoped.setattr(resolution_roots, "require_parent_identity", lambda *_args: None)
        scoped.setattr(record_io, "read_descriptor_bytes", lambda _descriptor: b"expected")
        scoped.setattr(record_posix, "descriptor_matches_entry", lambda *_args: True)
        scoped.setattr(record_posix, "entry_file_identity", lambda *_args: identity)
        with pytest.raises(ValueError, match="lane_resolution_current_record_changed"):
            record_io._stage_expected_record(parent, 8, b"expected", "staging")  # noqa: SLF001, RUF100

    restored: list[tuple[object, ...]] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(resolution_roots, "require_parent_identity", lambda *_args: None)
        scoped.setattr(record_io, "read_descriptor_bytes", lambda _descriptor: b"expected")
        scoped.setattr(record_posix, "descriptor_matches_entry", lambda *_args: _args[-1] == 8)
        scoped.setattr(record_posix, "entry_file_identity", lambda *_args: None)
        scoped.setattr(record_posix, "stage_locked_file", lambda *_args: (7, identity))
        scoped.setattr(record_io.os, "fstat", lambda _descriptor: object())
        scoped.setattr(record_posix, "file_identity", lambda _metadata: identity)
        scoped.setattr(record_io.os, "close", lambda _descriptor: None)
        scoped.setattr(record_posix, "restore_staged_file", lambda *args: restored.append(args))
        with pytest.raises(ValueError, match="lane_resolution_current_record_changed"):
            record_io._stage_expected_record(parent, 8, b"expected", "staging")  # noqa: SLF001, RUF100
    assert restored


def test_posix_prepare_and_create_locked_file_cleanup_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_close = os.close
    descriptor_holder: dict[str, int] = {}
    removed: list[tuple[object, ...]] = []
    with _open_record_directory(tmp_path) as (directory, directory_descriptor):
        original_create = record_posix.create_bound_file

        def create(directory_fd: int, name: str) -> int:
            descriptor_holder["value"] = original_create(directory_fd, name)
            return descriptor_holder["value"]

        def close_with_failure(descriptor: int) -> None:
            if descriptor == descriptor_holder.get("value"):
                raise RuntimeError(_CLOSE_FAILURE)
            original_close(descriptor)

        with monkeypatch.context() as scoped:
            scoped.setattr(record_posix, "create_bound_file", create)
            scoped.setattr(record_posix.os, "close", close_with_failure)
            scoped.setattr(
                record_posix,
                "remove_owned_entry",
                lambda *args, **_kwargs: removed.append(args),
            )
            with pytest.raises(RuntimeError, match=_CLOSE_FAILURE):
                record_posix.prepare_bound_file(directory_descriptor, "target", b"content")
        original_close(descriptor_holder["value"])
        for path in directory.iterdir():
            path.unlink()

        with monkeypatch.context() as scoped:
            scoped.setattr(
                record_posix.fcntl,
                "flock",
                lambda *_args: (_ for _ in ()).throw(OSError("lock")),
            )
            scoped.setattr(record_posix, "remove_owned_entry", lambda *_args, **_kwargs: None)
            with pytest.raises(OSError, match="lock"):
                record_posix.create_locked_file_link(directory_descriptor, "target", b"content")
        for path in directory.iterdir():
            path.unlink()

        fsync_calls = 0
        original_fsync = os.fsync

        def fail_second_fsync(descriptor: int) -> None:
            nonlocal fsync_calls
            fsync_calls += 1
            if fsync_calls == 2:
                raise RuntimeError(_DIRECTORY_SYNC_FAILURE)
            original_fsync(descriptor)

        with monkeypatch.context() as scoped:
            scoped.setattr(record_posix.os, "fsync", fail_second_fsync)
            scoped.setattr(record_posix, "remove_owned_entry", lambda *_args, **_kwargs: None)
            with pytest.raises(RuntimeError, match=_DIRECTORY_SYNC_FAILURE):
                record_posix.create_locked_file_link(directory_descriptor, "target", b"content")
        for path in directory.iterdir():
            path.unlink()


def test_posix_lock_and_stable_read_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _open_record_directory(tmp_path) as (directory, directory_descriptor):
        locked = directory / "locked"
        locked.write_bytes(b"content")
        with monkeypatch.context() as scoped:
            scoped.setattr(
                record_posix.fcntl,
                "flock",
                lambda *_args: (_ for _ in ()).throw(OSError("lock")),
            )
            with pytest.raises(OSError, match="lock"):
                record_posix.lock_regular_file(directory_descriptor, locked.name)

        descriptor = os.open(locked, os.O_RDONLY)
        try:
            identities = iter(
                (
                    (1, 2, stat.S_IFREG, len(b"content"), 1, 1),
                    (1, 3, stat.S_IFREG, len(b"content"), 1, 1),
                )
            )
            with monkeypatch.context() as scoped:
                scoped.setattr(record_posix, "file_identity", lambda _metadata: next(identities))
                with pytest.raises(ValueError, match=r"^$"):
                    record_posix.read_stable_descriptor(descriptor, max_bytes=1024)
        finally:
            os.close(descriptor)


def test_posix_stage_locked_file_restoration_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _open_record_directory(tmp_path) as (directory, directory_descriptor):
        locked = directory / "locked"
        locked.write_bytes(b"content")
        descriptor = os.open(locked, os.O_RDONLY)
        identity = (1, 2, stat.S_IFREG, 3, 4, 5)
        restored: list[tuple[object, ...]] = []
        try:
            with monkeypatch.context() as scoped:
                scoped.setattr(record_posix, "rename_no_replace", lambda *_args: None)
                scoped.setattr(record_posix, "entry_file_identity", lambda *_args: identity)
                scoped.setattr(record_posix, "file_identity", lambda _metadata: identity)
                scoped.setattr(
                    record_posix,
                    "open_identity_bound_file",
                    lambda *_args: (_ for _ in ()).throw(OSError("reopen")),
                )
                scoped.setattr(
                    record_posix,
                    "restore_staged_file",
                    lambda *args: restored.append(args),
                )
                with pytest.raises(OSError, match="reopen"):
                    record_posix.stage_locked_file(
                        directory_descriptor,
                        locked.name,
                        "staging",
                        descriptor,
                    )
        finally:
            os.close(descriptor)
        assert restored

        descriptor = os.open(locked, os.O_RDONLY)
        restore_before_rename: list[tuple[object, ...]] = []
        try:
            with monkeypatch.context() as scoped:
                scoped.setattr(
                    record_posix,
                    "rename_no_replace",
                    lambda *_args: (_ for _ in ()).throw(OSError("rename")),
                )
                scoped.setattr(
                    record_posix,
                    "restore_staged_file",
                    lambda *args: restore_before_rename.append(args),
                )
                with pytest.raises(OSError, match="rename"):
                    record_posix.stage_locked_file(
                        directory_descriptor,
                        locked.name,
                        "staging",
                        descriptor,
                    )
        finally:
            os.close(descriptor)
        assert restore_before_rename == []


def test_posix_remove_owned_entry_restoration_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _open_record_directory(tmp_path) as (_directory, directory_descriptor):
        identity = (1, 2, stat.S_IFREG, 3, 4, 5)
        restored: list[tuple[object, ...]] = []
        with monkeypatch.context() as scoped:
            scoped.setattr(record_posix.fcntl, "flock", lambda *_args: None)
            scoped.setattr(record_posix, "open_identity_bound_file", lambda *_args: 7)
            scoped.setattr(record_posix, "rename_no_replace", lambda *_args: None)
            scoped.setattr(record_posix.os, "fstat", lambda _descriptor: object())
            scoped.setattr(record_posix, "file_identity", lambda _metadata: identity)
            scoped.setattr(
                record_posix,
                "entry_file_identity",
                lambda *_args: (9, 9, stat.S_IFREG, 3, 4, 5),
            )
            scoped.setattr(
                record_posix,
                "restore_staged_file",
                lambda *args: restored.append(args),
            )
            scoped.setattr(record_posix.os, "close", lambda _descriptor: None)
            with pytest.raises(OSError, match=os.strerror(errno.ESTALE)):
                record_posix.remove_owned_entry(directory_descriptor, "target", identity)
        assert restored

        restored.clear()
        with monkeypatch.context() as scoped:
            scoped.setattr(record_posix.fcntl, "flock", lambda *_args: None)
            scoped.setattr(record_posix, "open_identity_bound_file", lambda *_args: 7)
            scoped.setattr(record_posix, "rename_no_replace", lambda *_args: None)
            scoped.setattr(record_posix.os, "fstat", lambda _descriptor: object())
            scoped.setattr(record_posix, "file_identity", lambda _metadata: identity)
            scoped.setattr(record_posix, "entry_file_identity", lambda *_args: None)
            scoped.setattr(
                record_posix,
                "restore_staged_file",
                lambda *args: restored.append(args),
            )
            scoped.setattr(record_posix.os, "close", lambda _descriptor: None)
            with pytest.raises(OSError, match=os.strerror(errno.ESTALE)):
                record_posix.remove_owned_entry(directory_descriptor, "target", identity)
        assert restored
