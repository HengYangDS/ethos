"""Shared pytest fixtures for the ETHOS test suite.

Some in-process CLI tests run `ethos prove --execute`, which persists a HEAD-keyed
proof record under the real repository's `.ethos/state/proof/`. That record would
leak into later tests (e.g. report/campaign closeout would see the working tree as
already proven). This autouse fixture isolates each test by clearing the proof-record
store before and after it runs.
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
