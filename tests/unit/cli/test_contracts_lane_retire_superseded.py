from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.store.state.lease.lifecycle.core as state

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked


def absorb_obsolete_delta_in_accepted(repo: Path) -> str:
    (repo / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    git(repo, "add", "obsolete.txt")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "absorb obsolete lane delta",
    )
    return git(repo, "rev-parse", "dev")


def test_lane_retire_superseded_apply_removes_absorbed_linked_lane(
    monkeypatch,
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
    worktree = tmp_path / "repo-work-superseded"
    git(repo, "worktree", "add", "-b", "work/superseded", worktree.as_posix(), "dev")
    (worktree / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    git(worktree, "add", "obsolete.txt")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "obsolete lane delta",
    )
    worktree_head = git(worktree, "rev-parse", "HEAD")
    accepted_head = absorb_obsolete_delta_in_accepted(repo)
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    payload = run_ethos(
        "lane",
        "retire",
        "superseded",
        "--branch",
        "work/superseded",
        "--expect-head",
        worktree_head,
        "--absorbed-by",
        accepted_head,
        "--reason",
        "accepted root already carries the semantic fix",
        "--authorize",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire superseded"
    assert payload["ok"] is True
    assert payload["state"] == "retired_superseded"
    assert payload["summary"] == {
        "branch": "work/superseded",
        "head": worktree_head,
        "absorbed_by": accepted_head,
        "retire_ready": True,
    }
    assert payload["data"]["mutation"]["expect_head"] == worktree_head
    assert not worktree.exists()


def test_lane_retire_superseded_blocks_unabsorbed_linked_lane(
    monkeypatch,
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
    worktree = tmp_path / "repo-work-superseded"
    git(repo, "worktree", "add", "-b", "work/superseded", worktree.as_posix(), "dev")
    (worktree / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    git(worktree, "add", "obsolete.txt")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "obsolete lane delta",
    )
    worktree_head = git(worktree, "rev-parse", "HEAD")
    accepted_head = git(repo, "rev-parse", "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    payload = run_ethos_blocked(
        "lane",
        "retire",
        "superseded",
        "--branch",
        "work/superseded",
        "--expect-head",
        worktree_head,
        "--absorbed-by",
        accepted_head,
        "--reason",
        "accepted root already carries the semantic fix",
        "--authorize",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire superseded"
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["superseded_lane_not_absorbed_by_accepted"]
    assert worktree.exists()
    assert git(repo, "rev-parse", "--verify", "work/superseded") == worktree_head


def test_lane_retire_superseded_blocks_without_current_absorption_head(
    monkeypatch,
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
    worktree = tmp_path / "repo-work-superseded"
    git(repo, "worktree", "add", "-b", "work/superseded", worktree.as_posix(), "dev")
    (worktree / "obsolete.txt").write_text("obsolete\n", encoding="utf-8")
    git(worktree, "add", "obsolete.txt")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "obsolete lane delta",
    )
    worktree_head = git(worktree, "rev-parse", "HEAD")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/superseded",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    payload = run_ethos_blocked(
        "lane",
        "retire",
        "superseded",
        "--branch",
        "work/superseded",
        "--expect-head",
        worktree_head,
        "--absorbed-by",
        "old-head",
        "--reason",
        "accepted root already carries the semantic fix",
        "--authorize",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire superseded"
    assert payload["ok"] is False
    assert payload["required_gaps"] == ["absorbed_by_not_current_accepted_head"]
    assert worktree.exists()
