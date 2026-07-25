from __future__ import annotations

import stat
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.io.core as record_io
import ethos.adapters.mutation.resolution.records.io.posix as record_posix

if TYPE_CHECKING:
    import os
    from pathlib import Path


def test_record_write_fsync_failure_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "receipts" / "record.json"
    destination.parent.mkdir(parents=True)
    original_fsync = record_io.os.fsync
    failed = False
    message = "temporary fsync interrupted"

    def fail_temporary_fsync(descriptor: int) -> None:
        nonlocal failed
        if not failed and stat.S_ISREG(record_io.os.fstat(descriptor).st_mode):
            failed = True
            raise OSError(message)
        original_fsync(descriptor)

    monkeypatch.setattr(record_io.os, "fsync", fail_temporary_fsync)

    with pytest.raises(OSError, match=message):
        record_store.write_json_atomic(destination, {"value": "new"}, record_root=record_root)

    assert failed is True
    assert not destination.exists()
    assert tuple(destination.parent.iterdir()) == ()


def test_record_write_failure_does_not_unlink_rebound_temporary_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "receipts" / "record.json"
    destination.parent.mkdir(parents=True)
    competitor = b"competitor\n"
    message = "temporary writer interrupted"

    def replace_temporary_then_fail(_descriptor: int, _content: bytes) -> None:
        temporary = next(destination.parent.glob("*.tmp"))
        temporary.unlink()
        temporary.write_bytes(competitor)
        raise OSError(message)

    monkeypatch.setattr(record_posix, "write_all", replace_temporary_then_fail)

    with pytest.raises(OSError, match=message):
        record_store.write_json_atomic(destination, {"value": "new"}, record_root=record_root)

    temporary = tuple(destination.parent.glob("*.tmp"))
    assert len(temporary) == 1
    assert temporary[0].read_bytes() == competitor
    assert not destination.exists()


def test_record_write_unlinks_temporary_before_final_directory_fsync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "receipts" / "record.json"
    destination.parent.mkdir(parents=True)
    original_fsync = record_io.os.fsync
    observed_directory_fsync = False

    def require_clean_directory_fsync(descriptor: int) -> None:
        nonlocal observed_directory_fsync
        if stat.S_ISDIR(record_io.os.fstat(descriptor).st_mode):
            observed_directory_fsync = True
            assert not tuple(destination.parent.glob("*.tmp"))
        original_fsync(descriptor)

    monkeypatch.setattr(record_io.os, "fsync", require_clean_directory_fsync)

    record_store.write_json_atomic(destination, {"value": "new"}, record_root=record_root)

    assert observed_directory_fsync is True
    assert destination.is_file()


@pytest.mark.parametrize("failure", ["open", "read"])
def test_record_replace_restores_canonical_after_staged_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    expected = {"value": "old"}
    replacement = {"value": "new"}
    expected_bytes = record_store.canonical_current_record_bytes(expected)
    destination.write_bytes(expected_bytes)
    original_open = record_io.os.open
    original_read = record_io.read_descriptor_bytes
    staged_descriptor: int | None = None
    message = f"staged {failure} interrupted"

    def fail_staged_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal staged_descriptor
        staged = dir_fd is not None and str(path).endswith(".cas")
        if staged and failure == "open":
            raise OSError(message)
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        if staged:
            staged_descriptor = descriptor
        return descriptor

    def fail_staged_read(descriptor: int) -> bytes:
        if failure == "read" and descriptor == staged_descriptor:
            raise OSError(message)
        return original_read(descriptor)

    monkeypatch.setattr(record_io.os, "open", fail_staged_open)
    monkeypatch.setattr(record_io, "read_descriptor_bytes", fail_staged_read)

    with pytest.raises(OSError, match=message):
        record_store.replace_json_atomic(
            destination,
            replacement,
            expected=expected,
            record_root=record_root,
        )

    assert destination.read_bytes() == expected_bytes
    assert not tuple(destination.parent.glob("*.cas"))
    assert not tuple(destination.parent.glob("*.tmp"))


