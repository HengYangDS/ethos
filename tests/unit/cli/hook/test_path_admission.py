from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.store.state.lease.core as state
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_hook_admit_accepts_multiple_keyword_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        holder_ref="agent:test:case:agent-a",
        payload={
            "path": worktree.as_posix(),
            "branch": "work/feature",
            "expected_head": git(worktree, "rev-parse", "HEAD"),
        },
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    payload = run_ethos(
        "hook",
        "admit",
        "pre-tool",
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
    assert payload["data"]["admission"]["ok"] is True
    assert [entry["relative_path"] for entry in payload["data"]["admission"]["paths"]] == [
        "README.md",
        ".gitignore",
    ]


def test_hook_admit_blocks_control_character_path_token_before_root_join(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_repo(tmp_path / "repo")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/feature",
        holder_ref="agent:test:case:agent-a",
        payload={
            "path": worktree.as_posix(),
            "branch": "work/feature",
            "expected_head": git(worktree, "rev-parse", "HEAD"),
        },
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    payload = run_ethos_blocked(
        "hook",
        "admit",
        "pre-tool",
        "README.md\nAGENTS.md",
        "--root",
        worktree.as_posix(),
        "--editor-root",
        worktree.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=worktree,
    )

    assert payload["ok"] is False
    assert payload["data"]["decision"] == {
        "action": "block",
        "reason": "prewrite_path_invalid_control_character",
    }
    assert payload["data"]["target_paths"] == ["README.md\nAGENTS.md"]
    assert payload["data"]["admission"]["paths"][0] == {
        "path": "README.md\nAGENTS.md",
        "relative_path": "",
        "ignored": False,
        "tracked_candidate": False,
        "allowed": False,
        "reason": "path_invalid_control_character",
    }
    assert "prewrite_path_invalid_control_character" in payload["required_gaps"]
