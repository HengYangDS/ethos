from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.resolution._shared as resolution_shared
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.current.snapshot as current_snapshot
import ethos.adapters.mutation.resolution.records.io.core as record_io
import ethos.adapters.mutation.resolution.records.io.posix as record_posix
import ethos.adapters.mutation.resolution.records.roots as resolution_roots
from ethos.adapters.mutation.resolution.lane import plan_lane_resolution
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.mutation.resolution.records.roots import historical_record_roots
from ethos.surface.cli.lane.resolution import _default_decision_path
from tests.support.contract_helpers import write_chronicle_decision
from tests.support.lane_helpers import init_repo
from tests.support.lane_helpers import orphan_work_lane


def test_record_roots_separate_current_v2_from_immutable_history(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    current = current_record_root(repo)
    history = historical_record_roots(repo)

    assert current == tmp_path / "repo-records/recovery/lane-resolution-v2"
    assert history == (
        tmp_path / "repo-records/recovery/lane-resolution",
        repo / "build/artifacts/lane-resolution",
    )
    assert current not in history


def test_current_record_root_does_not_fallback_to_populated_history(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    history = historical_record_roots(repo)
    for record_root in history:
        record_root.mkdir(parents=True)

    current = current_record_root(repo)

    assert current == tmp_path / "repo-records/recovery/lane-resolution-v2"
    assert not current.exists()
    assert all(record_root.is_dir() for record_root in history)


def test_accepted_control_root_rejects_missing_head_or_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resolution_roots, "_primary_control_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        resolution_roots,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(accepted_branch="dev"),
    )
    monkeypatch.setattr(resolution_roots, "_git_output", lambda *_args: "")
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_roots.accepted_control_root(tmp_path)

    missing = tmp_path / "missing"
    monkeypatch.setattr(resolution_roots, "_git_output", lambda *_args: "a" * 40)
    monkeypatch.setattr(
        resolution_roots,
        "_registered_worktrees",
        lambda _root: [
            {"branch": "refs/heads/other", "worktree": tmp_path.as_posix()},
            {"branch": "refs/heads/dev", "worktree": missing.as_posix()},
        ],
    )
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_roots.accepted_control_root(tmp_path)


def test_record_root_parser_and_shared_path_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        resolution_roots,
        "_git_output",
        lambda *_args: (tmp_path / "missing" / ".git").as_posix(),
    )
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_roots._primary_control_root(tmp_path)  # noqa: SLF001, RUF100

    monkeypatch.setattr(
        resolution_roots.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(args[0], 1, stdout=b"", stderr=b""),
    )
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_roots._registered_worktrees(tmp_path)  # noqa: SLF001, RUF100

    monkeypatch.setattr(
        resolution_roots.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(
            args[0],
            0,
            stdout=f"worktree {tmp_path}\nHEAD {'a' * 40}\nbranch refs/heads/dev\n\n".encode(),
            stderr=b"",
        ),
    )
    assert resolution_roots._registered_worktrees(tmp_path) == [  # noqa: SLF001, RUF100
        {"worktree": tmp_path.as_posix(), "HEAD": "a" * 40, "branch": "refs/heads/dev"}
    ]
    assert resolution_shared.canonical_package_path(tmp_path, "invalid") is None
    outside = tmp_path.parent / "outside-record"
    assert resolution_shared.display_path(tmp_path, outside) == outside.resolve().as_posix()


def test_registered_worktrees_uses_hardened_byte_git_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    head = b"a" * 40
    stdout = (
        b"worktree "
        + tmp_path.as_posix().encode()
        + b"\nHEAD "
        + head
        + b"\nbranch refs/heads/dev\nlocked maintenance\n\n"
    )

    def run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured.update(kwargs)
        return subprocess.CompletedProcess(args[0], 0, stdout=stdout, stderr=b"")

    monkeypatch.setattr(resolution_roots.subprocess, "run", run)

    assert resolution_roots._registered_worktrees(tmp_path) == [  # noqa: SLF001, RUF100
        {"worktree": tmp_path.as_posix(), "HEAD": "a" * 40, "branch": "refs/heads/dev"}
    ]
    assert captured["shell"] is False
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["LC_ALL"] == "C"
    assert environment["GIT_OPTIONAL_LOCKS"] == "0"
    assert environment["GIT_CONFIG_NOSYSTEM"] == "1"
    assert environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert environment["GIT_ATTR_NOSYSTEM"] == "1"
    assert "text" not in captured


