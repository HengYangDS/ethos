"""Python package markers state their purpose."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.paradigm.packages import package_docstring_gaps
from tests.support.governed_repository import write_tree

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("source", "gap"),
    [
        ("", True),
        ("import os\n", True),
        ("# Comment only.\n", True),
        ("def broken(:\n", True),
        ('"""Application commands."""\n', False),
        ('"""Application commands.\n\nMore detail.\n"""\n\nVALUE = 1\n', False),
    ],
    ids=["empty", "code-first", "comment-only", "unparsable", "one-line", "multi-line"],
)
def test_a_package_marker_must_open_with_a_docstring(
    tmp_path: Path, *, source: str, gap: bool
) -> None:
    """Only a marker whose first statement is a docstring states its package's purpose."""
    files = {"src/app/__init__.py": source, "src/app/module.py": "VALUE = 1\n"}
    write_tree(tmp_path, files)

    gaps = [item.required_gap for item in package_docstring_gaps(tmp_path, frozenset(files))]

    assert gaps == (["repository_paradigm_package_docstring:src/app/__init__.py"] if gap else [])
