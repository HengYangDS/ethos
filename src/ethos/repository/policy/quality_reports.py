"""Interpret native test reports without granting repository proof authority."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Annotated
from typing import NoReturn
from typing import TypedDict
from xml.etree import ElementTree

from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictStr
from pydantic import TypeAdapter
from pydantic import ValidationError

from ethos.repository.policy.quality.pytest import pytest_report

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ethos.repository.policy.quality.pytest import PytestReport

_NativeCount = Annotated[int, Field(strict=True, ge=0)]


class _PreciseCoverageRange(TypedDict):
    """One native execution counter over a JavaScript source range."""

    startOffset: _NativeCount
    endOffset: _NativeCount
    count: _NativeCount


class _PreciseCoverageFunction(TypedDict):
    """Native function identity, granularity and source counters."""

    functionName: StrictStr
    isBlockCoverage: StrictBool
    ranges: Annotated[list[_PreciseCoverageRange], Field(min_length=1)]


class _PreciseCoverageScript(TypedDict):
    """One script identity and its observed function coverage."""

    scriptId: StrictStr
    url: StrictStr
    functions: list[_PreciseCoverageFunction]


class _PreciseCoverageProcess(TypedDict):
    """One original precise-coverage observation, not an authenticated producer."""

    result: Annotated[list[_PreciseCoverageScript], Field(min_length=1)]
    timestamp: Annotated[float, Field(strict=True, ge=0)]


_PRECISE_COVERAGE_ADAPTER = TypeAdapter(_PreciseCoverageProcess)


def validate_node_precise_coverage(payload: bytes) -> None:
    """Validate one Node precise-coverage file; a valid shape never authenticates its producer."""
    try:
        report = _PRECISE_COVERAGE_ADAPTER.validate_json(payload)
    except ValidationError as error:
        _invalid("javascript_native_coverage_invalid", error)
    scripts = report["result"]
    if len({script["scriptId"] for script in scripts}) != len(scripts) or any(
        item["startOffset"] > item["endOffset"]
        for script in scripts
        for function in script["functions"]
        for item in function["ranges"]
    ):
        _invalid("javascript_native_coverage_invalid")


def _invalid(code: str, error: Exception | None = None) -> NoReturn:
    raise ValueError(code) from error


def junit_report(paths: Iterable[Path]) -> tuple[dict[str, int], bool]:
    """Return executed-case counts and whether native test evidence failed."""
    files = tuple(paths)
    if not files:
        _invalid("junit_missing")
    try:
        roots = tuple(ElementTree.parse(path).getroot() for path in files)
    except ElementTree.ParseError as error:
        _invalid("junit_invalid", error)
    return _junit_roots_report(roots)


def junit_stream_report(
    text: str, *, pytest_events: str | None = None
) -> tuple[dict[str, int], bool]:
    """Validate a JUnit report captured from the same native command."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        _invalid("junit_invalid", error)
    native = pytest_report(pytest_events) if pytest_events is not None else None
    return _junit_roots_report((root,), native=native)


def _junit_roots_report(
    roots: tuple[ElementTree.Element, ...],
    *,
    native: PytestReport | None = None,
) -> tuple[dict[str, int], bool]:
    if any(root.tag not in {"testsuite", "testsuites"} for root in roots):
        _invalid("junit_root_invalid")
    cases = tuple(case for root in roots for case in root.iter("testcase"))
    if not cases:
        _invalid("junit_empty")
    counts = {
        "total": len(cases),
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
    }
    if native is not None:
        identities = Counter((case.get("classname", ""), case.get("name", "")) for case in cases)
        if identities != Counter(native.cases):
            _invalid("pytest_junit_scope_mismatch")
        outcomes = Counter(
            (case.get("classname", ""), case.get("name", ""), child.tag)
            for case in cases
            for child in case
            if child.tag in {"failure", "error", "skipped"}
        )
        if outcomes != Counter(native.outcomes):
            _invalid("pytest_junit_outcome_mismatch")
        counts = {
            "total": native.total,
            "failures": native.failures,
            "errors": native.errors,
            "skipped": native.skipped,
        }
    declared_failures = _validated_suite_failures(roots, native=native)
    failed = bool(
        counts["failures"]
        or counts["errors"]
        or counts["total"] == counts["skipped"]
        or declared_failures
        or (native is not None and native.failed)
    )
    return counts, failed