@pytest.mark.parametrize(
    ("stdout", "stderr"),
    [
        (
            b"worktree /tmp/accepted\nHEAD " + b"a" * 40 + b"\nbranch refs/heads/dev\n\n",
            b"warning\n",
        ),
        (
            b"worktree /tmp/accepted\nworktree /tmp/other\nHEAD "
            + b"a" * 40
            + b"\nbranch refs/heads/dev\n\n",
            b"",
        ),
        (
            b"worktree /tmp/accepted\nHEAD "
            + b"a" * 40
            + b"\nbranch refs/heads/dev\nunexpected value\n\n",
            b"",
        ),
    ],
    ids=("stderr", "duplicate-field", "unknown-field"),
)
def test_registered_worktrees_rejects_untrusted_porcelain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: bytes,
    stderr: bytes,
) -> None:
    monkeypatch.setattr(
        resolution_roots.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(
            args[0], 0, stdout=stdout, stderr=stderr
        ),
    )

    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_roots._registered_worktrees(tmp_path)  # noqa: SLF001, RUF100


def test_current_record_create_rejects_intermediate_root_rebind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = tmp_path / "record-owner"
    record_root = owner / "records"
    destination = record_root / "receipts" / "record.json"
    destination.parent.mkdir(parents=True)
    held = tmp_path / "record-owner-held"
    outside_owner = tmp_path / "outside-owner"
    outside_destination = outside_owner / "records" / "receipts" / destination.name
    outside_destination.parent.mkdir(parents=True)
    original_open = record_posix.os.open
    rebound = False

    def rebind_before_root_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal rebound
        absolute_open = dir_fd is None and Path(path) == record_root
        component_open = dir_fd is not None and path == owner.name
        if (absolute_open or component_open) and not rebound:
            owner.rename(held)
            owner.symlink_to(outside_owner, target_is_directory=True)
            rebound = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(record_posix.os, "open", rebind_before_root_open)

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.write_json_atomic(destination, {"value": "inside"}, record_root=record_root)

    assert rebound is True
    assert not outside_destination.exists()


def test_current_snapshot_rejects_intermediate_root_rebind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = tmp_path / "snapshot-owner"
    record_root = owner / "records"
    (record_root / "decisions").mkdir(parents=True)
    held = tmp_path / "snapshot-owner-held"
    outside_owner = tmp_path / "outside-snapshot-owner"
    outside_root = outside_owner / "records"
    (outside_root / "decisions").mkdir(parents=True)
    original_open = current_snapshot.os.open
    rebound = False

    def rebind_before_root_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal rebound
        absolute_open = dir_fd is None and Path(path) == record_root
        component_open = dir_fd is not None and path == owner.name
        if (absolute_open or component_open) and not rebound:
            owner.rename(held)
            owner.symlink_to(outside_owner, target_is_directory=True)
            rebound = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(current_snapshot.os, "open", rebind_before_root_open)

    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)

    assert rebound is True
    assert snapshot is None
    assert state == "invalid"


