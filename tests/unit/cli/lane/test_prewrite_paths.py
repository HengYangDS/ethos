from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.store import state
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_lane_prewrite_accepts_multiple_keyword_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")

    payload = run_ethos(
        "lane",
        "prewrite",
        "--paths",
        "README.md",
        ".gitignore",
        "--editor-root",
        worktree.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is True
    assert payload["summary"]["path_count"] == 2
    assert [entry["relative_path"] for entry in payload["data"]["paths"]] == [
        "README.md",
        ".gitignore",
    ]


def test_lane_prewrite_blocks_whitespace_joined_path_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        owner="agent-a",
        payload={"path": worktree.as_posix(), "branch": "work/feature"},
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent-a")

    payload = run_ethos_blocked(
        "lane",
        "prewrite",
        "README.md .gitignore",
        "--editor-root",
        worktree.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is False
    assert payload["required_gaps"] == ["prewrite_path_invalid_whitespace"]
    assert payload["data"]["paths"][0] == {
        "path": "README.md .gitignore",
        "relative_path": "",
        "ignored": False,
        "tracked_candidate": False,
        "allowed": False,
        "reason": "path_invalid_whitespace",
    }
