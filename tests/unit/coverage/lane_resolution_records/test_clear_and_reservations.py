from __future__ import annotations

import errno
import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.resolution.records.clear.core as clear_core
import ethos.adapters.mutation.resolution.records.clear.quarantine as clear_quarantine
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.inventory as record_inventory
import ethos.adapters.mutation.resolution.records.io.core as record_io
import ethos.adapters.mutation.resolution.records.io.posix as record_posix
import ethos.adapters.mutation.resolution.records.reservations as reservation_store
import ethos.adapters.mutation.resolution.records.roots as resolution_roots
from ethos.contracts.resolution.closeout import OwnerlessCloseoutReservation

_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000201"


def test_clear_quarantine_identity_accepts_only_canonical_name() -> None:
    identity = (0xABC, 0xDEF, 0o40755)
    canonical = record_store.clear_quarantine_name(_DECISION_ID, identity)
    _empty, digest, encoded, suffix = canonical.split(".")

    assert suffix == "clear-quarantine"
    assert record_store.clear_quarantine_identity(canonical, _DECISION_ID) == identity
    for malformed in (
        f".{digest}.0{encoded}.clear-quarantine",
        f".{digest}.{encoded.upper()}.clear-quarantine",
        f".{digest}.clear-quarantine",
        f".{digest}.{encoded}-1.clear-quarantine",
    ):
        assert record_store.clear_quarantine_identity(malformed, _DECISION_ID) is None


def _receipt_reservation_paths(root: Path) -> tuple[Path, Path, Path]:
    record_root = root / "records"
    destination = record_store.receipt_path(
        root,
        _DECISION_ID,
        artifact_root=record_root,
    )
    reservation = destination.with_name(f".{destination.stem}.receipt-reservation")
    reservation.parent.mkdir(parents=True)
    return record_root, destination, reservation


def _mutate_current_record(
    operation: str,
    destination: Path,
    expected: dict[str, object],
    *,
    record_root: Path,
) -> None:
    if operation == "replace":
        record_store.replace_json_atomic(
            destination,
            {"value": "new"},
            expected=expected,
            record_root=record_root,
        )
        return
    record_store.remove_record(
        destination,
        expected=expected,
        record_root=record_root,
    )


