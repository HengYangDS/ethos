from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_start_rollback as rollback

if TYPE_CHECKING:
    from pathlib import Path


def _completed(stderr: str = "initialization failed") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(("git",), 1, "", stderr)


def _lease() -> dict[str, object]:
    return {
        "holder_ref": "agent:test:case:owner",
        "lease_id": "lease:1",
        "epoch": 3,
        "expected_head": "a" * 40,
        "expires_at": "2026-08-10T00:00:00+00:00",
        "payload_sha256": "b" * 64,
    }


def _run_worktree_list(
    target: Path,
    *,
    branch: str = "work/example",
    head: str = "a" * 40,
    returncode: int = 0,
):
    output = f"worktree {target}\nHEAD {head}\nbranch refs/heads/{branch}\n"

    def run(*_args, **_kwargs):
        return subprocess.CompletedProcess(("git",), returncode, output, "")

    return run


def test_worktree_head_rejects_failed_or_mismatched_observation(tmp_path: Path) -> None:
    assert (
        rollback.worktree_head(
            tmp_path,
            target=tmp_path / "lane",
            branch="work/example",
            run=_run_worktree_list(tmp_path / "lane", returncode=1),
        )
        is None
    )
    assert (
        rollback.worktree_head(
            tmp_path,
            target=tmp_path / "lane",
            branch="work/other",
            run=_run_worktree_list(tmp_path / "lane"),
        )
        is None
    )


@pytest.mark.parametrize(
    ("target_exists", "ref_head", "expected_gap"),
    [
        (True, "", "lane_start_target_path_ownership_unknown"),
        (False, "a" * 40, "lane_start_target_ref_ownership_unknown"),
    ],
)
def test_rollback_retains_unknown_carrier_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_exists: object,
    ref_head: str,
    expected_gap: str,
) -> None:
    target = tmp_path / "lane"
    if target_exists:
        target.mkdir()
    monkeypatch.setattr(rollback, "ref_head", lambda *_args: ref_head)
    context = rollback.LaneStartRollback(
        repo=tmp_path,
        target=target,
        branch="work/example",
        ownership=("work/example", "a" * 40, "a" * 40),
        completed=_completed(),
        run=lambda *_args, **_kwargs: subprocess.CompletedProcess(("git",), 0, "", ""),
        lease=None,
        source_lease={},
        failure_gap="lane_start_failed",
    )

    report = rollback.rollback_lane_start(context)

    assert report["required_gaps"] == ["lane_creation_compensation_failed", expected_gap]
    assert report["lease_state"] == "not_acquired"


def test_rollback_reports_cleanup_failure_without_deleting_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "lane"
    target.mkdir()
    monkeypatch.setattr(rollback, "ref_head", lambda *_args: "a" * 40)
    monkeypatch.setattr(rollback, "remove_lane_start_worktree", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        rollback,
        "delete_lane_start_ref",
        lambda *_args, **_kwargs: pytest.fail("ref deletion must not run"),
    )
    monkeypatch.setattr(rollback, "state_database", lambda _repo: tmp_path / "state.sqlite")
    monkeypatch.setattr(rollback, "revoke_lease", lambda *_args, **_kwargs: {})
    context = rollback.LaneStartRollback(
        repo=tmp_path,
        target=target,
        branch="work/example",
        ownership=("work/example", "a" * 40, "a" * 40),
        completed=_completed(),
        run=_run_worktree_list(target),
        lease=_lease(),
        source_lease={},
        failure_gap="lane_start_failed",
    )

    report = rollback.rollback_lane_start(context)

    assert report["carrier_cleanup"] == {"worktree_removed": False, "ref_removed": False}
    assert report["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lane_start_worktree_cleanup_failed",
    ]


