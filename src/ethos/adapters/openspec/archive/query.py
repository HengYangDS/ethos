"""Read-only logical-ID lookup for dated OpenSpec archive carriers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.openspec.identifiers import archive_name_parts
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from pathlib import Path


def archive_query_report(root: Path, *, logical_id: str) -> dict[str, Any]:
    """Resolve exactly one dated archive from a logical Change ID."""
    archive_root = root / "openspec" / "changes" / "archive"
    matches: list[Path] = []
    if (archive_root / logical_id).is_dir():
        state, gap = "invalid", f"openspec_archive_directory_identifier_not_logical:{logical_id}"
    elif logical_change_identifier_issue(logical_id):
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
    if not identifier:
        return []
    if archive.is_dir():
        return [f"openspec_active_change_identifier_is_archive_directory:{identifier}"]
    return (
        [f"openspec_active_change_identifier_invalid:{identifier}"]
        if logical_change_identifier_issue(identifier)
        else []
    )


def _matching_archives(archive_root: Path, logical_id: str) -> list[Path]:
    if not archive_root.is_dir():
        return []
    return [
        path
        for path in sorted(archive_root.iterdir())
        if path.is_dir()
        and (parts := archive_name_parts(path.name)) is not None
        and parts[1] == logical_id
    ]
