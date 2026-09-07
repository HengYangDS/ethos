from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import exact_lease
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime

if TYPE_CHECKING:
    from pathlib import Path


def test_superseded_retirement_exposes_exact_missing_worktree_recovery_path() -> None:
    completed = run_ethos_raw("lane", "retire", "superseded", "--help")

    assert completed.returncode == 0, completed.stderr
    assert "--path" in completed.stdout


def test_retirement_help_exposes_abandonment_and_one_recovery_route() -> None:
    completed = run_ethos_raw("lane", "retire", "--help")

    assert completed.returncode == 0, completed.stderr
    assert "abandon" in completed.stdout
    assert "recover" in completed.stdout


@pytest.mark.parametrize("historical_policy", [False, True])
def test_landed_retires_clean_absorbed_topic_worktree(
    tmp_path: Path, *, historical_policy: bool
) -> None:
    """Authoring prefixes do not prevent exact deletion-only accepted absorption."""
    repo = init_git_repo(tmp_path / "repo")
    historical = git(repo, "rev-parse", "HEAD")
    adopt_and_commit(repo)
    accepted = git(repo, "rev-parse", "HEAD")
    source = historical if historical_policy else accepted
    branch = "topic/absorbed"
    worktree = tmp_path / "absorbed"
    git(repo, "worktree", "add", "-b", branch, worktree.as_posix(), source)
    install_fixture_hook_runtime(repo)
    args = (
        "lane",
        "retire",
        "landed",
        "--branch",
        branch,
        "--expect-head",
        source,
        "--root",
        repo.as_posix(),
        "--authorize",
        "--json",
    )

    planned = run_ethos(*args, cwd=repo)
    assert planned["required_gaps"] == []
    assert planned["verdict"] == "pass"
    applied = run_ethos(*args, "--apply", cwd=repo)

    assert applied["verdict"] == "pass"
    assert not worktree.exists()
    assert git(repo, "branch", "--list", branch) == ""
    assert git(repo, "rev-parse", "dev") == accepted
    assert observe_lease(state_database(repo), branch).state == "missing"


@pytest.mark.parametrize("boundary", ["dirty", "foreign_lease", "stale_head", "locked"])
def test_landed_topic_retirement_preserves_unadmitted_resources(
    tmp_path: Path, boundary: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    source = git(repo, "rev-parse", "HEAD")
    branch = "topic/absorbed"
    worktree = tmp_path / "absorbed"
    git(repo, "worktree", "add", "-b", branch, worktree.as_posix(), source)
    if boundary == "dirty":
        (worktree / "unique.txt").write_text("unabsorbed work\n", encoding="utf-8")
    elif boundary == "foreign_lease":
        acquire_lease(
            state_database(repo),
            lease=exact_lease(branch=branch, holder_ref="agent:test:case:other"),
        )
    elif boundary == "locked":
        git(repo, "worktree", "lock", worktree.as_posix())
    install_fixture_hook_runtime(repo)

    blocked = run_ethos_blocked(
        "lane",
        "retire",
        "landed",
        "--branch",
        branch,
        "--expect-head",
        "0" * 40 if boundary == "stale_head" else source,
        "--root",
        repo.as_posix(),
        "--authorize",
        "--apply",
        "--json",
        cwd=repo,
    )

    expected = {
        "dirty": "work_lane_dirty",
        "foreign_lease": "foreign_work_lane_retire_authority_required",
        "stale_head": "expect_head_mismatch",
    }
    if boundary in expected:
        assert expected[boundary] in blocked["required_gaps"]
    assert worktree.is_dir()
    assert git(repo, "rev-parse", branch) == source
    if boundary == "dirty":
        assert (worktree / "unique.txt").read_text(encoding="utf-8") == "unabsorbed work\n"
    if boundary == "foreign_lease":
        assert observe_lease(state_database(repo), branch).state == "valid"
