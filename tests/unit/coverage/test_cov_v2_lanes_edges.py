"""Coverage-closure v2: mutation/lanes helper branches (100% no-exemption)."""

from __future__ import annotations

from pathlib import Path

from ethos.adapters.mutation import lanes
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE


def test_status_work_lane_none_when_worktrees_not_list() -> None:
    # A status without a worktrees list yields no lane (line 303).
    assert lanes._status_work_lane({"worktrees": "nope"}, "work/x") is None


def test_status_work_lane_skips_non_dict_and_finds_match() -> None:
    # Non-dict rows are skipped; a matching work-lane row is returned (lines 305-308).
    status = {
        "worktrees": [
            "junk",
            {"branch": "work/x", "role": ROLE_WORK_LANE, "path": "/workspace/x"},
        ]
    }
    lane = lanes._status_work_lane(status, "work/x")
    assert lane is not None
    assert lane["branch"] == "work/x"


def test_status_work_lane_none_when_no_match() -> None:
    status = {"worktrees": [{"branch": "work/y", "role": ROLE_WORK_LANE}]}
    assert lanes._status_work_lane(status, "work/x") is None


def test_state_root_returns_accepted_root_path(tmp_path: Path) -> None:
    # An accepted-root worktree with a path supplies the state root (lines 318-319).
    status = {
        "worktrees": [
            "junk",
            {"role": ROLE_ACCEPTED_ROOT, "path": "/workspace/accepted"},
        ]
    }
    assert lanes._state_root(status, tmp_path) == Path("/workspace/accepted")


def test_state_root_falls_back_when_no_accepted_root(tmp_path: Path) -> None:
    # No accepted-root row (or non-list worktrees) falls back to the given path
    # (line 320 and the non-list guard).
    assert lanes._state_root({"worktrees": "x"}, tmp_path) == tmp_path
    assert lanes._state_root({"worktrees": [{"role": ROLE_WORK_LANE}]}, tmp_path) == tmp_path
