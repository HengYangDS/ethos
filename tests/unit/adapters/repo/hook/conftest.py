"""Share the empty repository in which the staged commit admission tests run `pre-commit`."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.hook.admission as hook_runtime
from tests.support.runtime_scenarios import git_process

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an empty repository whose selected runtime and prewrite owner are neutral.

    Its `pre-commit` therefore runs only its staged content checks.
    """
    assert git_process(tmp_path, "init", "--quiet", "--initial-branch=dev").returncode == 0
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)
    monkeypatch.setattr(
        "ethos.adapters.admission.prewrite.prewrite_guard", lambda **_kwargs: {"verdict": "pass"}
    )
    return tmp_path
