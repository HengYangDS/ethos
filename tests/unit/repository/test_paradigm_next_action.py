"""A paradigm report routes its next action to the repair that the product can write."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.paradigm.repair import REPAIR_PREVIEW
from tests.support.paradigm import CONFORMING
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_EDITORCONFIG = "repository_paradigm_text_normalization:.editorconfig"
_DOCSTRING = "repository_paradigm_package_docstring:src/sample/__init__.py"
_NO_EDITORCONFIG = {path: text for path, text in CONFORMING.items() if path != ".editorconfig"}
_CASES = {
    "editable-carrier": (_NO_EDITORCONFIG, [_EDITORCONFIG], REPAIR_PREVIEW),
    "judgment-only": (
        {**CONFORMING, "src/sample/__init__.py": ""},
        [_DOCSTRING],
        "open src/sample/__init__.py with a one-line docstring that names the package's purpose",
    ),
    "both": (
        {**_NO_EDITORCONFIG, "src/sample/__init__.py": ""},
        [_EDITORCONFIG, _DOCSTRING],
        REPAIR_PREVIEW,
    ),
}


@pytest.mark.parametrize(("files", "gaps", "expected"), _CASES.values(), ids=_CASES)
def test_the_next_action_is_the_repair_that_the_product_can_write(
    tmp_path: Path, files: dict[str, str], gaps: list[str], expected: str
) -> None:
    """An editable carrier routes to the repair preview; judgment alone names its own repair."""
    report = paradigm_report(tmp_path, files)
    assert report["required_gaps"] == gaps
    assert report["next_action"] == expected
    assert all(detail["repair"] for detail in report["gaps"])