def _validated_suite_failures(
    roots: tuple[ElementTree.Element, ...], *, native: PytestReport | None = None
) -> bool:
    """Reject incomplete suite totals and retain suite-level failure evidence."""
    failed = False
    if native is not None and sum(len(tuple(root.iter("testsuite"))) for root in roots) != 1:
        _invalid("pytest_junit_scope_mismatch")
    for root in roots:
        for suite in root.iter():
            if suite.tag not in {"testsuite", "testsuites"}:
                continue
            cases = tuple(suite.iter("testcase"))
            observed = {
                "tests": len(cases),
                "skipped": sum(case.find("skipped") is not None for case in cases),
            }
            if native is not None:
                observed = {
                    "tests": native.total,
                    "failures": native.failures,
                    "errors": native.errors,
                    "skipped": native.skipped,
                }
            failed |= _suite_count_failure(suite, observed)
    return failed


def _suite_count_failure(suite: ElementTree.Element, observed: dict[str, int]) -> bool:
    """One suite's native declared totals retain their observed count meaning."""
    failed = False
    for key in ("tests", "failures", "errors", "skipped"):
        raw = suite.get(key)
        if raw is None:
            continue
        try:
            value = int(raw)
        except ValueError as error:
            _invalid("junit_suite_count_invalid", error)
        if value < 0:
            _invalid("junit_suite_count_invalid")
        if key in observed and value != observed[key]:
            _invalid("junit_suite_count_mismatch")
        if key in {"failures", "errors"}:
            failed |= value > 0
    return failed


