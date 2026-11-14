"""A paradigm report routes its next action to the repair that the product can write."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.repository.paradigm.report as report_module
from ethos.contracts.paradigm.declaration import load_repository_paradigm
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
    "reporting-only": ({**CONFORMING, "src/sample/__init__.py": ""}, [], ""),
    "both": ({**_NO_EDITORCONFIG, "src/sample/__init__.py": ""}, [_EDITORCONFIG], REPAIR_PREVIEW),
}


@pytest.mark.parametrize(("files", "gaps", "expected"), _CASES.values(), ids=_CASES)
def test_the_next_action_is_the_repair_that_the_product_can_write(
    tmp_path: Path, files: dict[str, str], gaps: list[str], expected: str
) -> None:
    """An editable carrier routes to the repair preview; a reporting obligation routes nowhere."""
    report = paradigm_report(tmp_path, files)
    assert report["required_gaps"] == gaps
    assert report["next_action"] == expected
    assert all(detail["repair"] for detail in report["gaps"])


def test_a_reporting_obligation_is_named_and_does_not_block(tmp_path: Path) -> None:
    """The audit names a reporting gap with its repair, apart from the gaps that block."""
    report = paradigm_report(tmp_path, {**CONFORMING, "src/sample/__init__.py": ""})

    assert (report["verdict"], report["required_gaps"]) == ("pass", [])
    assert report["reported_gaps"] == [_DOCSTRING]
    assert [detail["obligation"] for detail in report["gaps"]] == ["package-docstring"]


def test_an_armed_obligation_blocks_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Arming is the declaration's edit: without the row, the same gap is required."""
    armed = load_repository_paradigm().model_copy(update={"reporting": ()})
    monkeypatch.setattr(report_module, "load_repository_paradigm", lambda: armed)

    report = paradigm_report(tmp_path, {**CONFORMING, "src/sample/__init__.py": ""})

    assert (report["verdict"], report["required_gaps"]) == ("block", [_DOCSTRING])
    assert report["reported_gaps"] == []
