"""Canonical official OpenSpec Change identifier and root grammar."""

from __future__ import annotations

import re
from datetime import date

LOGICAL_CHANGE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TEMPORAL_SUFFIX_PATTERN = re.compile(r"-20\d{6}$")
_ARCHIVED_ROOT_PATTERN = re.compile(
    r"^openspec/changes/archive/(20\d{2}-\d{2}-\d{2})-"
    r"([a-z][a-z0-9]*(?:-[a-z0-9]+)*)$"
)
_CHANGE_ROOT_INVALID = "openspec_change_root_invalid"
OPEN_SPEC_ARCHIVE_ROOT = "openspec/changes/archive"


def logical_change_identifier_issue(identifier: str) -> str:
    """Return the stable validation issue for one logical Change ID."""
    if not LOGICAL_CHANGE_ID_PATTERN.fullmatch(identifier):
        return "invalid"
    if TEMPORAL_SUFFIX_PATTERN.search(identifier):
        return "temporal_suffix"
    return ""


def active_change_root(change: str) -> str:
    """Return the sole active OpenSpec root for one logical Change."""
    if logical_change_identifier_issue(change):
        raise ValueError(_CHANGE_ROOT_INVALID)
    return f"openspec/changes/{change}"


def active_change_scope(change: str) -> str:
    """Return the recursive path projection for one official Change root."""
    return f"{active_change_root(change)}/**"


def archived_change_root(change: str, archived_on: date) -> str:
    """Return the dated immutable OpenSpec root for one logical Change."""
    if logical_change_identifier_issue(change):
        raise ValueError(_CHANGE_ROOT_INVALID)
    return f"{OPEN_SPEC_ARCHIVE_ROOT}/{archived_on.isoformat()}-{change}"


def parse_archived_change_root(root: str) -> tuple[str, date] | None:
    """Parse one exact dated official OpenSpec archive root."""
    archived = _ARCHIVED_ROOT_PATTERN.fullmatch(root)
    if archived is None:
        return None
    try:
        archived_on = date.fromisoformat(archived[1])
    except ValueError:
        return None
    return archived[2], archived_on


def archived_change_root_matches(root: str, change: str) -> bool:
    """Return whether one dated archive root belongs to the requested Change."""
    parsed = parse_archived_change_root(root)
    return parsed is not None and parsed[0] == change
