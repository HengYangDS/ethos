from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.resolution._shared as resolution_shared
import ethos.adapters.mutation.resolution.records.core as record_store
import ethos.adapters.mutation.resolution.records.current.snapshot as current_snapshot
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
