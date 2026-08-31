"""Shared pytest fixtures for the ETHOS test suite.

The autouse Git fixture gives the suite a HERMETIC identity: many tests shell out
to `git commit` in throwaway repos, which fails when the runner has no global
user.name/user.email (the case in CI's clean container — the dominant cause of
"passes locally, red in CI"). Binding GIT_AUTHOR_*/GIT_COMMITTER_* per test makes
the suite self-contained instead of depending on the developer's ambient machine
config. System and user Git config are hidden entirely, while
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

_REPO_ROOT = Path(__file__).resolve().parents[1]
set_hypothesis_home_dir(
    _REPO_ROOT
    / "build/runtime/tool-cache/hypothesis"
    / os.environ.get("PYTEST_XDIST_WORKER", "local")
)


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
    count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    entries = [
        (os.environ[f"GIT_CONFIG_KEY_{index}"], os.environ[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(count)
    ]
    declared = {key for key, _value in entries}
    entries.extend(
        (key, value)
        for key, value in (
            ("init.templateDir", git_template.as_posix()),
            ("core.fsmonitor", "false"),
            ("user.name", "ETHOS Test"),
            ("user.email", "test@example.invalid"),
        )
        if key not in declared
    )
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(entries)))
    for index, (key, value) in enumerate(entries):
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{index}", key)
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{index}", value)
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
