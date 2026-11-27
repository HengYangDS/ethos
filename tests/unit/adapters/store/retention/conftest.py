"""Share the governed repository in which the record retirement preview and apply run."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.application.retention as retention
from tests.support.governed_repository import adopted_repository

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a governed repository whose preview and apply run as the selected runtime."""
    repo, _head = adopted_repository(tmp_path)
    monkeypatch.setattr(retention, "runtime_selected", lambda _root: True)
    return repo
