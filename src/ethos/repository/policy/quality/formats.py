"""Read tool-neutral LCOV and SARIF reports without granting proof authority."""

from __future__ import annotations

import json
from collections.abc import Iterator
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import NoReturn
from urllib.parse import unquote
from urllib.parse import urlsplit

_ADVERSE = frozenset({"warning", "error"})
_LEVELS = frozenset({"none", "note", *_ADVERSE})
_KINDS = frozenset({"notApplicable", "pass", "fail", "review", "open", "informational"})


def _invalid(code: str, error: Exception | None = None) -> NoReturn:
    raise ValueError(code) from error


def repository_file(name: str, *, repository_root: Path) -> str:
    """Bind a native file name to a repository-relative path without leaving the root."""
    native = Path(name)
    if native.is_absolute():
        try:
            return native.resolve().relative_to(repository_root).as_posix()
        except ValueError as error:
            _invalid("coverage_source_outside_repository", error)
    relative = PurePosixPath(name)
    if not name or ".." in relative.parts or "\\" in name:
        _invalid("coverage_file_invalid")
    return relative.as_posix()


def _lcov_records(text: str) -> Iterator[tuple[str, list[tuple[str, str]]]]:
    """Split LCOV text into its source records without interpreting their values."""
    name: str | None = None
    entries: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        key, separator, value = line.partition(":")
        if not line or key == "TN":
            continue
        if line == "end_of_record" and name is not None:
            yield name, entries
            name, entries = None, []
        elif key == "SF":
            if name is not None:
                _invalid("lcov_record_unterminated")
            name = value
        elif name is None or not separator or not key.isupper():
            _invalid("lcov_invalid")
        else:
            entries.append((key, value))
    if name is not None:
        _invalid("lcov_record_unterminated")


