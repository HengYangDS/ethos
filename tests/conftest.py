"""Shared pytest fixtures for the ETHOS test suite.

The autouse Git fixture gives the suite a HERMETIC identity: many tests shell out
to `git commit` in throwaway repos, which fails when the runner has no global
user.name/user.email (the case in CI's clean container — the dominant cause of
"passes locally, red in CI"). Binding GIT_AUTHOR_*/GIT_COMMITTER_* per test makes
the suite self-contained instead of depending on the developer's ambient machine
config. The fixture also disables commit signing through Git's environment-backed
config so global `commit.gpgsign=true` cannot make temporary test commits depend
on local keys. System and user Git config are hidden entirely, while
`init.templateDir` points to a repository-owned empty template directory so
temporary test repositories never inherit developer-global hooks such as
pre-commit. Repository-local config remains authoritative so hook tests exercise
the same `core.hooksPath` semantics as production. The fixture also disables
fsmonitor so temporary test repositories never depend on a host-local filesystem
monitor.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from hypothesis.configuration import set_hypothesis_home_dir

from tests.support.hook_runtime_cache import install_session_hook_runtime_cache

_REPO_ROOT = Path(__file__).resolve().parents[1]
set_hypothesis_home_dir(
    _REPO_ROOT
    / "build/runtime/tool-cache/hypothesis"
    / os.environ.get("PYTEST_XDIST_WORKER", "local")
)


@pytest.fixture(scope="session", autouse=True)
def _cache_immutable_hook_runtime(tmp_path_factory: pytest.TempPathFactory) -> object:
    """Build package bytes once; copy them into each repository's common-dir."""
    if os.environ.get("ETHOS_TEST_DISABLE_RUNTIME_CACHE") == "1":
        yield
        return
    with pytest.MonkeyPatch.context() as monkeypatch:
        install_session_hook_runtime_cache(
            monkeypatch,
            tmp_path_factory.mktemp("ethos-hook-runtime-cache"),
        )
        yield


@pytest.fixture(autouse=True)
def _hermetic_git_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Bind a deterministic git identity so `git commit` in test repos never depends
    on ambient global config (absent in CI). Covers both the author/committer used by
    plumbing and the config-derived identity read by signature policy checks."""
    git_template = tmp_path / "empty-git-template"
    git_template.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "ETHOS Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "ETHOS Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.invalid")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "3")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "credential.helper")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "")
    monkeypatch.setenv("GIT_CONFIG_KEY_1", "init.templateDir")
    monkeypatch.setenv("GIT_CONFIG_VALUE_1", git_template.as_posix())
    monkeypatch.setenv("GIT_CONFIG_KEY_2", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_2", "false")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
