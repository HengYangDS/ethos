"""Tracked path observation without Git path quoting."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git_adapter
from ethos.adapters.repo.git import tracked_paths
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_tracked_paths_keep_exact_names(tmp_path: Path) -> None:
    """Non-ASCII and quoted names keep their bytes instead of Git's quoted form."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "docs").mkdir()
    (repo / 'docs/über "quoted".md').write_text("# Notes\n", encoding="utf-8")
    commit_fixture(repo, "record notes")
    paths = tracked_paths(repo)
    assert 'docs/über "quoted".md' in paths
    assert "AGENTS.md" in paths


def test_tracked_paths_are_empty_when_git_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed listing observes no tracked paths rather than a partial set."""
    refused = subprocess.CompletedProcess(("git",), 128, b"", b"fatal: not a git repository")
    monkeypatch.setattr(git_adapter, "run_git", lambda *_args, **_options: refused)
    assert tracked_paths(tmp_path) == ()
