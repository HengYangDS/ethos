"""Share the unresolved native merge from which Change selection tests start."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.openspec_lifecycle import native_merge_fixture

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def pending_merge(tmp_path: Path) -> Path:
    """Reproduce independent open Changes with a real unresolved native merge."""
    return native_merge_fixture(tmp_path)
