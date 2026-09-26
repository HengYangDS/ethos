"""Interpret native test reports without granting repository proof authority."""

from __future__ import annotations

import json
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import NoReturn
from urllib.parse import urlparse
from urllib.request import url2pathname
from xml.etree import ElementTree

if TYPE_CHECKING:
    from collections.abc import Iterable


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


def go_covered_paths(profile: list[str], production: tuple[str, ...]) -> list[str]:
    """Bind Go's native coverage profile to exact tracked source paths."""
    if not profile or not profile[0].startswith("mode: "):
        _invalid("go_coverage_invalid")
    hits = dict.fromkeys(production, 0)
    for line in profile[1:]:
        fields = line.split()
        if len(fields) != 3:
            _invalid("go_coverage_invalid")
        source = fields[0].split(":", maxsplit=1)[0]
        try:
            statements = int(fields[1])
            count = int(fields[2])
        except ValueError as error:
            _invalid("go_coverage_invalid", error)
        if statements <= 0 or count < 0:
            _invalid("go_coverage_invalid")
        candidate = source
        while candidate:
            if candidate in hits:
                hits[candidate] += count
                break
            _, separator, candidate = candidate.partition("/")
            if not separator:
                break
    if any(count == 0 for count in hits.values()):
        _invalid("go_source_unexercised")
    return list(hits)


def _v8_entry_executed(entry: dict[str, object]) -> bool:
    """Distinguish loaded modules from unexecuted V8 source ranges."""
    functions = entry.get("functions")
    if not isinstance(functions, list):
        _invalid("javascript_coverage_invalid")
    for function in functions:
        if not isinstance(function, dict):
            _invalid("javascript_coverage_invalid")
        ranges = function.get("ranges")
        if not isinstance(ranges, list):
            _invalid("javascript_coverage_invalid")
        if any(
            isinstance(block, dict) and isinstance(block.get("count"), int) and block["count"] > 0
            for block in ranges
        ):
            return True
    return False


def v8_covered_paths(root: Path, directory: Path, production: tuple[str, ...]) -> set[str]:
    """Bind owned V8 coverage artifacts to committed JavaScript modules."""
    expected = {(root / path).resolve(): path for path in production}
    observed: set[str] = set()
    artifacts = list(directory.glob("coverage-*.json"))
    if not artifacts:
        _invalid("javascript_coverage_missing")
    for artifact in artifacts:
        try:
            document = json.loads(artifact.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            _invalid("javascript_coverage_invalid", error)
        if not isinstance(document, dict) or not isinstance(document.get("result"), list):
            _invalid("javascript_coverage_invalid")
        for entry in document["result"]:
            if not isinstance(entry, dict):
                _invalid("javascript_coverage_invalid")
            url = entry.get("url")
            if not isinstance(url, str) or not url.startswith("file:"):
                continue
            path = Path(url2pathname(urlparse(url).path)).resolve()
            if path in expected and _v8_entry_executed(entry):
                observed.add(expected[path])
    if observed != set(production):
        _invalid("javascript_source_unexercised")
    return observed
