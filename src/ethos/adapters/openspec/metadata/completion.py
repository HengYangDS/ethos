from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.archive.validation import openspec_archive_closeout_report
from ethos.adapters.openspec.governance import openspec_governance_report

if TYPE_CHECKING:
    from pathlib import Path


class CompletedActiveChangesEvidence(NamedTuple):
    """Lifecycle projections returned with completed-active change review."""

    active_lifecycle: dict[str, Any]
    archive_closeout: dict[str, Any]


def completed_active_changes_report(root: Path) -> dict[str, Any]:
    """Report active OpenSpec changes that are complete but not archived."""
    if not (root / "openspec").exists():
        return completed_active_changes_payload(
            root,
            completed_changes=[],
            required_gaps=[],
            list_result={},
            evidence=CompletedActiveChangesEvidence(
                {"ok": True, "state": "not_applicable", "required_gaps": []},
                {},
            ),
        )
    base_command = openspec_cli.openspec_base_command()
    if base_command is None:
        return completed_active_changes_payload(
            root,
            completed_changes=[],
            required_gaps=["openspec_official_cli_missing"],
            list_result={},
            evidence=CompletedActiveChangesEvidence(
                {"ok": False, "state": "unavailable", "required_gaps": []},
                {},
            ),
        )

    list_result = openspec_cli.run_json(root, base_command, ("list", "--json"))
    required_gaps: list[str] = []
    if list_result["exit_code"] != 0:
        required_gaps.append("openspec_list_failed")
    if list_result["parse_error"]:
        required_gaps.append("openspec_list_json_parse_failed")
    completed_changes = [] if required_gaps else completed_active_change_names(list_result["json"])
    required_gaps.extend(
        f"openspec_completed_change_unarchived:{name}" for name in completed_changes
    )
    active_lifecycle = (
        openspec_governance_report(root, lifecycle=True)
        if not required_gaps
        else {"ok": False, "state": "not_run", "required_gaps": []}
    )
    required_gaps.extend(str(gap) for gap in active_lifecycle.get("required_gaps", []))
    archive_closeout = openspec_archive_closeout_report(root)
    required_gaps.extend(str(gap) for gap in archive_closeout["required_gaps"])
    return completed_active_changes_payload(
        root,
        completed_changes=completed_changes,
        required_gaps=required_gaps,
        list_result=list_result,
        evidence=CompletedActiveChangesEvidence(active_lifecycle, archive_closeout),
    )


def completed_active_change_names(list_payload: dict[str, Any]) -> list[str]:
    """Return active OpenSpec names whose state is complete."""
    changes = list_payload.get("changes", [])
    if not isinstance(changes, list):
        return []
    completed = []
    for item in changes:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or item.get("state") or "")
        name = str(item.get("name") or item.get("id") or "")
        if name and status in {"complete", "completed", "done"}:
            completed.append(name)
    return completed


def completed_active_changes_payload(
    root: Path,
    *,
    completed_changes: list[str],
    required_gaps: list[str],
    list_result: dict[str, Any],
    evidence: CompletedActiveChangesEvidence,
) -> dict[str, Any]:
    """Build the completed-active OpenSpec read model payload."""
    return {
        "ok": not required_gaps,
        "state": "blocked" if required_gaps else "clean",
        "root": root.as_posix(),
        "completed_changes": completed_changes,
        "active_lifecycle": evidence.active_lifecycle,
        "archive_closeout": evidence.archive_closeout
        or {
            "ok": True,
            "state": "clean",
            "archive_root": "",
            "archives": [],
            "issues": [],
            "required_gaps": [],
            "summary": {"archive_count": 0, "issue_count": 0},
        },
        "required_gaps": required_gaps,
        "commands": {"list": list_result} if list_result else {},
    }
