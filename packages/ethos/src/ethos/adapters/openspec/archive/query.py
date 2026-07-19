"""Read-only logical-ID lookup for dated OpenSpec archive carriers."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import Any

from .core import ARCHIVE_NAME_PATTERN

if TYPE_CHECKING:
    from pathlib import Path

LOGICAL_CHANGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ARCHIVE_DATE_PREFIX_LENGTH = len("YYYY-MM-DD-")


def archive_query_report(root: Path, *, logical_id: str) -> dict[str, Any]:
    """Resolve exactly one dated archive from a logical Change ID."""
    archive_root = root / "openspec" / "changes" / "archive"
    matches: list[Path] = []
    if (archive_root / logical_id).is_dir() and ARCHIVE_NAME_PATTERN.fullmatch(logical_id):
        state, gap = "invalid", f"openspec_archive_directory_identifier_not_logical:{logical_id}"
    elif not LOGICAL_CHANGE_ID_PATTERN.fullmatch(logical_id):
        state, gap = "invalid", f"openspec_archive_logical_identifier_invalid:{logical_id}"
    else:
        matches = _matching_archives(archive_root, logical_id)
        state, gap = (
            ("missing", f"openspec_archive_logical_identifier_not_found:{logical_id}")
            if not matches
            else ("ambiguous", f"openspec_archive_logical_identifier_ambiguous:{logical_id}")
            if len(matches) > 1
            else ("resolved", "")
        )
    archive = matches[0] if state == "resolved" else None
    return {
        "ok": not gap,
        "state": state,
        "logical_id": logical_id,
        "archive_root": archive_root.relative_to(root).as_posix(),
        "archive_name": archive.name if archive else "",
        "archive_path": archive.relative_to(root).as_posix() if archive else "",
        "matches": [path.relative_to(root).as_posix() for path in matches],
        "required_gaps": [gap] if gap else [],
    }


def active_change_identifier_gaps(root: Path, identifier: str | None) -> list[str]:
    """Reject a real dated archive directory where an active ID is required."""
    archive = root / "openspec" / "changes" / "archive" / (identifier or "")
    return (
        [f"openspec_active_change_identifier_is_archive_directory:{identifier}"]
        if identifier and archive.is_dir() and ARCHIVE_NAME_PATTERN.fullmatch(identifier)
        else []
    )


def _matching_archives(archive_root: Path, logical_id: str) -> list[Path]:
    if not archive_root.is_dir():
        return []
    return [
        path
        for path in sorted(archive_root.iterdir())
        if path.is_dir()
        and ARCHIVE_NAME_PATTERN.fullmatch(path.name)
        and path.name[ARCHIVE_DATE_PREFIX_LENGTH:] == logical_id
    ]
