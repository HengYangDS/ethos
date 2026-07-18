from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.repo.status.core as status_core
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.status.core import workspace_status
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_workspace_status_bounded_reader_defers_foreign_path_scopes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    foreign = tmp_path / "repo-work-foreign"
    start_work_lane(
        root=repo,
        name="foreign",
        path=foreign,
        holder_ref="agent:test:case:agent-foreign",
        apply=True,
    )
    calls: list[tuple[object, ...]] = []

    def _path_scope_not_requested(*args, **_kwargs):
        calls.append(args)
        return (), "empty"

    monkeypatch.setattr(status_core, "branch_path_scope", _path_scope_not_requested)

    status = workspace_status(repo, include_foreign_path_scope=False)

    lane = status["foreign_work_lanes"][0]
    assert lane["branch"] == "work/foreign"
    assert lane["path_scope"] == []
    assert lane["scope_state"] == "deferred"
    assert lane["coordination_state"] == "advisory"
    assert status["coordination"]["foreign_work_lane_count"] == 1
    assert calls == []
    assert validate_schema_instance("workspace-status.schema.json", status)["ok"] is True
