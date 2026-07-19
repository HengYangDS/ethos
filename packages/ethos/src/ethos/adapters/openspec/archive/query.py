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
    base: dict[str, Any] = {
        "logical_id": logical_id,
        "archive_root": archive_root.relative_to(root).as_posix(),
        "archive_name": "",
        "archive_path": "",
        "matches": [],
    }
    if (archive_root / logical_id).is_dir() and ARCHIVE_NAME_PATTERN.fullmatch(logical_id):
        return _blocked(
            base,
            state="invalid",
            gap=f"openspec_archive_directory_identifier_not_logical:{logical_id}",
        )
    if not LOGICAL_CHANGE_ID_PATTERN.fullmatch(logical_id):
        return _blocked(
            base,
            state="invalid",
            gap=f"openspec_archive_logical_identifier_invalid:{logical_id}",
        )
    matches = _matching_archives(archive_root, logical_id)
    base["matches"] = [path.relative_to(root).as_posix() for path in matches]
    if not matches:
        return _blocked(
            base,
            state="missing",
            gap=f"openspec_archive_logical_identifier_not_found:{logical_id}",
        )
    if len(matches) > 1:
        return _blocked(
            base,
            state="ambiguous",
            gap=f"openspec_archive_logical_identifier_ambiguous:{logical_id}",
        )
    archive = matches[0]
    return {
        "ok": True,
        "state": "resolved",
        **base,
        "archive_name": archive.name,
        "archive_path": archive.relative_to(root).as_posix(),
        "required_gaps": [],
    }


def active_change_identifier_gaps(root: Path, identifier: str | None) -> list[str]:
    """Reject a real dated archive directory where an active ID is required."""
    if not identifier:
        return []
    archive = root / "openspec" / "changes" / "archive" / identifier
    if archive.is_dir() and ARCHIVE_NAME_PATTERN.fullmatch(identifier):
        return [f"openspec_active_change_identifier_is_archive_directory:{identifier}"]
    return []


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


def _blocked(base: dict[str, Any], *, state: str, gap: str) -> dict[str, Any]:
    return {"ok": False, "state": state, **base, "required_gaps": [gap]}
