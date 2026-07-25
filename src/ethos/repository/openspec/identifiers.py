"""Canonical OpenSpec Change and archive identifier grammar."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

LOGICAL_CHANGE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
ARCHIVE_NAME_PATTERN = re.compile(
    r"^(?P<archive_date>\d{4}-\d{2}-\d{2})-(?P<logical_id>[a-z][a-z0-9]*(?:-[a-z0-9]+)*)$"
)
TEMPORAL_SUFFIX_PATTERN = re.compile(r"-20\d{6}$")


def logical_change_identifier_issue(identifier: str) -> str:
    """Return the stable validation issue for one logical Change ID."""
    if not LOGICAL_CHANGE_ID_PATTERN.fullmatch(identifier):
        return "invalid"
    if TEMPORAL_SUFFIX_PATTERN.search(identifier):
        return "temporal_suffix"
    return ""


def is_logical_change_identifier(identifier: str) -> bool:
    """Return whether an identifier is a date-free lower-kebab Change ID."""
    return not logical_change_identifier_issue(identifier)


def archive_name_parts(name: str) -> tuple[str, str] | None:
    """Return archive date and logical ID only for the canonical archive form."""
    match = ARCHIVE_NAME_PATTERN.fullmatch(name)
    if match is None:
        return None
    logical_id = match.group("logical_id")
    if not is_logical_change_identifier(logical_id):
        return None
    return match.group("archive_date"), logical_id


def archive_identity_gaps(names: Iterable[str]) -> list[str]:
    """Return canonical-name and exact-one logical-ID gaps for archive names."""
    by_logical_id: dict[str, list[str]] = {}
    gaps: list[str] = []
    for name in names:
        parts = archive_name_parts(name)
        if parts is None:
            gaps.append(f"openspec_archive_name_invalid:{name}")
            continue
        by_logical_id.setdefault(parts[1], []).append(name)
    gaps.extend(
        f"openspec_archive_logical_identifier_ambiguous:{logical_id}"
        for logical_id, matches in sorted(by_logical_id.items())
        if len(matches) > 1
    )
    return sorted(gaps)
