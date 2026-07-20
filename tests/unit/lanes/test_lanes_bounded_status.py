from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.repo.status.core as status_core
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.status.core import workspace_status
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import assert_no_ui_projection
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_workspace_status_reports_exact_foreign_work_lane_aggregates(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    add_candidate_worktree(repo, candidate)
    foreign = tmp_path / "repo-work-foreign"
    git(repo, "worktree", "add", "-b", "work/foreign", foreign.as_posix(), "dev")

    status = workspace_status(repo)

    assert status["role"] == "accepted_root"
    lane = status["foreign_work_lanes"][0]
    assert lane["branch"] == "work/foreign"
    assert lane["head"] == git(repo, "rev-parse", "dev")
    assert lane["dirty"] is False
    assert lane["scope_state"] == "empty"
    assert status["required_gaps"] == []
    assert status["coordination_gaps"] == [
        "foreign_work_lane_present",
        "work_lane_missing_lease:work/foreign",
    ]
    coordination = status["coordination"]
    assert coordination["detail_state"] == "exact"
    assert coordination["foreign_work_lane_count"] == 1
    assert coordination["missing_lease_count"] == 1
    assert coordination["dirty_foreign_work_lane_count"] == 0
    assert coordination["overlap_count"] == 0
    assert coordination["unknown_scope_count"] == 0
    assert coordination["closeout_residue_count"] == 0
    assert coordination["dirty_closeout_residue_count"] == 0
    assert status["closeout_support"]["target_path"] == candidate.as_posix()
    assert status["closeout_support"]["required_gaps"] == ["protected_root_mutation"]
    assert_no_ui_projection(status)


def test_workspace_status_empty_inventory_preserves_explicit_detail_mode(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")

    full = workspace_status(repo)
    full_coordination = full["coordination"]

    assert full["foreign_work_lanes"] == []
    assert full_coordination["detail_state"] == "exact"
    assert full_coordination["dirty_foreign_work_lane_count"] == 0
    assert full_coordination["overlap_count"] == 0
    assert full_coordination["unknown_scope_count"] == 0
    assert full_coordination["closeout_residue_count"] == 0
    assert full_coordination["dirty_closeout_residue_count"] == 0
    assert validate_schema_instance("workspace-status.schema.json", full)["ok"] is True

    bounded = workspace_status(repo, include_foreign_path_scope=False)
    bounded_coordination = bounded["coordination"]

    assert bounded["foreign_work_lanes"] == []
    assert bounded_coordination["foreign_work_lane_count"] == 0
    assert bounded_coordination["missing_lease_count"] == 0
    assert validate_schema_instance("workspace-status.schema.json", bounded)["ok"] is True
    assert bounded_coordination["detail_state"] == "deferred"
    assert bounded_coordination["dirty_foreign_work_lane_count"] is None
    assert bounded_coordination["overlap_count"] is None
    assert bounded_coordination["unknown_scope_count"] is None
    assert bounded_coordination["closeout_residue_count"] is None
    assert bounded_coordination["dirty_closeout_residue_count"] is None


def test_workspace_status_non_git_empty_inventory_preserves_explicit_detail_mode(
    tmp_path: Path,
) -> None:
    root = tmp_path / "non-git"
    root.mkdir()

    full = workspace_status(root)
    full_coordination = full["coordination"]

    assert full["foreign_work_lanes"] == []
    assert full_coordination["detail_state"] == "exact"
    assert full_coordination["dirty_foreign_work_lane_count"] == 0
    assert full_coordination["overlap_count"] == 0
    assert full_coordination["unknown_scope_count"] == 0
    assert full_coordination["closeout_residue_count"] == 0
    assert full_coordination["dirty_closeout_residue_count"] == 0
    assert validate_schema_instance("workspace-status.schema.json", full)["ok"] is True

    bounded = workspace_status(root, include_foreign_path_scope=False)
    bounded_coordination = bounded["coordination"]

    assert bounded["foreign_work_lanes"] == []
    assert bounded_coordination["detail_state"] == "deferred"
    assert bounded_coordination["dirty_foreign_work_lane_count"] is None
    assert bounded_coordination["overlap_count"] is None
    assert bounded_coordination["unknown_scope_count"] is None
    assert bounded_coordination["closeout_residue_count"] is None
    assert bounded_coordination["dirty_closeout_residue_count"] is None
    assert validate_schema_instance("workspace-status.schema.json", bounded)["ok"] is True


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
    assert status["coordination"]["detail_state"] == "deferred"
    assert status["coordination"]["overlap_count"] is None
    assert status["coordination"]["unknown_scope_count"] is None
    assert status["coordination"]["closeout_residue_count"] is None
    assert status["coordination"]["dirty_closeout_residue_count"] is None
    assert calls == []
    assert validate_schema_instance("workspace-status.schema.json", status)["ok"] is True
