from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.store import state
from ethos.surface.cli.lane import _lane_status_next_actions

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.ethos_cli_runner import run_ethos


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def test_lane_status_next_action_does_not_suggest_prewrite_from_accepted_root(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "candidate/dev",
        (tmp_path / "repo-candidate-dev").as_posix(),
        "dev",
    )
    foreign = tmp_path / "repo-work-foreign"
    git(repo, "worktree", "add", "-b", "work/foreign", foreign.as_posix(), "dev")

    payload = run_ethos("lane", "status", "--root", repo.as_posix(), "--json", cwd=repo)

    assert payload["data"]["role"] == "accepted_root"
    assert payload["data"]["foreign_work_lanes"][0]["current_actor_capability"] == "observe"
    assert "ethos lane prewrite <path>" not in payload["next_actions"]
    assert payload["next_actions"] == ["ethos orient --json", "ethos lane status --json"]


def test_lane_status_next_action_keeps_prewrite_for_current_work_lane(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(
        repo,
        "worktree",
        "add",
        "-b",
        "candidate/dev",
        (tmp_path / "repo-candidate-dev").as_posix(),
        "dev",
    )
    worktree = tmp_path / "repo-work-owned"
    git(repo, "worktree", "add", "-b", "work/owned", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/owned",
        owner="agent-a",
        ttl_seconds=3600,
    )

    payload = run_ethos("lane", "status", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["data"]["role"] == "work_lane"
    assert "ethos lane prewrite <path>" in payload["next_actions"]
    assert "ethos land --json" in payload["next_actions"]


def test_lane_status_next_action_routes_blocking_gaps_to_orient() -> None:
    payload = {
        "role": "accepted_root",
        "required_gaps": ["work_lane_missing_lease"],
    }

    assert _lane_status_next_actions(payload) == ("ethos orient --json",)


def test_lane_status_next_action_suggests_lane_start_for_clean_root() -> None:
    payload = {
        "role": "accepted_root",
        "required_gaps": [],
        "coordination": {"advisory_gaps": []},
    }

    assert _lane_status_next_actions(payload) == (
        "ethos lane start <name> --path <path> --owner <owner> --apply --json",
    )
