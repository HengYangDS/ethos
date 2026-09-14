"""Tests for source build identity observation boundaries."""

from __future__ import annotations

import os
import subprocess
from itertools import pairwise
from pathlib import Path

import pytest

import ethos.adapters.process as process_adapter
import ethos.adapters.repo.runtime.source as source
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.runtime.binding import runner_source_root
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
    assert runner_source_root(repository / "tracked.txt") == repository
    module = repository / "untracked/ethos.py"
    module.parent.mkdir()
    module.touch()
    assert runner_source_root(module) == module.parent
    packaged = tmp_path / "site-packages/ethos/__init__.py"
    packaged.parent.mkdir(parents=True)
    packaged.touch()
    assert runner_source_root(packaged) == packaged.parent


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


@pytest.mark.parametrize("include_overlay", [False, True])
def test_source_identity_rejects_head_movement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, include_overlay: bool
) -> None:
    """A moving ref cannot pair the previous commit with a later source tree."""
    repository = _repository(tmp_path / "source", "base")
    observed_git = source.run_git
    moved = False

    def move_after_head(root: Path, *args: str, **kwargs):
        nonlocal moved
        result = observed_git(root, *args, **kwargs)
        if args == ("rev-parse", "HEAD") and not moved:
            moved = True
            (root / "tracked.txt").write_text("later source\n")
            commit_fixture(root, "advance source")
        return result

    monkeypatch.setattr(source, "run_git", move_after_head)
    with pytest.raises(GitExecutionError, match="build_source_identity_changed") as failure:
        source.source_git_identity(repository, include_overlay=include_overlay)
    assert failure.value.cwd == repository.as_posix()
    assert failure.value.observation["observed_head"] == git(repository, "rev-parse", "HEAD")


def test_source_identity_steps_share_one_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each native query consumes the same budget instead of starting a new timeout."""
    repository = _repository(tmp_path / "source", "base")
    observed_git = source.run_git
    elapsed = 0.0
    timeouts: list[float] = []
    monkeypatch.setattr(source, "monotonic", lambda: elapsed, raising=False)

    def observe_deadline(root: Path, *args: str, **kwargs):
        nonlocal elapsed
        timeout = kwargs.get("timeout")
        assert isinstance(timeout, float)
        assert 0 < timeout <= 30
        timeouts.append(timeout)
        elapsed += 1
        return observed_git(root, *args, **kwargs)

    monkeypatch.setattr(source, "run_git", observe_deadline)
    source.source_git_identity(repository)
    assert all(later < earlier for earlier, later in pairwise(timeouts))
    assert len(timeouts) >= 3


def test_source_identity_timeout_preserves_index_and_removes_owned_scratch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Native timeout evidence survives without leaving the observation index behind."""
    repository = _repository(tmp_path / "source", "base")
    index = repository / ".git/index"
    before = index.read_bytes()
    observed_process = process_adapter.run_command
    temporary: list[Path] = []

    def timeout_overlay(root: Path, command: tuple[str, ...], **kwargs):
        if command[1:] == ("add", "-A"):
            temporary.append(Path(kwargs["env"]["GIT_INDEX_FILE"]).parent)
            raise subprocess.TimeoutExpired(command, 0.01, b"partial", b"waiting")
        return observed_process(root, command, **kwargs)

    monkeypatch.setattr(process_adapter, "run_command", timeout_overlay)
    with pytest.raises(GitExecutionError, match="git_process_timed_out") as failure:
        source.source_git_identity(repository)
    assert failure.value.observation["stderr"] == "waiting"
    assert temporary
    assert all(not path.exists() for path in temporary)
    assert index.read_bytes() == before


@pytest.mark.parametrize("mode", ["staged", "deleted", "mode", "assume", "skip", "untracked"])
def test_source_overlay_preserves_native_content_without_mutating_the_live_index(
    tmp_path: Path, mode: str
) -> None:
    """Caller staging and index optimization flags cannot hide current source content."""
    repository = _repository(tmp_path / "source", "base")
    path = repository / "tracked.txt"
    if mode == "staged":
        path.write_text("intermediate\n")
        git(repository, "add", "tracked.txt")
    elif mode in {"assume", "skip"}:
        git(
            repository,
            "update-index",
            f"--{'assume-unchanged' if mode == 'assume' else 'skip-worktree'}",
            "tracked.txt",
        )
    elif mode == "mode":
        if os.name == "nt":
            pytest.skip("POSIX executable permission observation")
        git(repository, "config", "core.filemode", "true")
        path.chmod(0o755)
    if mode == "deleted":
        path.unlink()
    elif mode == "untracked":
        path = repository / "new-source.txt"
        path.write_text("current\n")
    elif mode != "mode":
        path.write_text("current\n")
    index = repository / ".git/index"
    before = index.read_bytes()
    commit, tree = source.source_git_identity(repository)
    assert commit == git(repository, "rev-parse", "HEAD")
    assert tree != git(repository, "rev-parse", "HEAD^{tree}")
    if mode == "deleted":
        assert "tracked.txt" not in git(repository, "ls-tree", "--name-only", tree).splitlines()
    elif mode == "mode":
        assert git(repository, "ls-tree", tree, "tracked.txt").startswith("100755 ")
    else:
        assert git(repository, "show", f"{tree}:{path.name}") == "current"
    assert index.read_bytes() == before


def test_source_observation_refuses_a_step_after_total_budget_expires(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Time spent in earlier queries cannot be recovered by a later per-step timeout."""
    repository = _repository(tmp_path / "source", "base")
    observed_git = source.run_git
    elapsed = 0.0

    def exhaust(root: Path, *args: str, **kwargs):
        nonlocal elapsed
        result = observed_git(root, *args, **kwargs)
        elapsed = 31.0
        return result

    monkeypatch.setattr(source, "monotonic", lambda: elapsed)
    monkeypatch.setattr(source, "run_git", exhaust)
    with pytest.raises(GitExecutionError, match="git_process_timed_out") as failure:
        source.source_git_identity(repository, include_overlay=False)
    assert failure.value.observation["timeout_seconds"] == 0.0