def test_plan_decision_does_not_open_an_absolute_rebound_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    decision_path = _default_decision_path(repo, "work/orphan")
    record_root = current_record_root(repo)
    decision_path.parent.mkdir(parents=True)
    owner = record_root.parents[1]
    held = owner.with_name(f"{owner.name}-held")
    outside_owner = tmp_path / "outside-record-owner"
    outside_decision = (
        outside_owner / record_root.relative_to(owner) / "decisions" / decision_path.name
    )
    outside_decision.parent.mkdir(parents=True)
    original_open = Path.open
    rebound = False

    def rebind_before_decision_open(
        path: Path,
        *args: object,
        **kwargs: object,
    ) -> object:
        nonlocal rebound
        if path == decision_path and not rebound:
            owner.rename(held)
            owner.symlink_to(outside_owner, target_is_directory=True)
            rebound = True
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", rebind_before_decision_open)

    report = plan_lane_resolution(
        root=repo,
        branch="work/orphan",
        disposition="block",
        reason="Decision writes must stay bound to the current record root.",
        evidence_refs=("evidence:record-edges",),
        chronicle_ref=write_chronicle_decision(
            repo,
            topic="lane-resolution-record-edges",
            token="block",
        ),
        recovery_plan="Keep the exact lane unchanged.",
        decision_path=decision_path,
        break_glass=False,
        apply=True,
    )

    assert report["ok"] is True
    assert outside_decision.exists() is False


def test_current_record_write_rejects_post_open_ancestor_detach(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = tmp_path / "record-owner"
    record_root = owner / "records"
    destination = record_root / "receipts" / "record.json"
    destination.parent.mkdir(parents=True)
    held_owner = tmp_path / "record-owner-held"
    original_write = record_posix.write_all
    detached = False

    def detach_after_parent_open(descriptor: int, content: bytes) -> None:
        nonlocal detached
        if not detached:
            owner.rename(held_owner)
            destination.parent.mkdir(parents=True)
            detached = True
        original_write(descriptor, content)

    monkeypatch.setattr(record_posix, "write_all", detach_after_parent_open)

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        record_store.write_json_atomic(destination, {"value": "detached"}, record_root=record_root)

    assert detached is True
    assert not destination.exists()
    assert not (held_owner / "records" / "receipts" / destination.name).exists()
    assert not tuple((held_owner / "records" / "receipts").glob("*.tmp"))


def test_current_snapshot_rejects_post_open_ancestor_detach(tmp_path: Path) -> None:
    owner = tmp_path / "snapshot-owner"
    record_root = owner / "records"
    (record_root / "decisions").mkdir(parents=True)
    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)
    assert snapshot is not None
    assert state == "valid"

    held_owner = tmp_path / "snapshot-owner-held"
    owner.rename(held_owner)
    (record_root / "decisions").mkdir(parents=True)
    (record_root / "unexpected").write_text("visible after detach\n", encoding="utf-8")

    with snapshot, pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        _ = snapshot.names


def test_receipt_sidecar_claim_cannot_split_across_category_detach(tmp_path: Path) -> None:
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000201"
    record_root = tmp_path / "records"
    receipt = record_store.receipt_path(tmp_path, decision_id, artifact_root=record_root)
    category = receipt.parent
    category.mkdir(parents=True)
    reservation = receipt.with_name(f".{receipt.stem}.receipt-reservation")
    held_category = record_root / "receipts-held"

    def detach_claim_and_probe() -> None:
        with record_store.claim_resolution_receipt_reservation(
            root=tmp_path,
            decision_id=decision_id,
            artifact_root=record_root,
            mode="create",
        ) as locked_descriptor:
            assert locked_descriptor is not None
            category.rename(held_category)
            category.mkdir()
            with (
                pytest.raises(FileExistsError),
                record_store.claim_resolution_receipt_reservation(
                    root=tmp_path,
                    decision_id=decision_id,
                    artifact_root=record_root,
                    mode="recover",
                ),
            ):
                pytest.fail("a detached sidecar must not admit a second canonical lock")
            category.rmdir()
            with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
                record_store.release_resolution_receipt_reservation(
                    root=tmp_path,
                    decision_id=decision_id,
                    artifact_root=record_root,
                    locked_descriptor=locked_descriptor,
                )

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        detach_claim_and_probe()

    assert not reservation.exists()
    assert (held_category / reservation.name).is_file()


