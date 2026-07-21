"""Shared pytest fixtures for the ETHOS test suite.

Some in-process CLI tests run `ethos prove --execute`, which persists a HEAD-keyed
proof record under local `.ethos/state/proof/`. A single shared test store races
under xdist, so this autouse fixture points each worker at its own ignored proof
state directory and clears only that worker-owned directory around each test.

A second autouse fixture gives the suite a HERMETIC git identity: many tests shell out
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
import shutil
from pathlib import Path

import pytest
from hypothesis.configuration import set_hypothesis_home_dir

_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEST_PROOF_STATE_DIR_ENV = "ETHOS_TEST_PROOF_STATE_DIR"
set_hypothesis_home_dir(
    _REPO_ROOT
    / "build/runtime/tool-cache/hypothesis"
    / os.environ.get("PYTEST_XDIST_WORKER", "local")
)


def _worker_proof_dir() -> Path:
    worker = os.environ.get("PYTEST_XDIST_WORKER", "local")
    return Path(".ethos") / "state" / f"proof-{worker}"


@pytest.fixture(autouse=True)
def _isolate_proof_records(monkeypatch: pytest.MonkeyPatch) -> object:
    proof_dir = _worker_proof_dir()
    monkeypatch.setenv(_TEST_PROOF_STATE_DIR_ENV, proof_dir.as_posix())
    shutil.rmtree(proof_dir, ignore_errors=True)
    yield
    shutil.rmtree(proof_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def _hermetic_git_identity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Bind a deterministic git identity so `git commit` in test repos never depends
    on ambient global config (absent in CI). Covers both the author/committer used by
    plumbing and the config-derived identity read by signature policy checks."""
    git_template = tmp_path / "empty-git-template"
    git_template.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "ETHOS Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@ethos.local")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "ETHOS Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@ethos.local")
    # The repository checkout stays authoritative for CLI contract reads.  Do
    # not override the checkout's signing or hook configuration: the in-process
    # CLI must observe the same governed checkout that CI configured.  Temporary
    # repos used by tests carry explicit configuration where needed, while the
    # author/committer environment keeps their commit creation hermetic.
