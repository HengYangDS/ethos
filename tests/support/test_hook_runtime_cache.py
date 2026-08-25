"""Contracts for the test-only immutable hook-runtime cache."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.hook_runtime_install as hook_runtime_install
from ethos.repository.release.identity import BuildIdentity
from tests.support.governed_repository import git
from tools.ci.hook_runtime_cache import install_session_hook_runtime_cache
from tools.ci.hook_runtime_cache import session_hook_runtime_cache_root
from tools.ci.hook_runtime_cache import warm_session_hook_runtime_cache


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
    identity = BuildIdentity(
        product_version="0.2.0-alpha.1",
        distribution_version="0.2.0a1.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb",
        source_commit="a" * 40,
        source_tree="b" * 40,
        channel="development",
        acceptance_state="unaccepted",
    )
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
        python = runtime / "python/bin/python"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"python")
        (runtime / "python/bin/ethos").write_bytes(b"ethos")
        immutable = runtime / "python/lib/python3.14/site-packages/immutable.py"
        immutable.parent.mkdir(parents=True)
        immutable.write_text("VALUE = 1\n", encoding="utf-8")
        (runtime / "manifest.json").write_text(
            '{"runtime_digest":"'
            + "c" * 64
            + '","wheel_sha256":"'
            + "d" * 64
            + '","python_abi":"cpython-test","product_version":"'
            + identity.product_version
            + '","distribution_version":"'
            + identity.distribution_version
            + '","channel":"development","acceptance_state":"unaccepted"'
            + ',"python_version":"3.14.7","python_implementation":"cpython"'
            + ',"dependency_lock_sha256":"'
            + "e" * 64
            + '","platform":"darwin","source_commit":"'
            + identity.source_commit
            + '","source_tree":"'
            + identity.source_tree
            + '"}',
            encoding="utf-8",
        )
        return runtime / "python"

    monkeypatch.setattr(hook_runtime_install, "materialize_hook_runtime", build_runtime)
    monkeypatch.setattr(hook_runtime_install, "require_runtime", lambda *_args: None)
    monkeypatch.setattr(hook_runtime_install, "finalize_runtime", lambda *_args: None)
    warm_session_hook_runtime_cache(cache, expected_build=identity)

    def reject_worker_build(*_args: object, **_kwargs: object) -> Path:
        message = "worker attempted to build the shared runtime template"
        raise AssertionError(message)

    monkeypatch.setattr(hook_runtime_install, "materialize_hook_runtime", reject_worker_build)

    outputs = []
    finalized = []
    for name in ("first", "second"):
        repo = _git_repo(tmp_path / name)
        with pytest.MonkeyPatch.context() as worker:
            worker.setattr(
                hook_runtime_install,
                "finalize_runtime",
                lambda runtime, *_args: finalized.append(runtime),
            )
            install_session_hook_runtime_cache(worker, cache)
            outputs.append(
                hook_runtime_install.materialize_hook_runtime(
                    repo,
                    Path(sys.executable),
                    expected_build=identity,
                )
            )

    assert builds == 1
    assert [path.name for path in finalized] == ["c" * 64, "c" * 64]
    assert outputs[0] != outputs[1]
    assert all((path / "bin/python").read_bytes() == b"python" for path in outputs)
    assert not (outputs[0] / "bin/python").samefile(outputs[1] / "bin/python")
    assert not (outputs[0] / "bin/ethos").samefile(outputs[1] / "bin/ethos")
    assert (
        not outputs[0]
        .parent.joinpath("manifest.json")
        .samefile(outputs[1].parent / "manifest.json")
    )
    immutable = tuple(path / "lib/python3.14/site-packages/immutable.py" for path in outputs)
    assert all(path.read_text(encoding="utf-8") == "VALUE = 1\n" for path in immutable)
    assert not immutable[0].samefile(immutable[1])


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
