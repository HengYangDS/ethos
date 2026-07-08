from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ethos.repository.openspec.metadata import ALLOWED_OPENSPEC_METADATA_KEYS
from ethos.repository.openspec.metadata import is_relative_to
from ethos.repository.openspec.metadata import read_openspec_metadata

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

ARCHIVE_NAME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")
CHECKBOX_PATTERN = re.compile(r"^\s*-\s+\[([ xX])]")
DELTA_HEADER_PATTERN = re.compile(r"^## (ADDED|MODIFIED|REMOVED|RENAMED) Requirements$")
REQUIRED_ARCHIVE_FILES = ("proposal.md", "design.md", "tasks.md", ".openspec.yaml")


def openspec_archive_closeout_report(root: Path) -> dict[str, Any]:
    """Report archive closeout gaps for OpenSpec archived changes."""
    archive_root = root / "openspec" / "changes" / "archive"
    if not archive_root.is_dir():
        return {
            "ok": True,
            "state": "clean",
            "archive_root": archive_root.relative_to(root).as_posix()
            if is_relative_to(archive_root, root)
            else archive_root.as_posix(),
            "archives": [],
            "issues": [],
            "required_gaps": [],
            "summary": {"archive_count": 0, "issue_count": 0},
        }
    archives = tuple(path for path in sorted(archive_root.iterdir()) if path.is_dir())
    issues: list[dict[str, str]] = []
    for archive in archives:
        issues.extend(archive_closeout_issues(archive, root=root))
    required_gaps = sorted({issue["gap"] for issue in issues})
    return {
        "ok": not required_gaps,
        "state": "blocked" if required_gaps else "clean",
        "archive_root": archive_root.relative_to(root).as_posix(),
        "archives": [path.relative_to(root).as_posix() for path in archives],
        "issues": sorted(issues, key=lambda issue: (issue["gap"], issue["path"])),
        "required_gaps": required_gaps,
        "summary": {
            "archive_count": len(archives),
            "issue_count": len(issues),
        },
    }


def archive_closeout_issues(archive: Path, *, root: Path) -> list[dict[str, str]]:
    """Return per-file closeout issues for one archived OpenSpec change."""
    name = archive.name
    issues: list[dict[str, str]] = []
    if not ARCHIVE_NAME_PATTERN.fullmatch(name):
        issues.append(archive_issue("openspec_archive_name_invalid", archive, name, root=root))
    for filename in REQUIRED_ARCHIVE_FILES:
        path = archive / filename
        if not path.is_file():
            stem = "metadata" if filename == ".openspec.yaml" else path.stem
            issues.append(archive_issue(f"openspec_archive_{stem}_missing", path, name, root=root))
    metadata = archive / ".openspec.yaml"
    if metadata.is_file():
        issues.extend(archive_metadata_issues(metadata, archive_name=name, root=root))
    design = archive / "design.md"
    if design.is_file() and not design.read_text(encoding="utf-8").strip():
        issues.append(archive_issue("openspec_archive_design_empty", design, name, root=root))
    tasks = archive / "tasks.md"
    if tasks.is_file():
        issues.extend(archive_task_issues(tasks, archive_name=name, root=root))
    issues.extend(archive_delta_issues(archive / "specs", archive_name=name, root=root))
    return issues


def archive_metadata_issues(
    path: Path,
    *,
    archive_name: str,
    root: Path,
) -> list[dict[str, str]]:
    """Return metadata closeout issues for one archived OpenSpec change."""
    metadata = read_openspec_metadata(path)
    issues: list[dict[str, str]] = []
    for key in sorted(set(metadata) - ALLOWED_OPENSPEC_METADATA_KEYS):
        issues.append(
            archive_issue(
                f"openspec_archive_metadata_key_unsupported:{key}",
                path,
                archive_name,
                root=root,
            )
        )
    if metadata.get("schema") != "spec-driven":
        issues.append(
            archive_issue(
                "openspec_archive_metadata_schema_invalid",
                path,
                archive_name,
                root=root,
            )
        )
    created = metadata.get("created", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", created):
        issues.append(
            archive_issue(
                "openspec_archive_metadata_created_invalid",
                path,
                archive_name,
                root=root,
            )
        )
    elif ARCHIVE_NAME_PATTERN.fullmatch(archive_name) and created > archive_name[:10]:
        issues.append(
            archive_issue(
                "openspec_archive_metadata_created_after_archive",
                path,
                archive_name,
                root=root,
            )
        )
    return issues


def archive_task_issues(
    path: Path,
    *,
    archive_name: str,
    root: Path,
) -> list[dict[str, str]]:
    """Return task-list closeout issues for one archived OpenSpec change."""
    marks = [
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := CHECKBOX_PATTERN.match(line))
    ]
    issues: list[dict[str, str]] = []
    if not marks:
        issues.append(
            archive_issue(
                "openspec_archive_tasks_no_checkboxes",
                path,
                archive_name,
                root=root,
            )
        )
    if any(mark == " " for mark in marks):
        issues.append(
            archive_issue(
                "openspec_archive_tasks_incomplete",
                path,
                archive_name,
                root=root,
            )
        )
    return issues


def archive_delta_issues(
    specs_root: Path,
    *,
    archive_name: str,
    root: Path,
) -> list[dict[str, str]]:
    """Return delta-spec closeout issues for one archived OpenSpec change."""
    if not specs_root.is_dir():
        return [
            archive_issue(
                "openspec_archive_delta_specs_missing",
                specs_root,
                archive_name,
                root=root,
            )
        ]
    spec_paths = tuple(sorted(specs_root.glob("*/spec.md")))
    if not spec_paths:
        return [
            archive_issue(
                "openspec_archive_delta_specs_missing",
                specs_root,
                archive_name,
                root=root,
            )
        ]
    issues: list[dict[str, str]] = []
    for path in spec_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        if not any(DELTA_HEADER_PATTERN.fullmatch(line) for line in lines):
            issues.append(
                archive_issue(
                    "openspec_archive_delta_header_missing",
                    path,
                    archive_name,
                    root=root,
                )
            )
        if not any(line.startswith("### Requirement:") for line in lines):
            issues.append(
                archive_issue(
                    "openspec_archive_delta_requirement_missing",
                    path,
                    archive_name,
                    root=root,
                )
            )
        if not any(line.startswith("#### Scenario:") for line in lines):
            issues.append(
                archive_issue(
                    "openspec_archive_delta_scenario_missing",
                    path,
                    archive_name,
                    root=root,
                )
            )
    return issues


def archive_issue(code: str, path: Path, archive_name: str, *, root: Path) -> dict[str, str]:
    """Build one archive closeout issue payload."""
    return {
        "archive": archive_name,
        "code": code,
        "gap": f"{code}:{archive_name}",
        "path": (
            path.relative_to(root).as_posix() if is_relative_to(path, root) else path.as_posix()
        ),
    }