def coverage_report(
    path: Path,
    *,
    include_files: bool = False,
    repository_root: Path | None = None,
    source_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    """Return combined statement-and-branch coverage from native XML counts."""
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as error:
        _invalid("coverage_invalid", error)
    return _coverage_root_report(
        root,
        include_files=include_files,
        repository_root=repository_root,
        source_paths=source_paths,
    )


def coverage_stream_report(
    payload: bytes,
    *,
    include_files: bool = False,
    repository_root: Path | None = None,
    source_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    """Interpret retained native coverage bytes using the same measurement owner."""
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        _invalid("coverage_invalid", error)
    return _coverage_root_report(
        root,
        include_files=include_files,
        repository_root=repository_root,
        source_paths=source_paths,
    )


def _coverage_root_report(
    root: ElementTree.Element,
    *,
    include_files: bool = False,
    repository_root: Path | None = None,
    source_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    """Share identical count and scope validation for native path and stream readers."""
    if root.tag != "coverage":
        _invalid("coverage_root_invalid")
    # A branch total declares branch measurement; kcov writes only a constant covered value.
    names = ("lines", "branches") if "branches-valid" in root.attrib else ("lines",)
    try:
        pairs = tuple(
            (int(root.attrib[f"{name}-covered"]), int(root.attrib[f"{name}-valid"]))
            for name in names
        )
    except (KeyError, ValueError) as error:
        _invalid("coverage_count_invalid", error)
    if any(not 0 <= covered <= total for covered, total in pairs):
        _invalid("coverage_count_invalid")
    covered = sum(item[0] for item in pairs)
    total = sum(item[1] for item in pairs)
    if not total:
        _invalid("coverage_empty")
    report: dict[str, object] = {
        "covered": covered,
        "total": total,
        "combined_percent": 100 * covered / total,
    }
    if include_files:
        report["files"] = _coverage_files(root, repository_root, source_paths)
    return report


def _coverage_source_roots(root: ElementTree.Element, repository_root: Path) -> tuple[str, ...]:
    """Resolve native XML coordinates within the exact producer's repository."""
    prefixes: list[str] = []
    for source in root.findall("sources/source"):
        native = Path(source.text or ".")
        try:
            relative = (
                native.resolve().relative_to(repository_root) if native.is_absolute() else native
            )
        except ValueError as error:
            _invalid("coverage_source_outside_repository", error)
        if ".." in relative.parts:
            _invalid("coverage_source_outside_repository")
        prefixes.append(relative.as_posix())
    return tuple(dict.fromkeys(prefixes)) or (".",)


def _coverage_files(
    root: ElementTree.Element,
    repository_root: Path | None,
    source_paths: tuple[str, ...],
) -> dict[str, dict[str, int]]:
    """Expose native covered-source scope without reparsing the XML report."""
    files: dict[str, dict[str, int]] = {}
    prefixes = _coverage_source_roots(root, repository_root) if repository_root else ()
    declared = frozenset(source_paths)
    for item in root.iter("class"):
        filename = item.get("filename", "")
        relative = PurePosixPath(filename)
        if not filename or relative.is_absolute() or ".." in relative.parts or "\\" in filename:
            _invalid("coverage_file_invalid")
        if prefixes:
            matches = {
                PurePosixPath(prefix, filename).as_posix()
                for prefix in prefixes
                if PurePosixPath(prefix, filename).as_posix() in declared
            }
            if not matches:
                _invalid("coverage_file_unbound")
            if len(matches) != 1:
                _invalid("coverage_file_ambiguous")
            filename = next(iter(matches))
        if filename in files:
            _invalid("coverage_file_invalid")
        try:
            hits = tuple(int(line.get("hits", "")) for line in item.iter("line"))
        except ValueError as error:
            _invalid("coverage_hit_invalid", error)
        if any(hit < 0 for hit in hits):
            _invalid("coverage_hit_invalid")
        files[filename] = {"lines": len(hits), "hit_lines": sum(hit > 0 for hit in hits)}
    if not files:
        _invalid("coverage_files_missing")
    return files


def _go_coverage_rows(profile: list[str]) -> list[tuple[str, int, int]]:
    """Parse Go's native coverage rows before resolving repository identity."""
    if not profile or profile[0] not in {"mode: set", "mode: count", "mode: atomic"}:
        _invalid("go_coverage_invalid")
    rows = []
    for line in profile[1:]:
        row = re.fullmatch(r"(.+):[0-9]+\.[0-9]+,[0-9]+\.[0-9]+ ([0-9]+) ([0-9]+)", line)
        if row is None:
            _invalid("go_coverage_invalid")
        rows.append((row.group(1), int(row.group(2)), int(row.group(3))))
    return rows


def go_covered_paths(
    profile: list[str],
    production: tuple[str, ...],
    source_paths: Mapping[str, str],
    *,
    zero_statement_paths: frozenset[str] = frozenset(),
) -> list[str]:
    """Bind Go's complete native profile through exact package-file identities."""
    scope = set(production)
    if not source_paths or not set(source_paths.values()) <= scope:
        _invalid("go_coverage_source_map_invalid")
    observed: set[str] = set()
    applicable: set[str] = set()
    covered: set[str] = set()
    for source, statements, count in _go_coverage_rows(profile):
        candidate = source_paths.get(source)
        if candidate is None:
            _invalid("go_coverage_source_unmapped")
        observed.add(candidate)
        if statements:
            applicable.add(candidate)
            if count:
                covered.add(candidate)
    if applicable - covered:
        _invalid("go_source_unexercised")
    if observed | zero_statement_paths != set(source_paths.values()):
        _invalid("go_coverage_source_missing")
    if not applicable:
        _invalid("go_coverage_no_applicable_statements")
    return [path for path in production if path in applicable]


def quality_evidence_paths(report: object, axis: str, source_tree: str) -> tuple[str, ...]:
    """Return only successful, exact-tree, axis-matching native subject evidence."""
    if not isinstance(report, Mapping) or report.get("verdict") != "pass":
        return ()
    evidence = report.get("quality_evidence")
    selected = evidence.get("selected_paths") if isinstance(evidence, Mapping) else None
    return (
        tuple(selected)
        if (
            isinstance(evidence, Mapping)
            and evidence.get("axis") == axis
            and evidence.get("source_tree") == source_tree
            and isinstance(selected, (list, tuple))
            and bool(selected)
            and all(isinstance(path, str) and path for path in selected)
            and len(set(selected)) == len(selected)
        )
        else ()
    )


def node_event_report(
    root: Path,
    payload: str,
    tests: tuple[str, ...],
) -> tuple[dict[str, int], tuple[str, ...]]:
    """Validate the original test journal without substituting a coverage collector."""
    try:
        events = tuple(json.loads(line) for line in payload.splitlines() if line)
    except json.JSONDecodeError as error:
        _invalid("javascript_native_events_invalid", error)
    if not events or any(
        not isinstance(event, dict)
        or not isinstance(event.get("type"), str)
        or not isinstance(event.get("data"), dict)
        for event in events
    ):
        _invalid("javascript_native_events_invalid")
    terminal = events[-1]
    if terminal["type"] != "test:summary" or "file" in terminal["data"]:
        _invalid("javascript_native_events_incomplete")
    if (
        sum(event["type"] == "test:summary" and "file" not in event["data"] for event in events)
        != 1
    ):
        _invalid("javascript_native_events_incomplete")
    summary = terminal["data"]
    counts = summary.get("counts")
    names = ("tests", "passed", "failed", "cancelled", "skipped", "todo")
    if (
        not isinstance(counts, dict)
        or type(summary.get("success")) is not bool
        or any(type(counts.get(key)) is not int or counts[key] < 0 for key in names)
        or counts["tests"] != sum(counts[key] for key in names[1:])
        or summary["success"] != (not counts["failed"] and not counts["cancelled"])
    ):
        _invalid("javascript_native_summary_invalid")
    _node_test_scope(root, events, tests)
    diagnostics = tuple(
        str(event["data"].get("message", ""))
        for event in events
        if event["type"] == "test:stderr"
        or (
            event["type"] == "test:diagnostic"
            and event["data"].get("level") not in {"info", "debug"}
        )
    )
    return (
        {
            "total": counts["tests"],
            "passed": counts["passed"],
            "skipped": counts["skipped"],
            "failures": counts["failed"],
            "errors": counts["cancelled"],
        },
        diagnostics,
    )


def istanbul_coverage_report(
    root: Path, report: Path, production: tuple[str, ...]
) -> tuple[dict[str, object], set[str]]:
    """Conserve native four-axis counts and exact subjects without reimplementing c8 policy."""
    try:
        document = json.loads(report.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        _invalid("javascript_coverage_invalid", error)
    if not isinstance(document, dict) or not isinstance(document.get("total"), dict):
        _invalid("javascript_coverage_invalid")
    expected = {(root / path).resolve(): path for path in production}
    files = {Path(path).resolve(): values for path, values in document.items() if path != "total"}
    if len(files) != len(document) - 1 or set(files) != set(expected):
        _invalid("javascript_coverage_scope_incomplete")
    axes = ("lines", "branches", "functions", "statements")
    for summary in document.values():
        if not isinstance(summary, dict):
            _invalid("javascript_coverage_invalid")
        for axis in axes:
            counts = summary.get(axis)
            if (
                not isinstance(counts, dict)
                or any(type(counts.get(key)) is not int for key in ("total", "covered", "skipped"))
                or not 0 <= counts["covered"] <= counts["total"]
                or not 0 <= counts["skipped"] <= counts["total"]
            ):
                _invalid("javascript_coverage_invalid")
    totals = document["total"]
    if any(
        totals[axis][key] != sum(summary[axis][key] for summary in files.values())
        for axis in axes
        for key in ("total", "covered", "skipped")
    ):
        _invalid("javascript_coverage_count_invalid")
    if not totals["statements"]["total"]:
        _invalid("javascript_coverage_empty")
    covered = {
        expected[path]
        for path, summary in files.items()
        if any(summary[axis]["covered"] > 0 for axis in axes)
        or all(summary[axis]["total"] == 0 for axis in axes)
    }
    return totals, covered


def _node_test_scope(
    root: Path, events: tuple[dict[str, object], ...], tests: tuple[str, ...]
) -> None:
    """Require each selected native test file to appear in the original event stream."""
    entered: set[Path] = set()
    for event in events:
        data = event.get("data")
        if (
            event.get("type") == "test:enqueue"
            and isinstance(data, dict)
            and "entryFile" not in data
        ):
            file = data.get("file")
            if isinstance(file, str):
                entered.add(Path(file).resolve())
    if {(root / path).resolve() for path in tests} != entered:
        _invalid("javascript_native_test_scope_incomplete")
