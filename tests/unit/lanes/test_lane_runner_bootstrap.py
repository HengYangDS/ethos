from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.mutation.lanes import start_work_lane
from ethos.surface.cli.lane.core import _start_next_actions
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_start_work_lane_returns_source_bound_runner_bootstrap(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "candidate")
    lane = tmp_path / "lane"

    report = start_work_lane(
        root=repo,
        name="runtime-bootstrap",
        path=lane,
        holder_ref="agent:test:case:runner",
        apply=True,
    )

    assert report["ok"] is True
    assert report["runner_bootstrap"] == {
        "command": "tools/ci/scripts/run-ethos-lane.sh",
        "project_environment": "build/runtime/venv",
        "uv_cache": "build/runtime/tool-cache/uv",
        "next_action": (
            f"cd {lane.resolve().as_posix()} && tools/ci/scripts/run-ethos-lane.sh status --json"
        ),
    }


def test_start_next_actions_are_empty_when_start_is_blocked() -> None:
    assert _start_next_actions({"ok": False}) == ()


def test_start_next_actions_fall_back_to_prewrite_without_bootstrap() -> None:
    assert _start_next_actions({"ok": True}) == ("ethos lane prewrite <path>",)
