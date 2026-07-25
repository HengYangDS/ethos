from __future__ import annotations

import threading
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.io.core as record_io
import ethos.adapters.mutation.resolution.records.io.posix as record_posix
import ethos.adapters.mutation.resolution.records.roots as resolution_roots

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
