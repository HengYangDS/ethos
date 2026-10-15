"""Preserve official OpenSpec validation meaning for gates and exact repair."""

from __future__ import annotations

from pathlib import Path
from pathlib import PurePosixPath
from stat import S_ISREG
from typing import Any

from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

_INFO_SPEC = "openspec_validation_issue:INFO:spec:"
_FAILED_SPEC = "openspec_validation_failed:spec:"


def validation_items(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Admit one complete official envelope, including additive producer metadata."""
    if not isinstance(payload, dict) or ("items" in payload) == ("itemFindings" in payload):
        return None
    findings = "itemFindings" in payload
    items = payload["itemFindings" if findings else "items"]
    if not isinstance(items, list) or any(not _valid_item(item) for item in items):
        return None
    identities = [(item["type"], item["id"]) for item in items]
    if (
        len(set(identities)) != len(identities)
        or not _valid_summary(payload, items, findings=findings)
        or not _valid_root(payload.get("root"))
    ):
        return None
    if findings:
        report = payload.get("report")
        if not (
            isinstance(report, dict)
            and report.get("kind") == "validation-findings"
            and report.get("version") == "1.0"
            and report.get("scope") in ("all", "changes", "specs", "archived")
            and type(report.get("returnedItems")) is int
            and report["returnedItems"] == len(items)
            and type(report.get("totalItems")) is int
            and report["totalItems"] == payload["summary"]["totals"]["items"]
            and all(item["issues"] for item in items)
        ):
            return None
    elif payload.get("version") != "1.0" or "report" in payload:
        return None
    return items


def _valid_item(item: object) -> bool:
    """Require a unique typed native item and every complete issue record."""
    return (
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and bool(item["id"].strip())
        and item.get("type") in ("change", "spec")
        and isinstance(item.get("valid"), bool)
        and isinstance(item.get("issues"), list)
        and all(
            isinstance(issue, dict)
            and issue.get("level") in ("ERROR", "WARNING", "INFO")
            and isinstance(issue.get("path"), str)
            and isinstance(issue.get("message"), str)
            for issue in item["issues"]
        )
    )


def _valid_counts(value: object) -> bool:
    """One complete nonnegative count triple conserves all item outcomes."""
    return (
        isinstance(value, dict)
        and all(
            type(value.get(key)) is int and value[key] >= 0 for key in ("items", "passed", "failed")
        )
        and value["items"] == value["passed"] + value["failed"]
    )


def _valid_root(root: object) -> bool:
    """Require the original native root record without constraining future sources."""
    return (
        isinstance(root, dict)
        and isinstance(root.get("path"), str)
        and root["path"].strip() == root["path"]
        and bool(root["path"])
        and not any(character in root["path"] for character in ("\0", "\r", "\n"))
        and Path(root["path"]).is_absolute()
        and isinstance(root.get("source"), str)
        and bool(root["source"].strip())
    )


def _valid_summary(payload: dict[str, Any], items: list[dict[str, Any]], *, findings: bool) -> bool:
    """Full counts are exact; findings conserve all failures and silent valid items."""
    summary = payload.get("summary")
    if not isinstance(summary, dict) or not _valid_counts(summary.get("totals")):
        return False
    totals, by_type = summary["totals"], summary.get("byType")
    if (
        not isinstance(by_type, dict)
        or set(by_type) - {"change", "spec"}
        or any(not _valid_counts(value) for value in by_type.values())
        or any(item["type"] not in by_type for item in items)
        or any(
            sum(value[key] for value in by_type.values()) != totals[key]
            for key in ("items", "passed", "failed")
        )
    ):
        return False
    for kind, counts in by_type.items():
        rows = [item for item in items if item["type"] == kind]
        passed = sum(item["valid"] for item in rows)
        observed = {"items": len(rows), "passed": passed, "failed": len(rows) - passed}
        if any(
            observed[key] > counts[key]
            if findings and key != "failed"
            else observed[key] != counts[key]
            for key in observed
        ):
            return False
    return True


def _valid_issue_gaps(item: dict[str, Any]) -> list[str]:
    """Keep canonical spec guidance strict without rejecting normal Change INFO."""
    return [
        f"openspec_validation_issue:{issue['level']}:"
        f"{item['type']}:{item['id']}:{issue['path'] or 'root'}"
        for issue in item["issues"]
        if item["type"] == "spec" or issue["level"] != "INFO"
    ]


def validation_failures(payload: dict[str, Any]) -> list[str]:
    """Project findings only after one complete native envelope is admitted."""
    items = validation_items(payload)
    if items is None:
        return ["openspec_validation_unreadable"]
    gaps: list[str] = []
    for item in items:
        if not item["valid"]:
            gaps.append(f"openspec_validation_failed:{item['type']}:{item['id']}")
        else:
            gaps.extend(_valid_issue_gaps(item))
    return list(dict.fromkeys(gaps))


def validation_result_gaps(result: dict[str, Any]) -> list[str]:
    """Bind complete native validation to its actual execution root and transport."""
    payload = result.get("json")
    gaps = (
        validation_failures(payload)
        if isinstance(payload, dict)
        else ["openspec_validation_unreadable"]
    )
    expected = result.get("cwd")
    observed = payload.get("root") if isinstance(payload, dict) else None
    try:
        same_root = (
            isinstance(expected, str)
            and Path(expected).is_absolute()
            and isinstance(observed, dict)
            and isinstance(observed.get("path"), str)
            and Path(observed["path"]).resolve() == Path(expected).resolve()
        )
    except (OSError, ValueError):
        same_root = False
    if not same_root and "openspec_validation_unreadable" not in gaps:
        gaps.append("openspec_validation_root_mismatch")
    exit_code = result.get("exit_code")
    if type(exit_code) is not int or (exit_code != 0 and not gaps):
        gaps.append("openspec_validate_failed")
    if result.get("parse_error"):
        gaps.append("openspec_validate_json_parse_failed")
    return list(dict.fromkeys(gaps))


def validation_issue_diagnostics(payload: object) -> tuple[dict[str, str], ...]:
    """Carry the blocking native issues of rejected items without reinterpreting them."""
    items = validation_items(payload) if isinstance(payload, dict) else None
    diagnostics: list[dict[str, str]] = []
    for item in items or ():
        if not isinstance(item, dict) or item.get("valid") is not False:
            continue
        issues = item.get("issues")
        diagnostics.extend(
            {
                "kind": "openspec_validation_issue",
                "item": f"{item.get('type')}:{item.get('id')}",
                "severity": str(issue["level"]).lower(),
                "path": str(issue["path"]) or "root",
                "message": str(issue.get("message") or ""),
            }
            for issue in (issues if isinstance(issues, list) else [])
            if isinstance(issue, dict)
            and issue.get("level") in {"ERROR", "WARNING"}
            and isinstance(issue.get("path"), str)
        )
    return tuple(diagnostics)


def valid_canonical_info_capabilities(official: dict[str, object]) -> tuple[str, ...] | None:
    """Bind blocking INFO gaps to unique valid native spec items, not gap text alone."""
    gaps = string_sequence(official.get("required_gaps"))
    expected = tuple(gap for gap in gaps if gap.startswith(_INFO_SPEC))
    if not expected:
        return ()
    commands = official.get("commands")
    validate = commands.get("validate") if isinstance(commands, dict) else None
    payload = validate.get("json") if isinstance(validate, dict) else None
    if not isinstance(validate, dict) or not isinstance(payload, dict):
        return None
    exit_code = validate.get("exit_code")
    if (
        not isinstance(exit_code, int)
        or isinstance(exit_code, bool)
        or exit_code != (1 if any(gap.startswith(_FAILED_SPEC) for gap in gaps) else 0)
        or validate.get("parse_error")
    ):
        return None
    items = validation_items(payload)
    if (
        items is None
        or validation_failures(payload) != gaps
        or any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in items)
    ):
        return None
    spec_ids = [item["id"] for item in items if item["type"] == "spec"]
    if len(spec_ids) != len(set(spec_ids)) or any(
        logical_change_identifier_issue(part)
        for identifier in spec_ids
        for part in identifier.split("/")
    ):
        return None
    return tuple(dict.fromkeys(gap.removeprefix(_INFO_SPEC).split(":", 1)[0] for gap in expected))


def canonical_info_only_capabilities(official: dict[str, object]) -> tuple[str, ...]:
    """Accept only a complete valid-INFO spec observation, never mixed gaps."""
    gaps = string_sequence(official.get("required_gaps"))
    if not gaps or any(not gap.startswith(_INFO_SPEC) for gap in gaps):
        return ()
    return valid_canonical_info_capabilities(official) or ()


def canonical_spec_repair_paths(root: Path, official: dict[str, object]) -> tuple[str, ...]:
    """Map only supported current spec failures to their canonical source files."""
    gaps = string_sequence(official.get("required_gaps"))
    invalid = tuple(gap.removeprefix(_FAILED_SPEC) for gap in gaps if gap.startswith(_FAILED_SPEC))
    info = valid_canonical_info_capabilities(official)
    if info is None:
        return ()
    capabilities = (*invalid, *info)
    if any(
        not capability
        or any(logical_change_identifier_issue(part) for part in capability.split("/"))
        for capability in capabilities
    ):
        return ()
    paths = tuple(
        dict.fromkeys(f"openspec/specs/{capability}/spec.md" for capability in capabilities)
    )
    for capability in info:
        path = root / f"openspec/specs/{capability}/spec.md"
        try:
            if not S_ISREG(path.lstat().st_mode):
                return ()
        except OSError:
            return ()
    return paths


def failed_validation_item(
    official: dict[str, object], *, kind: str, identifier: str
) -> dict[str, object] | None:
    """Return the unique invalid official item for one semantic identity."""
    commands = official.get("commands")
    validate = commands.get("validate") if isinstance(commands, dict) else None
    payload = validate.get("json") if isinstance(validate, dict) else None
    items = validation_items(payload) if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return None
    matching = [
        item
        for item in items
        if isinstance(item, dict)
        if item.get("type") == kind and item.get("id") == identifier and item.get("valid") is False
    ]
    return matching[0] if len(matching) == 1 else None


def strict_blocking_issue_paths(item: dict[str, object] | None) -> tuple[str, ...] | None:
    """Return file paths from ERROR/WARNING issues while ignoring INFO guidance."""
    issues = item.get("issues") if item is not None else None
    if not isinstance(issues, list) or not issues:
        return None
    paths: list[str] = []
    for issue in issues:
        if not isinstance(issue, dict):
            return None
        level = issue.get("level")
        if level == "INFO":
            continue
        if level not in {"ERROR", "WARNING"}:
            return None
        issue_path = _strict_relative_issue_path(issue.get("path"))
        if issue_path is None:
            return None
        paths.append(issue_path)
    return tuple(paths) or None


def resolved_issue_repairs(
    change_root: str,
    issue_paths: tuple[str, ...],
    official_outputs: set[str],
) -> tuple[str, ...]:
    """Resolve every validator path against the two official path bases."""
    repairs: list[str] = []
    for issue_path in issue_paths:
        candidates = {
            f"{change_root}/{issue_path}",
            f"{change_root}/specs/{issue_path}",
        }
        matches = candidates & official_outputs
        if len(matches) != 1:
            return ()
        repairs.extend(matches)
    return tuple(dict.fromkeys(repairs))


def _strict_relative_issue_path(value: object) -> str | None:
    """Return one canonical POSIX-relative validator path, or fail closed."""
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        return None
    path = PurePosixPath(value)
    canonical = path.as_posix()
    invalid_part = any(part in {"", ".", ".."} for part in path.parts)
    if path.is_absolute() or canonical != value or invalid_part:
        return None
    return canonical


def official_regular_file(path: Path) -> bool:
    """Return whether the exact path is a regular file without following a link."""
    try:
        return S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _inherited_validation_items(
    official: dict[str, object], *, change: str
) -> list[dict[str, Any]] | None:
    """Require complete native status, finding identities and strict-gap equality."""
    commands = official.get("commands")
    status = commands.get("status") if isinstance(commands, dict) else None
    validate = commands.get("validate") if isinstance(commands, dict) else None
    selected = status.get("json") if isinstance(status, dict) else None
    payload = validate.get("json") if isinstance(validate, dict) else None
    if not (
        isinstance(status, dict)
        and status.get("exit_code") == 0
        and not status.get("parse_error")
        and isinstance(selected, dict)
        and selected.get("changeName") == change
        and isinstance(validate, dict)
        and validate.get("exit_code") == 1
        and not validate.get("parse_error")
        and isinstance(payload, dict)
        and set(validation_result_gaps(validate))
        == set(string_sequence(official.get("required_gaps")))
    ):
        return None
    items = validation_items(payload)
    if items is None:
        return None
    identities = [(item["type"], item["id"]) for item in items]
    return (
        items
        if len(set(identities)) == len(identities)
        and any(
            item["type"] == "change" and item["id"] == change and item["valid"] for item in items
        )
        else None
    )


def _inherited_item_repair_paths(
    root: Path, item: dict[str, Any], *, change: str
) -> tuple[str, ...] | None:
    """Resolve one native item's exact unlinked carrier without changing its owner."""
    issue_paths = strict_blocking_issue_paths(item)
    if issue_paths is None:
        return None
    if item["type"] == "spec":
        path = root.resolve() / f"openspec/specs/{item['id']}/spec.md"
        return () if path.resolve() == path and official_regular_file(path) else None
    identifier = item["id"]
    if identifier == change or logical_change_identifier_issue(identifier):
        return None
    directory = active_change_root(identifier)
    outputs = {
        candidate
        for issue_path in issue_paths
        for candidate in (f"{directory}/{issue_path}", f"{directory}/specs/{issue_path}")
        if (target := root.resolve() / candidate).resolve() == target
        and official_regular_file(target)
    }
    return resolved_issue_repairs(directory, issue_paths, outputs) or None


def inherited_validation_repair_paths(
    root: Path, official: dict[str, object], *, change: str
) -> tuple[str, ...] | None:
    """Bind inherited repairs to complete native findings, never a second intent."""
    if not any(
        gap.startswith("openspec_validation_failed:change:")
        for gap in string_sequence(official.get("required_gaps"))
    ):
        return ()
    items = _inherited_validation_items(official, change=change)
    if items is None:
        return None
    repairs: list[str] = []
    for item in items:
        if not item["valid"]:
            paths = _inherited_item_repair_paths(root, item, change=change)
            if paths is None:
                return None
            repairs.extend(paths)
    return tuple(dict.fromkeys(repairs))
