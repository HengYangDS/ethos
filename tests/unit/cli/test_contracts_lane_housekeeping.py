from __future__ import annotations

from pathlib import Path  # noqa: TC003

from ethos.repository.registry.docs.commands import known_ethos_command
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_repo_with_candidate
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked


def test_lane_housekeeping_exposes_dry_run_and_authorized_apply(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    detached = tmp_path / "detached-probe"
    git(repo, "worktree", "add", "--detach", detached.as_posix(), "dev")

    planned = run_ethos(
        "lane",
        "housekeeping",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )
    assert planned["command"] == "lane housekeeping"
    assert planned["ok"] is True
    assert planned["state"] == "planned"
    assert planned["summary"]["removable_count"] == 1

    blocked = run_ethos_blocked(
        "lane",
        "housekeeping",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )
    assert blocked["required_gaps"] == ["authorization_required"]
    assert detached.exists()

    applied = run_ethos(
        "lane",
        "housekeeping",
        "--authorize",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )
    assert applied["state"] == "cleaned"
    assert applied["summary"]["removed_count"] == 1
    assert not detached.exists()


def test_lane_housekeeping_is_a_declared_repository_command() -> None:
    assert known_ethos_command("ethos lane housekeeping --json") is True
