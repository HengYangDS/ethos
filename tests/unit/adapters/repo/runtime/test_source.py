"""Tests for source build identity observation boundaries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.runtime.source import source_git_identity
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_source_identity_ignores_an_inherited_foreign_git_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _repository(tmp_path / "source", "source")
    foreign = _repository(tmp_path / "foreign", "foreign")
    expected = (git(source, "rev-parse", "HEAD"), git(source, "rev-parse", "HEAD^{tree}"))
    monkeypatch.setenv("GIT_DIR", git(foreign, "rev-parse", "--absolute-git-dir"))

    assert source_git_identity(source) == expected


def test_source_identity_includes_nonignored_overlay_but_excludes_ignored_residue(
    tmp_path: Path,
) -> None:
    source = _repository(tmp_path / "source", "base")
    (source / "tracked.txt").write_text("modified\n", encoding="utf-8")
    (source / "new-source.txt").write_text("new source\n", encoding="utf-8")
    (source / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (source / "ignored.txt").write_text("residue\n", encoding="utf-8")

    commit, tree = source_git_identity(source)

    assert commit == git(source, "rev-parse", "HEAD")
    assert git(source, "show", f"{tree}:tracked.txt") == "modified"
    assert git(source, "show", f"{tree}:new-source.txt") == "new source"
    assert git(source, "ls-tree", "--name-only", tree).splitlines() == [
        ".gitignore",
        "new-source.txt",
        "tracked.txt",
    ]


def _repository(path: Path, content: str) -> Path:
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch=dev")
    (path / "tracked.txt").write_text(content + "\n", encoding="utf-8")
    git(path, "add", "tracked.txt")
    git(
        path,
        "-c",
        "user.name=ETHOS Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "--quiet",
        "-m",
        content,
    )
    return path
