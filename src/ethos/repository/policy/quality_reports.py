"""Interpret native test reports without granting repository proof authority."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import NoReturn
from xml.etree import ElementTree

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


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
    declared_failures = _declared_junit_failures(roots)
    failed = bool(
        counts["failures"]
        or counts["errors"]
        or counts["total"] == counts["skipped"]
        or declared_failures
    )
    return counts, failed


def _declared_junit_failures(roots: tuple[ElementTree.Element, ...]) -> bool:
    """Reject suite-level failures even when testcase elements omit them."""
    failed = False
    for root in roots:
        for suite in root.iter():
            if suite.tag not in {"testsuite", "testsuites"}:
                continue
            for key in ("failures", "errors"):
                raw = suite.get(key, "0")
                try:
                    value = int(raw)
                except ValueError as error:
                    _invalid("junit_suite_count_invalid", error)
                if value < 0:
                    _invalid("junit_suite_count_invalid")
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
