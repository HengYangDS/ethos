"""Reject native report shapes that cannot support a quality claim."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import pytest

from ethos.adapters.process import run_command
from ethos.repository.policy.quality.pytest import pytest_report
from ethos.repository.policy.quality_reports import coverage_report
from ethos.repository.policy.quality_reports import coverage_stream_report
from ethos.repository.policy.quality_reports import istanbul_coverage_report
from ethos.repository.policy.quality_reports import junit_report
from ethos.repository.policy.quality_reports import junit_stream_report
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


@pytest.mark.parametrize("outcome", ["pass", "fail", "skip", "warn"])
def test_native_pytest_subtest_reports_preserve_parent_and_event_counts(
    tmp_path: Path, outcome: str
) -> None:
    """Original pytest events explain totals that its JUnit parent projection omits."""
    body = {
        "pass": "assert value > 0",
        "fail": "assert value != 2",
        "skip": "pytest.skip('native-skip') if value == 2 else None",
        "warn": "warnings.warn('native-warning') if value == 2 else None",
    }[outcome]
    source = tmp_path / "test_subtests.py"
    source.write_text(
        "import pytest\nimport warnings\n\ndef test_parent(subtests):\n"
        "    for value in (1, 2):\n        with subtests.test(value=value):\n"
        f"            {body}\n\ndef test_other():\n    assert True\n",
        encoding="utf-8",
    )
    xml, events = tmp_path / "junit.xml", tmp_path / "events.jsonl"
    result = run_command(
        tmp_path,
        (
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-p",
            "pytest_reportlog.plugin",
            "--noconftest",
            "--rootdir",
            str(tmp_path),
            "-o",
            "addopts=",
            "-o",
            f"cache_dir={tmp_path / 'cache'}",
            f"--basetemp={tmp_path / 'scratch'}",
            f"--junitxml={xml}",
            f"--report-log={events}",
            "-q",
            str(source),
        ),
        timeout=30,
        env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        remove_env=("PYTEST_ADDOPTS",),
    )
    assert result.returncode == int(outcome == "fail"), (result.stdout, result.stderr)
    original = xml.read_bytes(), events.read_bytes()
    counts, failed = junit_stream_report(original[0].decode(), pytest_events=original[1].decode())
    assert counts == {
        "total": 4,
        "failures": 2 if outcome == "fail" else 0,
        "errors": 0,
        "skipped": int(outcome == "skip"),
    }
    assert failed is (outcome in {"fail", "warn"})
    assert (xml.read_bytes(), events.read_bytes()) == original
    root = ElementTree.fromstring(original[0])
    parent, other = tuple(root.iter("testcase"))
    if outcome == "pass":
        for tag in ("failure", "error", "skipped"):
            marker = ElementTree.SubElement(parent, tag)
            with pytest.raises(ValueError, match=r"^pytest_junit_outcome_mismatch$"):
                junit_stream_report(
                    ElementTree.tostring(root, encoding="unicode"),
                    pytest_events=original[1].decode(),
                )
            parent.remove(marker)
    elif outcome in {"fail", "skip"}:
        for marker in tuple(parent):
            parent.remove(marker)
            other.append(marker)
        with pytest.raises(ValueError, match=r"^pytest_junit_outcome_mismatch$"):
            junit_stream_report(
                ElementTree.tostring(root, encoding="unicode"),
                pytest_events=original[1].decode(),
            )
    records = [json.loads(line) for line in original[1].decode().splitlines()]
    without_terminal = "\n".join(json.dumps(record) for record in records[:-1])
    with pytest.raises(ValueError, match=r"^pytest_terminal_missing$"):
        junit_stream_report(original[0].decode(), pytest_events=without_terminal)


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


@pytest.mark.parametrize(
    ("source", "filename"),
    [
        (".", "src/app.py"),
        ("src", "app.py"),
        ("absolute", "src/app.py"),
        ("absolute-src", "app.py"),
    ],
)
def test_native_coverage_source_roots_preserve_subject_identity(
    tmp_path: Path, source: str, filename: str
) -> None:
    """Native relative and absolute source roots identify the same declared subject."""
    root = tmp_path.resolve()
    if source == "absolute":
        source = str(root)
    elif source == "absolute-src":
        source = str(root / "src")
    payload = (
        '<coverage lines-covered="1" lines-valid="1" branches-covered="0" branches-valid="0">'
        f"<sources><source>{escape(source)}</source></sources>"
        f'<class filename="{filename}"><line hits="1"/></class></coverage>'
    ).encode()
    path = tmp_path / "coverage.xml"
    path.write_bytes(payload)
    expected = {
        "covered": 1,
        "total": 1,
        "combined_percent": 100,
        "files": {"src/app.py": {"lines": 1, "hit_lines": 1}},
    }
    assert (
        coverage_stream_report(
            payload, include_files=True, repository_root=root, source_paths=("src/app.py",)
        )
        == expected
    )
    assert (
        coverage_report(
            path, include_files=True, repository_root=root, source_paths=("src/app.py",)
        )
        == expected
    )


def test_native_coverage_source_roots_require_unique_subject_binding(tmp_path: Path) -> None:
    """A basename present under two admitted roots has no unique coverage identity."""
    payload = (
        b'<coverage lines-covered="1" lines-valid="1" branches-covered="0" branches-valid="0">'
        b"<sources><source>left</source><source>right</source></sources>"
        b'<class filename="app.py"><line hits="1"/></class></coverage>'
    )
    with pytest.raises(ValueError, match=r"^coverage_file_ambiguous$"):
        coverage_stream_report(
            payload,
            include_files=True,
            repository_root=tmp_path.resolve(),
            source_paths=("left/app.py", "right/app.py"),
        )


_NODE = "tests/test_answer.py::test_answer"


def _event(kind: str, **fields: object) -> str:
    return json.dumps({"$report_type": kind, **fields})


def _events(*events: str) -> str:
    start = _event("SessionStart", pytest_version="9.1.1")
    return "\n".join((start, *events, _event("SessionFinish", exitstatus=0)))


_SETUP = _event("TestReport", nodeid=_NODE, when="setup", outcome="passed")
_CALL = _event("TestReport", nodeid=_NODE, when="call", outcome="passed")


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("{", "pytest_event_invalid"),
        (_event("SessionStart", pytest_version="9.1.1"), "pytest_terminal_missing"),
        (_events(), "pytest_empty"),
        (_events(_event("TestReport", nodeid=_NODE, when="call")), "pytest_event_invalid"),
        (_events(_event("WarningMessage")), "pytest_event_invalid"),
        (_events(_event("CollectReport")), "pytest_event_invalid"),
        (
            _events(_event("TestReport", nodeid="test_answer", when="setup", outcome="passed")),
            "pytest_nodeid_invalid",
        ),
        (_events(_CALL), "pytest_report_order_invalid"),
        (_events(_SETUP), "pytest_execution_incomplete"),
        (
            _events(_SETUP, _event("SubTestReport", nodeid=_NODE, when="call", outcome="passed")),
            "pytest_subtest_unbound",
        ),
    ],
)
def test_pytest_events_refuse_incomplete_or_unordered_streams(text: str, code: str) -> None:
    """Only one complete, ordered official stream can describe a test attempt."""
    with pytest.raises(ValueError, match=f"^{code}$"):
        pytest_report(text)


def test_pytest_failed_setup_is_an_error_outcome() -> None:
    """A failed setup is a parent error, not a failed test call."""
    report = pytest_report(
        _events(
            _event("TestReport", nodeid=_NODE, when="setup", outcome="failed"),
            _event("TestReport", nodeid=_NODE, when="teardown", outcome="passed"),
        )
    )
    assert (report.errors, report.failures, report.failed) == (1, 0, True)
    assert report.outcomes == (("tests.test_answer", "test_answer", "error"),)


_JUNIT = (
    '<testsuite tests="1" failures="0" errors="0" skipped="0">'
    '<testcase classname="tests.test_answer" name="test_answer"/></testsuite>'
)


def _coverage(source: str, filename: str = "app.py") -> bytes:
    return (
        '<coverage lines-covered="1" lines-valid="1" branches-covered="0" branches-valid="0">'
        f"<sources><source>{escape(source)}</source></sources>"
        f'<class filename="{filename}"><line hits="1"/></class></coverage>'
    ).encode()


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("junit-xml", "junit_invalid"),
        ("junit-scope", "pytest_junit_scope_mismatch"),
        ("coverage-xml", "coverage_invalid"),
        ("coverage-outside", "coverage_source_outside_repository"),
        ("coverage-parent", "coverage_source_outside_repository"),
        ("coverage-unbound", "coverage_file_unbound"),
    ],
)
def test_native_report_streams_refuse_unbound_identities(
    tmp_path: Path, case: str, code: str
) -> None:
    """Retained native bytes bind only their exact producer identities and subjects."""
    root = tmp_path.resolve()
    scope = {"repository_root": root, "source_paths": ("src/app.py",), "include_files": True}
    other = _NODE.replace("test_answer", "test_other")
    other_events = _events(
        _event("TestReport", nodeid=other, when="setup", outcome="passed"),
        _event("TestReport", nodeid=other, when="call", outcome="passed"),
        _event("TestReport", nodeid=other, when="teardown", outcome="passed"),
    )
    actions = {
        "junit-xml": lambda: junit_stream_report("<"),
        "junit-scope": lambda: junit_stream_report(_JUNIT, pytest_events=other_events),
        "coverage-xml": lambda: coverage_stream_report(b"<", **scope),
        "coverage-outside": lambda: coverage_stream_report(
            _coverage(str(root.parent / "elsewhere")), **scope
        ),
        "coverage-parent": lambda: coverage_stream_report(_coverage("../elsewhere"), **scope),
        "coverage-unbound": lambda: coverage_stream_report(_coverage("src", "other.py"), **scope),
    }
    with pytest.raises(ValueError, match=f"^{code}$"):
        actions[case]()
