"""Tests for source build identity observation boundaries."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.source as source
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path


def _repository(path: Path, content: str) -> Path:
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch=dev")
    (path / "tracked.txt").write_text(content + "\n")
    commit_fixture(path, content)
    return path


def test_source_identity_ignores_an_inherited_foreign_git_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, foreign = (
        _repository(tmp_path / "source", "source"),
        _repository(tmp_path / "foreign", "foreign"),
    )
    expected = (git(repository, "rev-parse", "HEAD"), git(repository, "rev-parse", "HEAD^{tree}"))
    monkeypatch.setenv("GIT_DIR", git(foreign, "rev-parse", "--absolute-git-dir"))
    assert source.source_git_identity(repository) == expected


def test_source_identity_overlay_and_failure_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path / "source", "base")
    for path, content in (
        ("tracked.txt", "modified\n"),
        ("new-source.txt", "new source\n"),
        (".gitignore", "ignored.txt\n"),
        ("ignored.txt", "residue\n"),
    ):
        (repository / path).write_text(content)
    commit, tree = source.source_git_identity(repository)
    assert commit == git(repository, "rev-parse", "HEAD")
    assert git(repository, "show", f"{tree}:tracked.txt") == "modified"
    assert git(repository, "show", f"{tree}:new-source.txt") == "new source"
    assert git(repository, "ls-tree", "--name-only", tree).splitlines() == [
        ".gitignore",
        "new-source.txt",
        "tracked.txt",
    ]
    with pytest.raises(ValueError, match="build_channel_invalid"):
        source.source_build_identity(repository, channel="invalid")
    packaged = tmp_path / "package"
    packaged.mkdir()
    with pytest.raises(ValueError, match="package_build_identity_missing"):
        source.build_input_identity(packaged)
    with monkeypatch.context() as git_failure:
        git_failure.setattr(
            source, "run_git", lambda *_a, **_k: subprocess.CompletedProcess((), 1, "", "failed")
        )
        with pytest.raises(ValueError, match="build_source_identity_unavailable"):
            source.source_git_identity(packaged)
    invalid = _repository(tmp_path / "invalid-policy", "source")
    (invalid / ".ethos").mkdir()
    (invalid / ".ethos/workspace.toml").write_bytes(b"\xff")
    with pytest.raises(ValueError, match="accepted_build_policy_unavailable"):
        source.source_build_identity(invalid, channel="accepted")
