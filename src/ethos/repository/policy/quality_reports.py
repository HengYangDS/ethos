"""Interpret native test reports without granting repository proof authority."""

from __future__ import annotations

import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import NoReturn
from xml.etree import ElementTree

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping


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
    declared_failures = _validated_suite_failures(roots)
    failed = bool(
        counts["failures"]
        or counts["errors"]
        or counts["total"] == counts["skipped"]
        or declared_failures
    )
    return counts, failed


def _validated_suite_failures(roots: tuple[ElementTree.Element, ...]) -> bool:
    """Reject incomplete suite totals and retain suite-level failure evidence."""
    failed = False
    for root in roots:
        for suite in root.iter():
            if suite.tag not in {"testsuite", "testsuites"}:
                continue
            cases = tuple(suite.iter("testcase"))
            observed = {
                "tests": len(cases),
                "skipped": sum(case.find("skipped") is not None for case in cases),
            }
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


def coverage_report(path: Path, *, include_files: bool = False) -> dict[str, object]:
    """Return combined statement-and-branch coverage from native XML counts."""
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as error:
        _invalid("coverage_invalid", error)
    if root.tag != "coverage":
        _invalid("coverage_root_invalid")
    try:
        pairs = tuple(
            (int(root.attrib[f"{name}-covered"]), int(root.attrib[f"{name}-valid"]))
            for name in ("lines", "branches")
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
        report["files"] = _coverage_files(root)
    return report


def _coverage_files(root: ElementTree.Element) -> dict[str, dict[str, int]]:
    """Expose native covered-source scope without reparsing the XML report."""
    files: dict[str, dict[str, int]] = {}
    for item in root.iter("class"):
        filename = item.get("filename", "")
        relative = PurePosixPath(filename)
        if (
            not filename
            or relative.is_absolute()
            or ".." in relative.parts
            or "\\" in filename
            or filename in files
        ):
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


def _lcov_hit_count(line: str) -> int:
    """Read only the line counter needed for positive source execution."""
    fields = line[3:].split(",")
    try:
        number, count = int(fields[0]), int(fields[1])
    except (IndexError, ValueError) as error:
        _invalid("javascript_coverage_invalid", error)
    if len(fields) not in {2, 3} or number < 1 or count < 0:
        _invalid("javascript_coverage_invalid")
    return count


def lcov_covered_paths(root: Path, report: Path, production: tuple[str, ...]) -> set[str]:
    """Bind the Node test runner's LCOV report to exact production modules."""
    if not report.is_file():
        _invalid("javascript_coverage_missing")
    text = report.read_text(encoding="utf-8")
    if not text.strip().endswith("end_of_record"):
        _invalid("javascript_coverage_invalid")
    expected = {(root / path).resolve(): path for path in production}
    observed: set[str] = set()
    for block in text.split("end_of_record"):
        if not block.strip():
            continue
        lines = block.splitlines()
        sources = [line[3:] for line in lines if line.startswith("SF:")]
        if len(sources) != 1 or not sources[0]:
            _invalid("javascript_coverage_invalid")
        source = Path(sources[0])
        path = (source if source.is_absolute() else root / source).resolve()
        if path in expected and any(
            _lcov_hit_count(line) > 0 for line in lines if line.startswith("DA:")
        ):
            observed.add(expected[path])
    if observed != set(production):
        _invalid("javascript_source_unexercised")
    return observed
