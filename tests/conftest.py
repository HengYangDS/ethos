"""Shared pytest fixtures for the ETHOS test suite.

Some in-process CLI tests run `ethos prove --execute`, which persists a HEAD-keyed
proof record under the real repository's `.ethos/state/proof/`. That record would
leak into later tests (e.g. report/campaign closeout would see the working tree as
already proven). This autouse fixture isolates each test by clearing the proof-record
store before and after it runs.

A second autouse fixture gives the suite a HERMETIC git identity: many tests shell out
to `git commit` in throwaway repos, which fails when the runner has no global
user.name/user.email (the case in CI's clean container — the dominant cause of
"passes locally, red in CI"). Binding GIT_AUTHOR_*/GIT_COMMITTER_* per test makes the
suite self-contained instead of depending on the developer's ambient machine config.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_PROOF_DIR = Path(__file__).resolve().parents[1] / ".ethos" / "state" / "proof"


@pytest.fixture(autouse=True)
def _isolate_proof_records() -> object:
    shutil.rmtree(_PROOF_DIR, ignore_errors=True)
    yield
    shutil.rmtree(_PROOF_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def _hermetic_git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bind a deterministic git identity so `git commit` in test repos never depends
    on ambient global config (absent in CI). Covers both the author/committer used by
    plumbing and the config-derived identity read by signature policy checks."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "ETHOS Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@ethos.local")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "ETHOS Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@ethos.local")
