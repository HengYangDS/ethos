"""Tests for source build identity observation boundaries."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.source as source
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git

_ROOT = Path(__file__).resolve().parents[5]


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


def test_content_policy_keeps_checkout_identity_host_portable(tmp_path: Path) -> None:
    origin = _repository(tmp_path / "origin", "first\nsecond")
    (origin / ".gitattributes").write_bytes((_ROOT / ".gitattributes").read_bytes())
    git(origin, "add", ".gitattributes")
    commit_fixture(origin, "declare canonical source bytes")
    checkout = tmp_path / "checkout"
    git(tmp_path, "-c", "core.autocrlf=true", "clone", origin.as_posix(), checkout.as_posix())

    assert git(checkout, "-c", "core.autocrlf=true", "status", "--porcelain") == ""
    assert source.source_git_identity(checkout) == tuple(
        git(checkout, "rev-parse", revision) for revision in ("HEAD", "HEAD^{tree}")
    )


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
