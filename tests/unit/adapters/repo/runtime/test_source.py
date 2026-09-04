"""Tests for source build identity observation boundaries."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.runtime.source as source
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from collections.abc import Mapping


_ROOT = Path(__file__).resolve().parents[5]


def _repository(path: Path, content: str) -> Path:
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch=dev")
    (path / "tracked.txt").write_text(content + "\n")
    commit_fixture(path, content)
    return path


def _run_git_with_environment(
    root: Path,
    *args: str,
    environment: Mapping[str, str],
) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


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


def test_repository_content_policy_keeps_clean_checkout_identity_host_portable(
    tmp_path: Path,
) -> None:
    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "init", "--quiet", "--initial-branch=dev")
    policy = _ROOT / ".gitattributes"
    if policy.is_file():
        (origin / policy.name).write_bytes(policy.read_bytes())
    (origin / "tracked.txt").write_bytes(b"first\nsecond\n")
    commit_fixture(origin, "canonical source")

    global_config = tmp_path / "gitconfig"
    global_config.write_text("[core]\n\tautocrlf = true\n", encoding="utf-8")
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": global_config.as_posix(),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    checkout = tmp_path / "checkout"
    _run_git_with_environment(
        tmp_path,
        "clone",
        "--quiet",
        origin.as_posix(),
        checkout.as_posix(),
        environment=environment,
    )

    assert (
        _run_git_with_environment(checkout, "status", "--porcelain", environment=environment) == ""
    )
    assert source.source_git_identity(checkout) == (
        git(checkout, "rev-parse", "HEAD"),
        git(checkout, "rev-parse", "HEAD^{tree}"),
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
