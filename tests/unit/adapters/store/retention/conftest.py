"""Share the governed repository in which the record retirement preview and apply run."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.application.retention as retention
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a governed repository whose preview and apply run as the selected runtime."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    monkeypatch.setattr(retention, "runtime_selected", lambda _root: True)
    return repo
