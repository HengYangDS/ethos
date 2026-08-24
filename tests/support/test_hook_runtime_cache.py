"""Contracts for the test-only immutable hook-runtime cache."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook_runtime_install as hook_runtime_install
from ethos.adapters.repo.hook.source_identity import RuntimeSourceIdentity
from tests.support.governed_repository import git
from tools.ci.hook_runtime_cache import install_session_hook_runtime_cache
from tools.ci.hook_runtime_cache import session_hook_runtime_cache_root


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

    monkeypatch.setattr(hook_runtime_install, "resolve_runtime_wheel", build_wheel)
    install_session_hook_runtime_cache(monkeypatch, tmp_path / "cache")
    cached = hook_runtime_install.resolve_runtime_wheel
    source = Path(hook_runtime_install.__file__).resolve().parents[4]
    first = cached(source, tmp_path / "first")
    second = cached(source, tmp_path / "second")

    assert builds == 1
    assert first != second
    assert first.read_bytes() == second.read_bytes()
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


def test_independent_cache_installers_reuse_one_runtime_template(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    identity = RuntimeSourceIdentity(commit="a" * 40, tree="b" * 40)
    run = tmp_path / "pytest-run"
    cache = session_hook_runtime_cache_root(run / "popen-gw0")
    assert cache == session_hook_runtime_cache_root(run / "popen-gw7")
    builds = 0

    def build_runtime(repo: Path, _python: Path, **_kwargs: object) -> Path:
        nonlocal builds
        builds += 1
        common = Path(git(repo, "rev-parse", "--git-common-dir"))
        if not common.is_absolute():
            common = repo / common
        runtime = common / "ethos/runtime" / ("c" * 64)
        python = runtime / "venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"python")
        (runtime / "venv/bin/ethos").write_bytes(b"ethos")
        (runtime / "manifest.json").write_text(
            '{"runtime_digest":"'
            + "c" * 64
            + '","wheel_sha256":"'
            + "d" * 64
            + '","python_abi":"cpython-test","source_commit":"'
            + identity.commit
            + '","source_tree":"'
            + identity.tree
            + '"}',
            encoding="utf-8",
        )
        return runtime / "venv"

    monkeypatch.setattr(hook_runtime_install, "materialize_hook_runtime", build_runtime)
    monkeypatch.setattr(hook_runtime_install, "require_runtime", lambda *_args: None)
    monkeypatch.setattr(hook_runtime_install, "finalize_runtime", lambda *_args: None)

    outputs = []
    for name in ("first", "second"):
        repo = _git_repo(tmp_path / name)
        with pytest.MonkeyPatch.context() as worker:
            install_session_hook_runtime_cache(worker, cache)
            outputs.append(
                hook_runtime_install.materialize_hook_runtime(
                    repo,
                    Path(sys.executable),
                    expected_source=identity,
                )
            )

    assert builds == 1
    assert outputs[0] != outputs[1]
    assert all((path / "bin/python").read_bytes() == b"python" for path in outputs)


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
