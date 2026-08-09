"""Contracts for the test-only immutable hook-runtime cache."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook_runtime as hook_runtime
import ethos.adapters.repo.hook_runtime_install as hook_runtime_install
from tests.support.governed_repository import git
from tests.support.hook_runtime_cache import install_session_hook_runtime_cache


def test_cache_reuses_package_bytes_but_keeps_repository_runtime_paths_isolated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    builds = 0

    def build_wheel(_source: Path, wheel_dir: Path) -> Path:
        nonlocal builds
        builds += 1
        wheel_dir.mkdir(parents=True, exist_ok=True)
        wheel = wheel_dir / "ethos-built.whl"
        wheel.write_text("immutable package bytes\n", encoding="utf-8")
        return wheel

    def materialize(repo: Path, python: Path) -> Path:
        wheel = hook_runtime_install.resolve_runtime_wheel(tmp_path, repo / "wheel")
        runtime = repo / ".git/ethos/runtime/content-digest/venv"
        runtime.mkdir(parents=True)
        (runtime / "wheel-bytes.txt").write_bytes(wheel.read_bytes())
        assert python == Path(sys.executable)
        return runtime

    monkeypatch.setattr(hook_runtime_install, "resolve_runtime_wheel", build_wheel)
    monkeypatch.setattr(hook_runtime, "materialize_hook_runtime", materialize)
    install_session_hook_runtime_cache(monkeypatch, tmp_path / "cache")
    cached = hook_runtime.materialize_hook_runtime
    first_repo = _git_repo(tmp_path / "first")
    second_repo = _git_repo(tmp_path / "second")
    first = cached(first_repo, Path(sys.executable))
    second = cached(second_repo, Path(sys.executable))

    assert builds == 1
    assert first != second
    assert (first / "wheel-bytes.txt").read_bytes() == (second / "wheel-bytes.txt").read_bytes()
    assert not first.samefile(second)


def test_cache_rejects_a_cache_root_inside_the_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = Path(__file__).resolve().parents[2]
    status_before = _git_status(repository)

    with pytest.raises(ValueError, match="test_hook_runtime_cache_inside_repository"):
        install_session_hook_runtime_cache(monkeypatch, repository / "ethos/runtime/cache")

    assert _git_status(repository) == status_before
    assert not any(line.startswith("?? ethos/runtime/") for line in status_before)


def _git_repo(path: Path) -> Path:
    path.mkdir()
    git(path, "init", "-b", "dev")
    return path


def _git_status(root: Path) -> tuple[str, ...]:
    completed = subprocess.run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(completed.stdout.splitlines())
