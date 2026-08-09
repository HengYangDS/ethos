# ruff: noqa: SLF001
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.mutation.lane_lifecycle.work_lane_refresh as refresh
from ethos.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    from pathlib import Path


HEAD = "a" * 40
CANDIDATE = "b" * 40
BRANCH = "work/feature"


def _completed(*, returncode: int = 0, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _status(*, branch: str = BRANCH) -> dict[str, Any]:
    return {
        "branch": branch,
        "role": ROLE_WORK_LANE,
        "dirty": False,
        "candidate": {
            "exists": True,
            "worktree_exists": True,
            "head": CANDIDATE,
            "worktree_path": "/candidate",
        },
    }


def _common(monkeypatch: pytest.MonkeyPatch, *, branch: str = BRANCH) -> None:
    monkeypatch.setattr(
        refresh,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(candidate_branch="candidate/dev"),
    )
    monkeypatch.setattr(refresh, "workspace_status", lambda _root: _status(branch=branch))
    monkeypatch.setattr(refresh, "changed_paths", lambda _path: ())
    monkeypatch.setattr(
        refresh,
        "run_git",
        lambda _root, *args, **_kwargs: _completed(
            stdout=(HEAD if args[-2:] == ("rev-parse", "HEAD") else CANDIDATE) + "\n"
        ),
    )


def test_refresh_public_reader_distinguishes_current_and_ready(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(refresh, "equivalent_commit_identity", lambda *_a: False)
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_a: True)
    current = refresh.refresh_work_lane_base(root=tmp_path)
    assert current["state"] == "base_current"

    monkeypatch.setattr(refresh, "is_ancestor", lambda *_a: False)
    ready = refresh.refresh_work_lane_base(root=tmp_path)
    assert ready["state"] == "ready_to_refresh_base"


def test_refresh_rejects_snapshot_drift_before_rebase(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_a: False)
    monkeypatch.setattr(refresh, "equivalent_commit_identity", lambda *_a: False)
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: "drift")
    report = refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head=HEAD
    )
    assert report["required_gaps"] == ["refresh_base_snapshot_stale:work_lane"]


def test_refresh_conflict_reports_failed_restore(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_a: False)
    monkeypatch.setattr(refresh, "equivalent_commit_identity", lambda *_a: False)
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: HEAD)

    def run_git(_root: Path, *args: str, **_kwargs: object) -> SimpleNamespace:
        if "rebase" in args and "--abort" not in args:
            return _completed(returncode=1, stderr="CONFLICT (content): conflict")
        return _completed(stdout=(HEAD if args[-2:] == ("rev-parse", "HEAD") else CANDIDATE) + "\n")

    monkeypatch.setattr(refresh, "run_git", run_git)
    monkeypatch.setattr(
        refresh,
        "_attach_work_lane",
        lambda *_a: (_ for _ in ()).throw(ValueError("attachment stale")),
    )
    report = refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head=HEAD
    )
    assert report["required_gaps"] == [
        "refresh_base_failed",
        "refresh_base_worktree_restore_failed",
    ]
    assert "CONFLICT" in report["stderr"]


def test_refresh_rejects_rebase_postcondition_and_restores_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _common(monkeypatch)
    monkeypatch.setattr(refresh, "equivalent_commit_identity", lambda *_a: False)
    ancestry = iter((False, False))
    monkeypatch.setattr(refresh, "is_ancestor", lambda *_a: next(ancestry))
    heads = iter((HEAD, "rebased", "restored"))
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: next(heads))
    attached: list[tuple[str, str]] = []
    monkeypatch.setattr(
        refresh,
        "_attach_work_lane",
        lambda _root, branch, head: attached.append((branch, head)),
    )
    report = refresh.refresh_work_lane_base(
        root=tmp_path, apply=True, authorized=True, expect_head=HEAD
    )
    assert report["required_gaps"] == ["refresh_base_postcondition_failed"]
    assert attached == [(BRANCH, HEAD)]


@pytest.mark.parametrize("case", ["ref-drift", "effect-fails", "recovered"])
def test_refresh_recovery_replays_only_exact_persisted_ref_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    ref_matches = case != "ref-drift"
    effect_fails = case == "effect-fails"
    monkeypatch.setattr(refresh, "ref_head", lambda *_a: HEAD if ref_matches else "other")
    monkeypatch.setattr(refresh, "_actor", lambda: "agent:test")
    sentinel = object()
    monkeypatch.setattr(
        refresh,
        "execute_git_effect",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("stale")) if effect_fails else sentinel,
    )
    result = refresh._recover_applied_refresh(
        tmp_path, SimpleNamespace(), lambda: None, BRANCH, HEAD
    )
    assert (result is sentinel) is (case == "recovered")


def test_refresh_restore_and_attachment_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(refresh, "current_tracked_head", lambda _root: HEAD)
    monkeypatch.setattr(
        refresh,
        "run_git",
        lambda *_a, **_k: _completed(stdout=BRANCH + "\n"),
    )
    assert refresh._restore_pre_refresh_checkout(tmp_path, BRANCH, HEAD) == []

    monkeypatch.setattr(
        refresh,
        "attach_worktree",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("branch occupied")),
    )
    with pytest.raises(ValueError, match="work-lane branch attachment stale:branch occupied"):
        refresh._attach_work_lane(tmp_path, BRANCH, HEAD)