def test_rollback_reports_ref_drift_before_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    heads = iter(("a" * 40, "b" * 40))
    monkeypatch.setattr(rollback, "ref_head", lambda *_args: next(heads))
    monkeypatch.setattr(rollback, "remove_lane_start_worktree", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(rollback, "state_database", lambda _repo: tmp_path / "state.sqlite")
    monkeypatch.setattr(rollback, "revoke_lease", lambda *_args, **_kwargs: {})
    context = rollback.LaneStartRollback(
        repo=tmp_path,
        target=tmp_path / "lane",
        branch="work/example",
        ownership=("work/example", "a" * 40, "a" * 40),
        completed=_completed(),
        run=_run_worktree_list(tmp_path / "lane"),
        lease=_lease(),
        source_lease={},
        failure_gap="lane_start_failed",
    )

    report = rollback.rollback_lane_start(context)

    assert report["required_gaps"] == [
        "lane_creation_compensation_failed",
        "lane_start_ref_changed",
    ]


def test_rollback_translates_ref_delete_and_lease_revoke_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "lane"
    target.mkdir()
    heads = iter(("a" * 40, "a" * 40))
    monkeypatch.setattr(rollback, "ref_head", lambda *_args: next(heads))
    monkeypatch.setattr(rollback, "remove_lane_start_worktree", lambda *_args, **_kwargs: True)

    def fail_delete(*_args, **_kwargs):
        message = "git_effect_cas_rejected"
        raise ValueError(message)

    monkeypatch.setattr(rollback, "delete_lane_start_ref", fail_delete)
    monkeypatch.setattr(rollback, "state_database", lambda _repo: tmp_path / "state.sqlite")
    monkeypatch.setattr(rollback, "revoke_lease", lambda *_args, **_kwargs: {})
    context = rollback.LaneStartRollback(
        repo=tmp_path,
        target=target,
        branch="work/example",
        ownership=("work/example", "a" * 40, "a" * 40),
        completed=_completed(),
        run=_run_worktree_list(target),
        lease=_lease(),
        source_lease={},
        failure_gap="lane_start_failed",
    )

    report = rollback.rollback_lane_start(context)

    assert report["required_gaps"] == [
        "lane_creation_compensation_failed",
        "git_effect_cas_rejected",
    ]


def test_successful_rollback_revokes_exact_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "lane"
    target.mkdir()
    lease = _lease()
    heads = iter(("a" * 40, "a" * 40, ""))
    revoked: list[object] = []
    monkeypatch.setattr(rollback, "ref_head", lambda *_args: next(heads))
    monkeypatch.setattr(rollback, "remove_lane_start_worktree", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(rollback, "delete_lane_start_ref", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(rollback, "state_database", lambda _repo: tmp_path / "state.sqlite")
    monkeypatch.setattr(
        rollback,
        "revoke_lease",
        lambda _database, request: revoked.append(request) or {},
    )
    context = rollback.LaneStartRollback(
        repo=tmp_path,
        target=target,
        branch="work/example",
        ownership=("work/example", "a" * 40, "a" * 40),
        completed=_completed(""),
        run=_run_worktree_list(target),
        lease=lease,
        source_lease={},
        failure_gap="lane_start_postcondition_failed",
    )

    report = rollback.rollback_lane_start(context)

    assert report["carrier_cleanup"] == {"worktree_removed": True, "ref_removed": True}
    assert report["lease_state"] == "revoked"
    assert report["required_gaps"] == ["lane_start_postcondition_failed"]
    assert len(revoked) == 1


def test_rollback_preserves_child_process_diagnostics_after_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "lane"
    target.mkdir()
    completed = subprocess.CompletedProcess(("openspec", "new"), 7, "partial", "rejected")
    completed.parse_error = "unexpected eof"
    monkeypatch.setattr(rollback, "ref_head", lambda *_args: "")
    monkeypatch.setattr(rollback, "remove_lane_start_worktree", lambda *_args, **_kwargs: True)
    context = rollback.LaneStartRollback(
        repo=tmp_path,
        target=target,
        branch="work/example",
        ownership=("detached", "a" * 40, ""),
        completed=completed,
        run=_run_worktree_list(target, branch="detached"),
        lease=None,
        source_lease={},
        failure_gap="openspec_change_creation_failed",
    )

    report = rollback.rollback_lane_start(context)

    assert report["child_process"] == {
        "argv": ["openspec", "new"],
        "exit_code": 7,
        "stdout": "partial",
        "stderr": "rejected",
        "parse_error": "unexpected eof",
    }


def test_delete_ref_requires_lease_and_remove_worktree_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValueError, match=r"^lane_start_ref_cleanup_lease_missing$"):
        rollback.delete_lane_start_ref(tmp_path, "work/example", "a" * 40, None)

    def reject(*_args, **_kwargs):
        message = "worktree_changed"
        raise ValueError(message)

    monkeypatch.setattr(rollback, "remove_worktree", reject)
    assert not rollback.remove_lane_start_worktree(
        tmp_path,
        target=tmp_path / "lane",
        branch="work/example",
        head="a" * 40,
        run=lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
