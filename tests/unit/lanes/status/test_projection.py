"""Work Lane status projects only fresh topology and the minimal Lease relation."""

from __future__ import annotations

import shlex
import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.repo.status.workspace as workspace
from ethos.adapters.repo.coordination import FOREIGN_WORK_LANE_NEXT_ACTION
from ethos.adapters.repo.status.bindings import landing_readiness
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.governed_repository import prepared_work_lane

if TYPE_CHECKING:
    from pathlib import Path


def test_foreign_lane_projects_lease_actions_and_non_authorizing_lock(tmp_path: Path) -> None:
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
    git(repo, "worktree", "lock", "--reason", "handoff-in-progress", foreign.as_posix())
    locked = workspace_status(repo)["foreign_work_lanes"][0]
    assert locked["git_lock"] == {
        "locked": True,
        "reason": "handoff-in-progress",
        "mints_authority": False,
    }
    assert locked["handoff_required"] is True


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

    assert "next_action" not in status
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


def test_workspace_projection_distinguishes_candidate_and_non_git_failures(
    tmp_path: Path, monkeypatch
) -> None:
    for candidate, gap in (
        ({"branch": "candidate/dev", "exists": False}, "candidate_branch_missing"),
        ({"branch": "candidate/dev", "exists": True}, "candidate_worktree_missing"),
    ):
        report = landing_readiness(
            tmp_path,
            head="",
            branch="work/change",
            role="work_lane",
            candidate=candidate,
            accepted={},
        )
        assert report["required_gaps"] == [gap]
    monkeypatch.setattr(
        workspace,
        "git_stdout_checked",
        lambda *_args: (_ for _ in ()).throw(subprocess.CalledProcessError(128, "git")),
    )
    selected, observed = object(), []
    monkeypatch.setattr(
        workspace,
        "runtime_binding",
        lambda _root, **observations: observed.append(observations) or {},
    )
    status = workspace.workspace_status(tmp_path, selected_runtime=selected)
    assert (status["branch"], status["landing_readiness"]["state"], observed) == (
        "untracked",
        "not_work_lane",
        [{"selected_runtime": selected, "hook_binding": None}],
    )
    assert "git_repository_missing" in status["required_gaps"]


def test_public_lane_continuation_advances_from_integration_to_retirement(
    tmp_path: Path, monkeypatch
) -> None:
    """A lane moves through each Git boundary without losing uncommitted work."""
    repo, candidate, worktree = prepared_work_lane(tmp_path)
    branch = git(worktree, "branch", "--show-current")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    assert run_ethos("lane", "status", "--json", cwd=worktree)["next_action"] == (
        "ethos land --json"
    )

    git(candidate, "merge", "--ff-only", branch)
    staged = run_ethos("lane", "status", "--json", cwd=worktree)
    assert staged["data"]["landing_readiness"]["state"] == "candidate_integrated"
    assert staged["next_action"] == f"ethos status --root {repo} --json"
    assert staged["data"]["stage_gates"]["integration_allowed"] is False
    assert run_ethos("status", "--json", cwd=worktree)["next_action"] == staged["next_action"]
    assert (
        "--closeout" in run_ethos("status", "--root", str(repo), "--json", cwd=repo)["next_action"]
    )

    git(repo, "merge", "--ff-only", branch)
    accepted = run_ethos("lane", "status", "--json", cwd=worktree)
    assert accepted["data"]["landing_readiness"]["state"] == "accepted_integrated"
    assert accepted["next_action"] == (
        f"ethos lane retire landed --branch {branch} --root {repo} --json"
    )
    assert accepted["data"]["stage_gates"]["integration_allowed"] is False
    assert run_ethos("status", "--json", cwd=worktree)["next_action"] == accepted["next_action"]

    git(repo, "worktree", "remove", candidate.as_posix())
    git(repo, "branch", "-D", "candidate/dev")
    without_candidate = run_ethos("lane", "status", "--json", cwd=worktree)
    assert (without_candidate["verdict"], without_candidate["next_action"]) == (
        "pass",
        accepted["next_action"],
    )
    preview = run_ethos(*shlex.split(without_candidate["next_action"])[1:], cwd=repo)
    assert (preview["verdict"], preview["required_gaps"]) == ("pass", [])

    (worktree / "uncommitted.txt").write_text("new work\n", encoding="utf-8")
    dirty = run_ethos("lane", "status", "--json", cwd=worktree)
    assert dirty["data"]["dirty"] is True
    assert dirty["next_action"] == "ethos lane prewrite <path>"
