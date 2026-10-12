"""Reject native report shapes that cannot support a quality claim."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.quality_reports import coverage_report
from ethos.repository.policy.quality_reports import istanbul_coverage_report
from ethos.repository.policy.quality_reports import junit_report
from ethos.repository.policy.quality_reports import node_event_report

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


@pytest.mark.parametrize(
    "defect",
    ["none", "missing-terminal", "duplicate-terminal", "out-of-scope", "extra-test", "bad-counter"],
)
def test_native_node_events_require_conserved_scope_and_terminal(
    tmp_path: Path, defect: str
) -> None:
    """The test journal conserves terminal counts and exact entry scope, not coverage."""
    test = str(tmp_path / "answer.test.js")
    counts = {"tests": 1, "passed": 1, "failed": 0, "cancelled": 0, "skipped": 0, "todo": 0}
    events = [
        {"type": "test:enqueue", "data": {"file": test}},
        {"type": "test:summary", "data": {"success": True, "counts": counts}},
    ]
    if defect == "missing-terminal":
        events.pop()
    elif defect == "duplicate-terminal":
        events.append(events[-1])
    elif defect == "out-of-scope":
        events[0]["data"]["file"] = str(tmp_path / "other.test.js")
    elif defect == "extra-test":
        events.insert(
            1, {"type": "test:enqueue", "data": {"file": str(tmp_path / "other.test.js")}}
        )
    elif defect == "bad-counter":
        counts["passed"] = 2
    payload = "\n".join(map(json.dumps, events))
    if defect == "none":
        assert node_event_report(tmp_path, payload, ("answer.test.js",))[0]["passed"] == 1
    else:
        with pytest.raises(ValueError, match="javascript_"):
            node_event_report(tmp_path, payload, ("answer.test.js",))


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ("{not json\n", "javascript_native_events_invalid"),
        ("[]\n", "javascript_native_events_invalid"),
    ],
)
def test_node_event_journal_must_be_native_event_objects(
    tmp_path: Path, payload: str, code: str
) -> None:
    """Only complete native event objects can stand for a JavaScript test attempt."""
    with pytest.raises(ValueError, match=code):
        node_event_report(tmp_path, payload, ())


def _istanbul_axis(total: int, covered: int) -> dict[str, int]:
    return {"total": total, "covered": covered, "skipped": 0}


@pytest.mark.parametrize("fault", ["json", "summary", "counts", "empty"])
def test_istanbul_report_conserves_exact_native_counts(tmp_path: Path, fault: str) -> None:
    """Native coverage counts must parse, sum exactly and measure real statements."""
    source = tmp_path / "src/answer.js"
    source.parent.mkdir()
    source.write_text("export const answer = 42;\n", encoding="utf-8")
    axes = ("lines", "branches", "functions", "statements")
    measured = 0 if fault == "empty" else 1
    document: dict[str, object] = {
        "total": {axis: _istanbul_axis(measured, measured) for axis in axes},
        str(source): {axis: _istanbul_axis(measured, measured) for axis in axes},
    }
    if fault == "summary":
        document[str(source)] = "not a summary"
    if fault == "counts":
        document["total"] = {axis: _istanbul_axis(2, 1) for axis in axes}
    report = tmp_path / "coverage-summary.json"
    report.write_text("{" if fault == "json" else json.dumps(document), encoding="utf-8")
    code = {
        "json": "javascript_coverage_invalid",
        "summary": "javascript_coverage_invalid",
        "counts": "javascript_coverage_count_invalid",
        "empty": "javascript_coverage_empty",
    }[fault]
    with pytest.raises(ValueError, match=code):
        istanbul_coverage_report(tmp_path, report, ("src/answer.js",))