def test_receipt_reservation_reuse_rejects_pre_read_drift(
    tmp_path: Path,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")
    destination.write_text("occupied", encoding="utf-8")

    with pytest.raises(FileExistsError):
        record_store.reserve_resolution_receipt(
            root=tmp_path,
            decision_id=_DECISION_ID,
            artifact_root=record_root,
        )


def test_receipt_reservation_reuse_rejects_post_read_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")

    original_read = record_io.os.read

    def occupy_destination(descriptor: int, length: int) -> bytes:
        content = original_read(descriptor, length)
        destination.write_text("occupied", encoding="utf-8")
        return content

    monkeypatch.setattr(record_io.os, "read", occupy_destination)
    with pytest.raises(FileExistsError):
        record_store.reserve_resolution_receipt(
            root=tmp_path,
            decision_id=_DECISION_ID,
            artifact_root=record_root,
        )


def test_receipt_reservation_reuse_cannot_return_after_public_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, _destination, reservation = _receipt_reservation_paths(tmp_path)
    record_store.reserve_resolution_receipt(
        root=tmp_path,
        decision_id=_DECISION_ID,
        artifact_root=record_root,
    )
    read_complete = threading.Event()
    resume_reuse = threading.Event()
    original_read = record_io.read_descriptor_bytes
    errors: list[BaseException] = []
    returned: list[Path] = []

    def pause_after_read(descriptor: int) -> bytes:
        content = original_read(descriptor)
        if threading.current_thread().name == "reservation-reuse":
            read_complete.set()
            assert resume_reuse.wait(timeout=2)
        return content

    def reuse() -> None:
        try:
            returned.append(
                record_store.reserve_resolution_receipt(
                    root=tmp_path,
                    decision_id=_DECISION_ID,
                    artifact_root=record_root,
                )
            )
        except (OSError, ValueError) as error:
            errors.append(error)

    monkeypatch.setattr(record_io, "read_descriptor_bytes", pause_after_read)
    worker = threading.Thread(target=reuse, name="reservation-reuse")
    worker.start()
    assert read_complete.wait(timeout=2)

    record_store.release_resolution_receipt_reservation(
        root=tmp_path,
        decision_id=_DECISION_ID,
        artifact_root=record_root,
    )
    resume_reuse.set()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert returned == []
    assert len(errors) == 1
    assert isinstance(errors[0], FileExistsError)
    assert not reservation.exists()


@pytest.mark.parametrize("operation", ["replace", "remove"])
def test_mutable_record_operation_rejects_a_rebound_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    record_root = tmp_path / "records"
    category = record_root / "reservations"
    category.mkdir(parents=True)
    destination = category / "record.json"
    expected = {"value": "old"}
    destination.write_bytes(record_store.canonical_current_record_bytes(expected))
    held = record_root / "reservations-held"
    outside = tmp_path / "outside-reservations"
    outside.mkdir()
    original_open = record_io.os.open
    rebound = False

    def rebind_before_category_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal rebound
        category_open = (dir_fd is None and Path(path) == category) or (
            dir_fd is not None and path == category.name
        )
        if category_open and not rebound:
            category.rename(held)
            category.symlink_to(outside, target_is_directory=True)
            rebound = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(record_io.os, "open", rebind_before_category_open)

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        _mutate_current_record(operation, destination, expected, record_root=record_root)

    assert (held / destination.name).read_bytes() == record_store.canonical_current_record_bytes(
        expected
    )
    assert not (outside / destination.name).exists()


@pytest.mark.parametrize("operation", ["replace", "remove"])
def test_mutable_record_operation_preserves_a_post_compare_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    expected = {"value": "old"}
    competitor = {"value": "competitor"}
    destination.write_bytes(record_store.canonical_current_record_bytes(expected))
    rename_no_replace = record_posix.rename_no_replace
    raced = False

    def install_competitor_then_rename(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
    ) -> None:
        nonlocal raced
        if not raced:
            replacement = destination.with_name("replacement.json")
            replacement.write_bytes(record_store.canonical_current_record_bytes(competitor))
            replacement.replace(destination)
            raced = True
        assert rename_no_replace is not None
        rename_no_replace(directory_descriptor, source_name, target_name)

    monkeypatch.setattr(
        record_posix,
        "rename_no_replace",
        install_competitor_then_rename,
    )

    with pytest.raises(ValueError, match="lane_resolution_current_record_changed"):
        _mutate_current_record(operation, destination, expected, record_root=record_root)

    assert destination.read_bytes() == record_store.canonical_current_record_bytes(competitor)


def test_receipt_reservation_create_does_not_follow_a_rebound_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    held = record_root / "receipts-held"
    outside = tmp_path / "outside-receipts"
    outside.mkdir()
    original_open = record_io.os.open
    rebound = False

    def rebind_before_absolute_create(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal rebound
        if dir_fd is None and Path(path) == reservation and not rebound:
            destination.parent.rename(held)
            destination.parent.symlink_to(outside, target_is_directory=True)
            rebound = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(record_io.os, "open", rebind_before_absolute_create)

    created = record_store.reserve_resolution_receipt(
        root=tmp_path,
        decision_id=_DECISION_ID,
        artifact_root=record_root,
    )

    assert created == reservation
    assert reservation.read_text(encoding="utf-8") == f"{_DECISION_ID}\n"
    assert not (outside / reservation.name).exists()


def test_receipt_reservation_release_does_not_unlink_through_a_rebound_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root, destination, reservation = _receipt_reservation_paths(tmp_path)
    reservation.write_text(f"{_DECISION_ID}\n", encoding="utf-8")
    held = record_root / "receipts-held"
    outside = tmp_path / "outside-receipts"
    outside.mkdir()
    outside_reservation = outside / reservation.name
    outside_reservation.write_text("outside\n", encoding="utf-8")
    original_unlink = Path.unlink
    rebound = False

    def rebind_before_unlink(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal rebound
        if path == reservation and not rebound:
            destination.parent.rename(held)
            destination.parent.symlink_to(outside, target_is_directory=True)
            rebound = True
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", rebind_before_unlink)

    record_store.release_resolution_receipt_reservation(
        root=tmp_path,
        decision_id=_DECISION_ID,
        artifact_root=record_root,
    )

    assert outside_reservation.read_text(encoding="utf-8") == "outside\n"


def test_resolution_receipt_reservation_failure_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000102"
    with monkeypatch.context() as scoped:
        scoped.setattr(resolution_roots, "record_destination_safe", lambda *_args: False)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=decision_id,
                artifact_root=record_root,
            )

    destination = record_store.receipt_path(
        tmp_path,
        decision_id,
        artifact_root=record_root,
    )
    reservation = destination.with_name(f".{destination.stem}.receipt-reservation")
    with monkeypatch.context() as scoped:
        scoped.setattr(
            record_io.os, "fsync", lambda _descriptor: (_ for _ in ()).throw(RuntimeError)
        )
        with pytest.raises(RuntimeError):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=decision_id,
                artifact_root=record_root,
            )
    assert not reservation.exists()

    occupied_id = "lane-decision:00000000-0000-4000-8000-000000000103"
    occupied_destination = record_store.receipt_path(
        tmp_path,
        occupied_id,
        artifact_root=record_root,
    )
    original_write = record_io._write_bound_bytes  # noqa: SLF001, RUF100

    def write_then_occupy(parent: object, content: bytes) -> None:
        original_write(parent, content)
        occupied_destination.parent.mkdir(parents=True, exist_ok=True)
        occupied_destination.write_text("occupied\n", encoding="utf-8")

    with monkeypatch.context() as scoped:
        scoped.setattr(record_io, "_write_bound_bytes", write_then_occupy)
        with pytest.raises(FileExistsError):
            record_store.reserve_resolution_receipt(
                root=tmp_path,
                decision_id=occupied_id,
                artifact_root=record_root,
            )
    assert occupied_destination.is_file()

    with monkeypatch.context() as scoped:
        scoped.setattr(resolution_roots, "record_destination_safe", lambda *_args: False)
        with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
            record_store.release_resolution_receipt_reservation(
                root=tmp_path,
                decision_id=decision_id,
                artifact_root=record_root,
            )

    record_store.release_resolution_receipt_reservation(
        root=tmp_path,
        decision_id="lane-decision:00000000-0000-4000-8000-000000000104",
        artifact_root=record_root,
    )


def test_posix_rename_backend_and_error_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    class RenameAt2:
        def renameat2(self, *_args: object) -> int:
            return 0

    monkeypatch.setattr(record_posix.ctypes, "CDLL", lambda *_args, **_kwargs: RenameAt2())
    record_posix.rename_no_replace(1, "source", "target")

    monkeypatch.setattr(record_posix.ctypes, "CDLL", lambda *_args, **_kwargs: object())
    with pytest.raises(OSError, match=os.strerror(errno.ENOTSUP)) as unsupported:
        record_posix.rename_no_replace(1, "source", "target")
    assert unsupported.value.errno == errno.ENOTSUP

    class RenameAtX:
        def renameatx_np(self, *_args: object) -> int:
            return -1

    monkeypatch.setattr(record_posix.ctypes, "CDLL", lambda *_args, **_kwargs: RenameAtX())
    monkeypatch.setattr(record_posix.ctypes, "get_errno", lambda: errno.EEXIST)
    with pytest.raises(FileExistsError):
        record_posix.rename_no_replace(1, "source", "target")
    monkeypatch.setattr(record_posix.ctypes, "get_errno", lambda: errno.EIO)
    with pytest.raises(OSError, match=os.strerror(errno.EIO)) as failed:
        record_posix.rename_no_replace(1, "source", "target")
    assert failed.value.errno == errno.EIO


def test_posix_descriptor_and_bounded_read_edges(tmp_path: Path) -> None:
    with pytest.raises(OSError, match=os.strerror(errno.EINVAL)):
        record_posix.open_directory_path(tmp_path / "root" / ".." / "escape", create=False)
    assert record_posix.directory_descriptor_is_live(tmp_path, -1, (0, 0, 0)) is False
    assert (
        record_posix.child_directory_is_live(tmp_path, -1, (0, 0, 0), -1, "x", (0, 0, 0)) is False
    )
    assert record_posix.descriptor_matches_entry(-1, "x", -1) is False

    directory = tmp_path / "records"
    directory.mkdir()
    payload = directory / "payload"
    payload.write_bytes(b"content")
    descriptor = os.open(directory, record_posix.directory_flags())
    try:
        identity = record_posix.entry_file_identity(descriptor, payload.name)
        assert identity is not None
        assert record_posix.read_bound_file(descriptor, payload.name, identity, max_bytes=1) is None
    finally:
        os.close(descriptor)


@pytest.mark.parametrize(
    "case",
    [pytest.param((False, OSError), id="unsafe"), pytest.param((True, ValueError), id="changed")],
)
def test_record_root_identity_failure_edges(
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[bool, type[Exception]],
) -> None:
    changed, error_type = case
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        resolution_roots.direct_child_parts(Path("/records"), Path("/records/../escape"))
    parent = SimpleNamespace(parent_descriptor=-1)
    monkeypatch.setattr(record_posix, "entry_file_identity", lambda *_args: None)
    with pytest.raises(error_type):
        resolution_roots.require_entry_identity(parent, "record", changed=changed)


def test_record_io_lock_and_validation_failure_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = SimpleNamespace(
        parent_descriptor=1, destination=Path("record.json"), name="record.json"
    )
    monkeypatch.setattr(
        record_posix,
        "lock_regular_file",
        lambda *_args: (_ for _ in ()).throw(BlockingIOError),
    )
    with pytest.raises(FileExistsError):
        record_io._lock_existing_bound_record(parent, b"expected")  # noqa: SLF001, RUF100

    unlocked: list[int] = []
    monkeypatch.setattr(record_posix, "lock_regular_file", lambda *_args: 7)
    monkeypatch.setattr(
        record_io,
        "_require_locked_record_content",
        lambda *_args: (_ for _ in ()).throw(ValueError("changed")),
    )
    monkeypatch.setattr(record_posix, "unlock_close", unlocked.append)
    with pytest.raises(ValueError, match="changed"):
        record_io._lock_existing_bound_record(parent, b"expected")  # noqa: SLF001, RUF100
    assert unlocked == [7]

    monkeypatch.setattr(record_io, "_read_bound_bytes", lambda *_args: b"other")
    monkeypatch.setattr(record_posix, "entry_file_identity", lambda *_args: (1, 2, 3, 4, 5, 6))
    with pytest.raises(ValueError, match="lane_resolution_current_record_changed"):
        record_io._require_record(  # noqa: SLF001, RUF100
            parent,
            (1, 2, 3, 4, 5, 6),
            b"expected",
            changed=True,
        )
    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_io._require_record(  # noqa: SLF001, RUF100
            parent,
            (1, 2, 3, 4, 5, 6),
            b"expected",
            changed=False,
        )


def test_clear_core_mapping_and_validation_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observation = SimpleNamespace(record_root=tmp_path / "records")
    assert (
        clear_core._prepare_quarantine(  # noqa: SLF001, RUF100
            tmp_path,
            _DECISION_ID,
            observation,
            {"package_identity": None},
            tmp_path / _DECISION_ID,
        )[2]
        == "lane_resolution_clear_package_identity_mismatch"
    )
    monkeypatch.setattr(clear_core, "record_destination_safe", lambda *_args: False)
    assert (
        clear_core._prepare_quarantine(  # noqa: SLF001, RUF100
            tmp_path,
            _DECISION_ID,
            observation,
            {"package_identity": (1, 2, 0o40700)},
            tmp_path / _DECISION_ID,
        )[2]
        == "lane_resolution_clear_quarantine_path_unsafe"
    )
    assert [
        clear_core._move_gap(state)  # noqa: SLF001, RUF100 - coverage probes the internal gap table
        for state in ("moved", "collision", "identity_mismatch", "failed")
    ] == [
        "",
        "lane_resolution_clear_quarantine_collision",
        "lane_resolution_clear_package_identity_mismatch",
        "lane_resolution_clear_quarantine_failed",
    ]
    assert (
        clear_core._records_owner_gap(  # noqa: SLF001, RUF100
            ValueError("lane_resolution_accepted_control_root_unavailable")
        )
        == "lane_resolution_accepted_control_root_unavailable"
    )
    with pytest.raises(ValueError, match="other"):
        clear_core._records_owner_gap(ValueError("other"))  # noqa: SLF001, RUF100
    monkeypatch.setattr(
        clear_core, "validate_schema_instance", lambda *_args, **_kwargs: {"ok": False}
    )
    with pytest.raises(ValueError, match="lane_resolution_receipt_invalid"):
        clear_core._validate_clear_schema(tmp_path, {})  # noqa: SLF001, RUF100


def test_clear_quarantine_binding_and_candidate_edges(tmp_path: Path) -> None:
    manifest = {
        "bundle_sha256": "a" * 64,
        "patch_sha256": "b" * 64,
        "untracked_archive_sha256": "c" * 64,
    }
    assert clear_quarantine.quarantined_payloads_match(
        manifest,
        {"untracked.tar": "c" * 64},
        {"untracked.tar"},
    )
    assert clear_quarantine.exact_package_binding({}) is None
    assert (
        clear_quarantine.exact_package_binding(
            {"package_names": {1}, "payload_sha256": {}, "payload_identities": {}}
        )
        is None
    )
    assert clear_quarantine.exact_clear_receipt({}, {}) is False

    identity = (1, 2, 0o40700)
    name = record_store.clear_quarantine_name(_DECISION_ID, identity)
    source = clear_quarantine.ClearQuarantineCandidate(
        path=tmp_path / name,
        payload_sha256={},
        package_names=set(),
        payload_identities={},
        entry_identity=identity,
    )
    clears = {_DECISION_ID: {"manifest_sha256": "d" * 64}}
    records, invalid = clear_quarantine.clear_quarantines(tmp_path, (source,), clears, {})
    assert records[_DECISION_ID]["package_identity"] == identity
    assert invalid == []
    records, invalid = clear_quarantine.clear_quarantines(tmp_path, (source, source), clears, {})
    assert records == {}
    assert invalid == [source.path, source.path]


def test_ownerless_inventory_and_reservation_reader_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = OwnerlessCloseoutReservation(
        schema_version=2,
        decision_id=_DECISION_ID,
        lane_ref="work/example",
        head="a" * 40,
        executor_ref="agent:codex:thread:executor",
        decision_sha256="b" * 64,
        accepted_branch="dev",
        accepted_head="c" * 40,
        target_digest=reservation_store.target_digest("work/example", "a" * 40),
        target_binding_digest="d" * 64,
        phase="reserved",
        recovery_state="reserved_no_effect",
        postcondition_digest="",
    )
    monkeypatch.setattr(
        record_inventory,
        "read_current_lane_resolution_records",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )
    with pytest.raises(ValueError, match="lane_resolution_current_record_invalid"):
        record_inventory.ownerless_closeout_reservation_admission(
            root=tmp_path,
            record_root=tmp_path / "records",
            decision_path=tmp_path / "decision.json",
            decision_sha256=expected.decision_sha256,
            expected=expected,
        )

    monkeypatch.setattr(
        reservation_store,
        "read_descriptor_bytes",
        lambda _descriptor: (_ for _ in ()).throw(OSError("unreadable")),
    )
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        reservation_store._read_locked_ownerless_reservation(7)  # noqa: SLF001, RUF100
    monkeypatch.setattr(reservation_store, "read_descriptor_bytes", lambda _descriptor: b"{")
    with pytest.raises(ValueError, match="lane_resolution_ownerless_reservation_invalid"):
        reservation_store._read_locked_ownerless_reservation(7)  # noqa: SLF001, RUF100