def test_record_replace_post_rename_identity_failure_restores_canonical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    expected = {"value": "old"}
    expected_bytes = record_store.canonical_current_record_bytes(expected)
    destination.write_bytes(expected_bytes)
    original_identity = record_posix.entry_file_identity
    staged_identity_reads = 0
    message = "staged identity interrupted"

    def fail_staged_identity(descriptor: int, name: str):
        nonlocal staged_identity_reads
        if name.endswith(".cas"):
            staged_identity_reads += 1
            if staged_identity_reads == 2:
                raise OSError(message)
        return original_identity(descriptor, name)

    monkeypatch.setattr(record_posix, "entry_file_identity", fail_staged_identity)

    with pytest.raises(OSError, match=message):
        record_store.replace_json_atomic(
            destination,
            {"value": "new"},
            expected=expected,
            record_root=record_root,
        )

    assert staged_identity_reads >= 3
    assert destination.read_bytes() == expected_bytes
    assert not tuple(destination.parent.glob("*.cas"))
    assert not tuple(destination.parent.glob("*.tmp"))


def test_record_replace_directory_fsync_failure_rolls_back_without_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    expected = {"value": "old"}
    replacement = {"value": "new"}
    expected_bytes = record_store.canonical_current_record_bytes(expected)
    replacement_bytes = record_store.canonical_current_record_bytes(replacement)
    destination.write_bytes(expected_bytes)
    original_fsync = record_io.os.fsync
    failed = False
    message = "replacement directory fsync interrupted"

    def fail_final_replace_fsync(descriptor: int) -> None:
        nonlocal failed
        metadata = record_io.os.fstat(descriptor)
        directory = destination.parent.stat()
        is_target_directory = (metadata.st_dev, metadata.st_ino) == (
            directory.st_dev,
            directory.st_ino,
        )
        if (
            not failed
            and is_target_directory
            and destination.is_file()
            and destination.read_bytes() == replacement_bytes
        ):
            failed = True
            raise OSError(message)
        original_fsync(descriptor)

    monkeypatch.setattr(record_io.os, "fsync", fail_final_replace_fsync)

    with pytest.raises(OSError, match=message):
        record_store.replace_json_atomic(
            destination,
            replacement,
            expected=expected,
            record_root=record_root,
        )

    assert failed is True
    assert destination.read_bytes() == expected_bytes
    assert not tuple(destination.parent.glob("*.cas"))
    assert not tuple(destination.parent.glob("*.tmp"))


