"""Work Lane status projects only fresh topology and the minimal Lease relation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.coordination import FOREIGN_WORK_LANE_NEXT_ACTION
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path


def test_foreign_lane_projects_minimal_lease_and_observation_only_actions(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    foreign = create_change_source_lane(
        repo,
        tmp_path / "repo-work-foreign",
        branch="work/foreign",
        holder_ref="agent:test:case:foreign",
    )

    status = workspace_status(repo)
    lane = next(item for item in status["foreign_work_lanes"] if item["branch"] == "work/foreign")

    assert lane["lease"] == {
        "generation": 1,
        "holder_ref": "agent:test:case:foreign",
        "expires_at": lane["lease"]["expires_at"],
        "mints_authority": False,
    }
    assert lane["next_action"] == FOREIGN_WORK_LANE_NEXT_ACTION
    assert lane["action_preview"] == {
        "candidate_actions": ["observe"],
        "blocked_actions": ["write", "land", "retire"],
        "why": ["foreign_lane_requires_handoff_or_exact_authorized_lease_takeover"],
        "mints_authority": False,
        "recheck_required": True,
    }
    assert foreign.exists()


def test_worktree_lock_is_observed_but_never_mints_authority(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    foreign = create_change_source_lane(
        repo,
        tmp_path / "repo-work-locked",
        branch="work/locked",
        holder_ref="agent:test:case:foreign",
    )
    git(repo, "worktree", "lock", "--reason", "handoff-in-progress", foreign.as_posix())

    lane = next(
        item
        for item in workspace_status(repo)["foreign_work_lanes"]
        if item["branch"] == "work/locked"
    )

    assert lane["git_lock"] == {
        "locked": True,
        "reason": "handoff-in-progress",
        "mints_authority": False,
    }
    assert lane["handoff_required"] is True


def test_unbound_ref_projects_recovery_facts_without_commitment_mirrors(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    path = create_change_source_lane(
        repo,
        tmp_path / "repo-work-unbound",
        branch="work/unbound",
        holder_ref="agent:test:case:unbound",
    )
    git(repo, "worktree", "remove", path.as_posix())

    status = workspace_status(repo, include_foreign_path_scope=False)
    unbound = status["unbound_work_lane_refs"]

    assert len(unbound) == 1
    assert set(unbound[0]) == {
        "branch",
        "head",
        "generation",
        "holder_ref",
        "expires_at",
        "lease_state",
        "relation_to_accepted",
        "next_action",
    }
    assert validate_schema_instance("workspace-status.schema.json", status, root=repo) == {
        "verdict": "pass",
        "required_gaps": [],
    }
