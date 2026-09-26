"""Reject native report shapes that cannot support a quality claim."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.quality_reports import coverage_report
from ethos.repository.policy.quality_reports import junit_report

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("xml", "gap"),
    [
        ("<testsuite", "junit_invalid"),
        ("<other><testcase/></other>", "junit_root_invalid"),
        ("<testsuite/>", "junit_empty"),
        ('<testsuite failures="many"><testcase/></testsuite>', "junit_suite_count_invalid"),
        ('<testsuite errors="-1"><testcase/></testsuite>', "junit_suite_count_invalid"),
        ('<testsuite tests="2"><testcase/></testsuite>', "junit_suite_count_mismatch"),
        (
            '<testsuites tests="2"><testsuite tests="1"><testcase/></testsuite></testsuites>',
            "junit_suite_count_mismatch",
        ),
        (
            '<testsuite skipped="1"><testcase/></testsuite>',
            "junit_suite_count_mismatch",
        ),
    ],
)
def test_junit_rejects_invalid_or_false_success(tmp_path: Path, xml: str, gap: str) -> None:
    """A report is not successful merely because a file exists or cases have no failures."""
    path = tmp_path / "junit.xml"
    path.write_text(xml, encoding="utf-8")
    with pytest.raises(ValueError, match=f"^{gap}$"):
        junit_report((path,))


def test_junit_requires_a_report() -> None:
    """An empty selection cannot prove tests ran."""
    with pytest.raises(ValueError, match=r"^junit_missing$"):
        junit_report(())


def test_junit_suite_failure_is_not_hidden_by_a_passing_case(tmp_path: Path) -> None:
    """Declared suite failure is adverse evidence even without failed testcase elements."""
    path = tmp_path / "junit.xml"
    path.write_text(
        '<testsuites><testsuite failures="1"><testcase name="pass"/></testsuite></testsuites>',
        encoding="utf-8",
    )
    counts, failed = junit_report((path,))
    assert counts == {"total": 1, "failures": 0, "errors": 0, "skipped": 0}
    assert failed is True


def test_junit_declared_counts_agree_with_executed_cases(tmp_path: Path) -> None:
    """A complete native report retains matching suite-level totals."""
    path = tmp_path / "junit.xml"
    path.write_text(
        '<testsuites tests="2" failures="0" errors="0" skipped="1">'
        '<testsuite tests="2" failures="0" errors="0" skipped="1">'
        '<testcase name="passed"/><testcase name="skipped"><skipped/></testcase>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    counts, failed = junit_report((path,))
    assert counts == {"total": 2, "failures": 0, "errors": 0, "skipped": 1}
    assert failed is False


@pytest.mark.parametrize(
    ("xml", "gap"),
    [
        ("<coverage", "coverage_invalid"),
        ("<other/>", "coverage_root_invalid"),
        ("<coverage/>", "coverage_count_invalid"),
        (
            '<coverage lines-covered="no" lines-valid="1"/>',
            "coverage_count_invalid",
        ),
        (
            '<coverage lines-covered="2" lines-valid="1" branches-covered="0" branches-valid="0"/>',
            "coverage_count_invalid",
        ),
        (
            '<coverage lines-covered="0" lines-valid="0" branches-covered="0" branches-valid="0"/>',
            "coverage_empty",
        ),
    ],
)
def test_coverage_rejects_invalid_totals(tmp_path: Path, xml: str, gap: str) -> None:
    """Malformed, impossible and empty aggregate counts cannot qualify behavior."""
    path = tmp_path / "coverage.xml"
    path.write_text(xml, encoding="utf-8")
    with pytest.raises(ValueError, match=f"^{gap}$"):
        coverage_report(path)


_CLASS = '<class filename="app.py"><line hits="1"/></class>'


@pytest.mark.parametrize(
    ("classes", "gap"),
    [
        ("", "coverage_files_missing"),
        (_CLASS.replace('filename="app.py"', 'filename=""'), "coverage_file_invalid"),
        (_CLASS.replace("app.py", "/tmp/app.py"), "coverage_file_invalid"),
        (_CLASS.replace("app.py", "../app.py"), "coverage_file_invalid"),
        (_CLASS.replace("app.py", r"nested\app.py"), "coverage_file_invalid"),
        (_CLASS + _CLASS, "coverage_file_invalid"),
        (_CLASS.replace('hits="1"', 'hits="unknown"'), "coverage_hit_invalid"),
        (_CLASS.replace('hits="1"', 'hits="-1"'), "coverage_hit_invalid"),
    ],
)
def test_coverage_rejects_untrustworthy_source_scope(
    tmp_path: Path, classes: str, gap: str
) -> None:
    """A valid aggregate cannot hide absent, unsafe, duplicate or invalid source data."""
    path = tmp_path / "coverage.xml"
    path.write_text(
        '<coverage lines-covered="1" lines-valid="1" branches-covered="0" branches-valid="0">'
        + classes
        + "</coverage>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=f"^{gap}$"):
        coverage_report(path, include_files=True)