def test_record_replace_staging_tombstone_unlink_failure_restores_previous_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    expected = {"value": "old"}
    expected_bytes = record_store.canonical_current_record_bytes(expected)
    destination.write_bytes(expected_bytes)
    original_unlink = record_io.os.unlink
    failed = False
    message = "staging tombstone unlink interrupted"

    def fail_staging_tombstone_unlink(
        path: object,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal failed
        candidate = str(path)
        if not failed and ".cas." in candidate and candidate.endswith(".delete"):
            failed = True
            raise OSError(message)
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(record_io.os, "unlink", fail_staging_tombstone_unlink)

    with pytest.raises(OSError, match=message):
        record_store.replace_json_atomic(
            destination,
            {"value": "new"},
            expected=expected,
            record_root=record_root,
        )

    assert failed is True
    assert destination.read_bytes() == expected_bytes
    assert not tuple(destination.parent.glob("*.cas"))
    assert not tuple(destination.parent.glob("*.tmp"))
    assert not tuple(destination.parent.glob("*.delete"))


def test_record_replace_staging_delete_fsync_failure_preserves_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    expected = {"value": "old"}
    replacement = {"value": "new"}
    replacement_bytes = record_store.canonical_current_record_bytes(replacement)
    destination.write_bytes(record_store.canonical_current_record_bytes(expected))
    original_fsync = record_io.os.fsync
    failed = False
    message = "staging delete directory fsync interrupted"

    def fail_staging_delete_fsync(descriptor: int) -> None:
        nonlocal failed
        metadata = record_io.os.fstat(descriptor)
        directory = destination.parent.stat()
        is_target_directory = (metadata.st_dev, metadata.st_ino) == (
            directory.st_dev,
            directory.st_ino,
        )
        has_staging = any(".cas" in path.name for path in destination.parent.iterdir())
        if (
            not failed
            and is_target_directory
            and destination.is_file()
            and destination.read_bytes() == replacement_bytes
            and not has_staging
        ):
            failed = True
            raise OSError(message)
        original_fsync(descriptor)

    monkeypatch.setattr(record_io.os, "fsync", fail_staging_delete_fsync)

    with pytest.raises(OSError, match=message):
        record_store.replace_json_atomic(
            destination,
            replacement,
            expected=expected,
            record_root=record_root,
        )

    assert failed is True
    assert destination.read_bytes() == replacement_bytes
    assert not tuple(destination.parent.glob("*.cas"))
    assert not tuple(destination.parent.glob("*.tmp"))
    assert not tuple(destination.parent.glob("*.delete"))


def test_record_replace_rejects_staging_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "reservations" / "record.json"
    destination.parent.mkdir(parents=True)
    expected = {"value": "old"}
    expected_bytes = record_store.canonical_current_record_bytes(expected)
    destination.write_bytes(expected_bytes)
    original_open = record_posix.open_regular_file
    stolen_name = ".stolen-old"
    staging_name = ""
    swapped = False

    def swap_staging_before_open(directory_descriptor: int, name: str) -> int:
        nonlocal staging_name, swapped
        if not swapped and name.endswith(".cas"):
            record_posix.os.rename(
                name,
                stolen_name,
                src_dir_fd=directory_descriptor,
                dst_dir_fd=directory_descriptor,
            )
            descriptor = record_posix.os.open(
                name,
                record_posix.os.O_WRONLY | record_posix.os.O_CREAT | record_posix.os.O_EXCL,
                0o600,
                dir_fd=directory_descriptor,
            )
            try:
                record_posix.write_all(descriptor, expected_bytes)
                record_posix.os.fsync(descriptor)
            finally:
                record_posix.os.close(descriptor)
            staging_name = name
            swapped = True
        return original_open(directory_descriptor, name)

    monkeypatch.setattr(record_posix, "open_regular_file", swap_staging_before_open)

    with pytest.raises(OSError, match="Stale"):
        record_store.replace_json_atomic(
            destination,
            {"value": "new"},
            expected=expected,
            record_root=record_root,
        )

    assert swapped is True
    assert (destination.parent / stolen_name).read_bytes() == expected_bytes
    assert (destination.parent / staging_name).read_bytes() == expected_bytes
    assert not destination.exists()


def test_record_write_preserves_same_inode_competitor_on_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    destination = record_root / "receipts" / "record.json"
    destination.parent.mkdir(parents=True)
    payload = {"value": "new"}
    canonical = record_store.canonical_current_record_bytes(payload)
    competitor = b"!" * len(canonical)
    message = "post-link validation interrupted"
    mutated = False

    def overwrite_then_fail(
        _parent: object,
        identity: record_posix.FileIdentity,
        _content: bytes,
        *,
        changed: bool,
    ) -> None:
        nonlocal mutated
        assert changed is False
        metadata = destination.stat()
        with destination.open("r+b", buffering=0) as stream:
            stream.write(competitor)
            record_io.os.fsync(stream.fileno())
        record_io.os.utime(
            destination,
            ns=(metadata.st_atime_ns, identity[4]),
            follow_symlinks=False,
        )
        current = record_posix.file_identity(destination.stat())
        assert current[:5] == identity[:5]
        assert current != identity
        mutated = True
        raise OSError(message)

    monkeypatch.setattr(
        record_io,
        "_require_record",
        overwrite_then_fail,  # noqa: SLF001, RUF100 - exact rollback fault injection
    )

    with pytest.raises(OSError, match=message):
        record_store.write_json_atomic(destination, payload, record_root=record_root)

    assert mutated is True
    assert destination.read_bytes() == competitor


def test_owned_entry_removal_restores_competitor_moved_to_private_tombstone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "records" / "record.json"
    destination.parent.mkdir()
    destination.write_bytes(b"owned\n")
    competitor = b"competitor\n"
    directory = record_posix.open_directory_path(destination.parent, create=False)
    identity = record_posix.entry_file_identity(directory, destination.name)
    assert identity is not None
    original_rename = record_posix.rename_no_replace
    raced = False

    def swap_before_quarantine(
        directory_descriptor: int,
        source_name: str,
        target_name: str,
    ) -> None:
        nonlocal raced
        if not raced and source_name == destination.name and target_name.endswith(".delete"):
            record_posix.os.unlink(source_name, dir_fd=directory_descriptor)
            descriptor = record_posix.os.open(
                source_name,
                record_posix.os.O_WRONLY | record_posix.os.O_CREAT | record_posix.os.O_EXCL,
                0o600,
                dir_fd=directory_descriptor,
            )
            try:
                record_posix.write_all(descriptor, competitor)
                record_posix.os.fsync(descriptor)
            finally:
                record_posix.os.close(descriptor)
            raced = True
        original_rename(directory_descriptor, source_name, target_name)

    monkeypatch.setattr(record_posix, "rename_no_replace", swap_before_quarantine)

    try:
        with pytest.raises(OSError, match="Stale"):
            record_posix.remove_owned_entry(directory, destination.name, identity)
    finally:
        record_posix.os.close(directory)

    assert raced is True
    assert destination.read_bytes() == competitor
    assert not tuple(destination.parent.glob("*.delete"))
