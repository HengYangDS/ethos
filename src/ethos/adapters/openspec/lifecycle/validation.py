"""Preserve official OpenSpec validation meaning for gates and exact repair."""

from __future__ import annotations

from stat import S_ISREG
from typing import TYPE_CHECKING
from typing import Any

from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

_INFO_SPEC = "openspec_validation_issue:INFO:spec:"
_FAILED_SPEC = "openspec_validation_failed:spec:"

if TYPE_CHECKING:
    from pathlib import Path


def validation_items(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Select exactly one supported official validation envelope."""
    if "items" in payload and set(payload) <= {"items", "summary", "version", "root"}:
        items = payload["items"]
    elif "itemFindings" in payload and set(payload) <= {
        "report",
        "itemFindings",
        "summary",
        "root",
    }:
        report = payload.get("report")
        items = payload["itemFindings"]
        if not (
            isinstance(report, dict)
            and report.get("kind") == "validation-findings"
            and report.get("version") == "1.0"
            and isinstance(report.get("returnedItems"), int)
            and not isinstance(report["returnedItems"], bool)
            and isinstance(report.get("totalItems"), int)
            and not isinstance(report["totalItems"], bool)
            and 0 <= report["returnedItems"] <= report["totalItems"]
            and isinstance(items, list)
            and len(items) == report["returnedItems"]
        ):
            return None
    else:
        return None
    return items if isinstance(items, list) else None


def _valid_issue_gaps(item: dict[str, Any]) -> list[str]:
    """Keep canonical spec guidance strict without rejecting normal Change INFO."""
    issues = item.get("issues", [])
    if not isinstance(issues, list):
        return ["openspec_validation_unreadable"]
    gaps: list[str] = []
    for issue in issues:
        if (
            not isinstance(issue, dict)
            or issue.get("level") not in {"ERROR", "WARNING", "INFO"}
            or not isinstance(issue.get("path"), str)
        ):
            gaps.append("openspec_validation_unreadable")
        elif item["type"] == "spec" or issue["level"] != "INFO":
            gaps.append(
                f"openspec_validation_issue:{issue['level']}:"
                f"{item['type']}:{item['id']}:{issue['path'] or 'root'}"
            )
    return gaps


def validation_failures(payload: dict[str, Any]) -> list[str]:
    """Admit native validity and issue content from one declared report envelope."""
    items = validation_items(payload)
    if items is None:
        return ["openspec_validation_unreadable"]
    gaps: list[str] = []
    for item in items:
        if not (
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and item["id"].strip()
            and item.get("type") in ("change", "spec")
            and isinstance(item.get("valid"), bool)
        ):
            gaps.append("openspec_validation_unreadable")
        elif not item["valid"]:
            gaps.append(f"openspec_validation_failed:{item['type']}:{item['id']}")
        else:
            gaps.extend(_valid_issue_gaps(item))
    return list(dict.fromkeys(gaps))


def validation_result_gaps(result: dict[str, Any]) -> list[str]:
    """Combine native validation content, exit and transport at one boundary."""
    gaps = validation_failures(result["json"])
    if result["exit_code"] != 0 and not gaps:
        gaps.append("openspec_validate_failed")
    if result["parse_error"]:
        gaps.append("openspec_validate_json_parse_failed")
    return gaps


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