@pytest.mark.parametrize("detached_component", ["record_root", "ancestor"])
def test_receipt_sidecar_claim_cannot_split_across_lineage_detach(
    tmp_path: Path,
    detached_component: str,
) -> None:
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000202"
    owner = tmp_path / "owner"
    record_root = owner / "records"
    receipt = record_store.receipt_path(tmp_path, decision_id, artifact_root=record_root)
    receipt.parent.mkdir(parents=True)
    reservation = receipt.with_name(f".{receipt.stem}.receipt-reservation")
    held_owner = tmp_path / "owner-held"
    held_root = owner / "records-held"
    old_record_root = held_root if detached_component == "record_root" else held_owner / "records"

    def detach_claim_and_probe() -> None:
        with record_store.claim_resolution_receipt_reservation(
            root=tmp_path,
            decision_id=decision_id,
            artifact_root=record_root,
            mode="create",
        ) as locked_descriptor:
            assert locked_descriptor is not None
            if detached_component == "record_root":
                record_root.rename(held_root)
            else:
                owner.rename(held_owner)
            receipt.parent.mkdir(parents=True)
            with (
                pytest.raises(FileExistsError),
                record_store.claim_resolution_receipt_reservation(
                    root=tmp_path,
                    decision_id=decision_id,
                    artifact_root=record_root,
                    mode="recover",
                ),
            ):
                pytest.fail("a detached lineage must not admit a second canonical lock")

    with pytest.raises(OSError, match="lane_resolution_record_path_unsafe"):
        detach_claim_and_probe()

    assert not reservation.exists()
    assert (old_record_root / "receipts" / reservation.name).is_file()


def test_receipt_sidecar_claim_preserves_caller_blocking_error(tmp_path: Path) -> None:
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000203"
    message = "caller body blocked"
    record_root = tmp_path / "records"
    record_store.receipt_path(tmp_path, decision_id, artifact_root=record_root).parent.mkdir(
        parents=True
    )

    with (
        pytest.raises(BlockingIOError, match=message),
        record_store.claim_resolution_receipt_reservation(
            root=tmp_path,
            decision_id=decision_id,
            artifact_root=record_root,
            mode="create",
        ),
    ):
        raise BlockingIOError(message)


def test_receipt_sidecar_claim_preserves_caller_value_error(tmp_path: Path) -> None:
    decision_id = "lane-decision:00000000-0000-4000-8000-000000000204"
    message = "caller value invalid"
    record_root = tmp_path / "records"
    record_store.receipt_path(tmp_path, decision_id, artifact_root=record_root).parent.mkdir(
        parents=True
    )

    with (
        pytest.raises(ValueError, match=message),
        record_store.claim_resolution_receipt_reservation(
            root=tmp_path,
            decision_id=decision_id,
            artifact_root=record_root,
            mode="create",
        ),
    ):
        raise ValueError(message)


def test_current_snapshot_closes_descriptor_on_root_binding_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record_root = tmp_path / "records"
    (record_root / "decisions").mkdir(parents=True)
    (record_root / "decisions/decision.json").write_text("{}\n", encoding="utf-8")
    original_open = current_snapshot.posix.open_directory_path
    original_close = current_snapshot.os.close
    opened: list[int] = []

    def track_open(path: Path, *, create: bool) -> int:
        descriptor = original_open(path, create=create)
        opened.append(descriptor)
        return descriptor

    def track_close(descriptor: int) -> None:
        original_close(descriptor)

    monkeypatch.setattr(current_snapshot.posix, "open_directory_path", track_open)
    monkeypatch.setattr(
        current_snapshot.posix,
        "directory_path_identity",
        lambda _path: (-1, -1, -1),
    )
    monkeypatch.setattr(current_snapshot.os, "close", track_close)

    snapshot, state = current_snapshot.open_current_record_snapshot(record_root)

    assert snapshot is None
    assert state == "invalid"
    with pytest.raises(OSError, match="Bad file descriptor"):
        current_snapshot.os.fstat(opened[0])


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