def _count(value: str, gap: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        _invalid(gap, error)
    if number < 0:
        _invalid(gap)
    return number


def _lcov_lines(entries: list[tuple[str, str]]) -> dict[int, int]:
    """Return one record's line hits after checking its optional `LF` and `LH` totals."""
    lines: dict[int, int] = {}
    declared: dict[str, int] = {}
    for key, value in entries:
        if key == "DA":
            fields = value.split(",")
            if len(fields) not in {2, 3}:
                _invalid("lcov_line_invalid")
            number = _count(fields[0], "lcov_line_invalid")
            if number < 1:
                _invalid("lcov_line_invalid")
            lines[number] = lines.get(number, 0) + _count(fields[1], "lcov_line_invalid")
        elif key in {"LF", "LH"}:
            declared[key] = _count(value, "lcov_count_mismatch")
    found, executed = len(lines), sum(count > 0 for count in lines.values())
    if declared.get("LF", found) != found or declared.get("LH", executed) != executed:
        _invalid("lcov_count_mismatch")
    return lines


def lcov_files(
    payload: bytes, *, repository_root: Path, tracked_paths: frozenset[str]
) -> dict[str, dict[str, int]]:
    """Return executable and executed line counts per tracked file from LCOV records."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        _invalid("lcov_invalid", error)
    hits: dict[str, dict[int, int]] = {}
    for name, entries in _lcov_records(text):
        path = repository_file(name, repository_root=repository_root)
        if path not in tracked_paths:
            _invalid("coverage_file_unbound")
        merged = hits.setdefault(path, {})
        for number, count in _lcov_lines(entries).items():
            merged[number] = merged.get(number, 0) + count
    if not hits:
        _invalid("lcov_files_missing")
    return {
        name: {"lines": len(counts), "hit_lines": sum(count > 0 for count in counts.values())}
        for name, counts in hits.items()
    }


@dataclass(frozen=True, slots=True)
class SarifReport:
    """Adverse SARIF observations and the files its runs declare they analyzed."""

    findings: tuple[dict[str, object], ...]
    failures: tuple[str, ...]
    # None when no run lists its artifacts, so the scanned scope is unknown.
    inventory: frozenset[str] | None


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _invalid("sarif_invalid")
    return value


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        _invalid("sarif_invalid")
    return value


def _location(
    location: Mapping[str, object], bases: Mapping[str, object], repository_root: Path
) -> str | None:
    """Resolve a file URI or a base-relative reference inside the repository, if any."""
    uri, base = location.get("uri"), location.get("uriBaseId")
    if not isinstance(uri, str) or not uri:
        return None
    parsed = urlsplit(uri)
    if parsed.scheme == "file":
        native = Path(unquote(parsed.path))
    elif parsed.scheme:
        return None
    else:
        declared = bases.get(base) if isinstance(base, str) else None
        parent = repository_root
        if isinstance(declared, Mapping) and isinstance(declared.get("uri"), str):
            parent = Path(unquote(urlsplit(str(declared["uri"])).path))
        native = parent / unquote(parsed.path)
    try:
        return native.resolve().relative_to(repository_root).as_posix()
    except ValueError:
        return None


def _level(result: Mapping[str, object], rules: list[object]) -> tuple[str, str]:
    """Apply SARIF defaults: a fail result takes its rule's level, then `warning`."""
    kind = result.get("kind", "fail")
    level = result.get("level")
    if level is None:
        index = result.get("ruleIndex")
        rule: object = rules[index] if isinstance(index, int) and 0 <= index < len(rules) else None
        if rule is None:
            rule = next(
                (item for item in rules if _mapping(item).get("id") == result.get("ruleId")), {}
            )
        configured = _mapping(_mapping(rule).get("defaultConfiguration", {})).get("level")
        level = (configured or "warning") if kind == "fail" else "none"
    if kind not in _KINDS or level not in _LEVELS:
        _invalid("sarif_invalid")
    return str(kind), str(level)


def _run_failures(run: Mapping[str, object]) -> list[str]:
    """A failed invocation or an adverse notification about the tool's own run."""
    failures: list[str] = []
    for invocation_value in _sequence(run.get("invocations", [])):
        invocation = _mapping(invocation_value)
        if invocation.get("executionSuccessful") is False:
            failures.append("sarif_execution_failed")
        failures.extend(
            f"sarif_notification:{key}"
            for key in ("toolExecutionNotifications", "toolConfigurationNotifications")
            for notification in _sequence(invocation.get(key, []))
            if _mapping(notification).get("level", "warning") in _ADVERSE
        )
    return failures


def _run_findings(
    run: Mapping[str, object], rules: list[object], bases: Mapping[str, object], root: Path
) -> list[dict[str, object]]:
    """Fail results whose effective level is a warning or an error."""
    findings: list[dict[str, object]] = []
    for result_value in _sequence(run.get("results")):
        result = _mapping(result_value)
        kind, level = _level(result, rules)
        if kind != "fail" or level not in _ADVERSE:
            continue
        locations = (
            _mapping(
                _mapping(_mapping(item).get("physicalLocation", {})).get("artifactLocation", {})
            )
            for item in _sequence(result.get("locations", []))
        )
        findings.append(
            {
                "rule": result.get("ruleId", ""),
                "level": level,
                "message": _mapping(result.get("message", {})).get("text", ""),
                "paths": [
                    path
                    for location in locations
                    if (path := _location(location, bases, root)) is not None
                ],
            }
        )
    return findings


def _run_inventory(
    run: Mapping[str, object], bases: Mapping[str, object], root: Path, tracked: frozenset[str]
) -> set[str] | None:
    """Tracked files a run lists as analyzed; None when it lists no artifacts."""
    if "artifacts" not in run:
        return None
    inventory: set[str] = set()
    for artifact_value in _sequence(run["artifacts"]):
        artifact = _mapping(artifact_value)
        roles = artifact.get("roles")
        if roles is not None and "analysisTarget" not in _sequence(roles):
            continue
        path = _location(_mapping(artifact.get("location", {})), bases, root)
        if path in tracked:
            inventory.add(path)
    return inventory


def sarif_report(
    payload: bytes, *, repository_root: Path, tracked_paths: frozenset[str]
) -> SarifReport:
    """Read SARIF 2.1.0 adverse results, run failures and analyzed artifacts."""
    try:
        document = _mapping(json.loads(payload))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _invalid("sarif_invalid", error)
    runs = _sequence(document.get("runs"))
    if document.get("version") != "2.1.0" or not runs:
        _invalid("sarif_invalid")
    findings: list[dict[str, object]] = []
    failures: list[str] = []
    inventory: set[str] | None = None
    for run_value in runs:
        run = _mapping(run_value)
        driver = _mapping(_mapping(run.get("tool")).get("driver"))
        if not isinstance(driver.get("name"), str) or "results" not in run:
            _invalid("sarif_invalid" if "results" in run else "sarif_results_missing")
        bases = _mapping(run.get("originalUriBaseIds", {}))
        failures.extend(_run_failures(run))
        findings.extend(
            _run_findings(run, _sequence(driver.get("rules", [])), bases, repository_root)
        )
        listed = _run_inventory(run, bases, repository_root, tracked_paths)
        if listed is not None:
            inventory = (inventory or set()) | listed
    return SarifReport(
        tuple(findings), tuple(failures), frozenset(inventory) if inventory is not None else None
    )
