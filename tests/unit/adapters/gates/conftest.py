"""Share the owned Work Lane in which the source formatting tests format."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.governed_repository import prepared_work_lane

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Prepare a Work Lane that the test actor holds for the fixture Change."""
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    return prepared_work_lane(tmp_path, name="format").worktree
