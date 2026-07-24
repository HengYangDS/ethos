from __future__ import annotations

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
        lambda *args, **_kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr=""),
    )
    with pytest.raises(ValueError, match="lane_resolution_accepted_control_root_unavailable"):
        resolution_roots._registered_worktrees(tmp_path)  # noqa: SLF001, RUF100

    monkeypatch.setattr(
        resolution_roots.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(
            args[0],
            0,
            stdout=f"worktree {tmp_path}\nbranch refs/heads/dev\n\n",
            stderr="",
        ),
    )
    assert resolution_roots._registered_worktrees(tmp_path) == [  # noqa: SLF001, RUF100
        {"worktree": tmp_path.as_posix(), "branch": "refs/heads/dev"}
    ]
    assert resolution_shared.canonical_package_path(tmp_path, "invalid") is None
    outside = tmp_path.parent / "outside-record"
    assert resolution_shared.display_path(tmp_path, outside) == outside.resolve().as_posix()


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
