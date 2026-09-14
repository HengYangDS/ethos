"""Profile-conditioned OpenSpec lifecycle adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.lifecycle.report import official_change_rows

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


def load_profile_commitment(
    root: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
) -> Commitment:
    """Compile the selected official OpenSpec Change into a Commitment."""
    if not openspec_profile_enabled(root, tree_ref=tree_ref):
        msg = "openspec_profile_not_enabled"
        raise ValueError(msg)
    return load_openspec_commitment(root, change_id=change_id, tree_ref=tree_ref)


def active_change_progress_report(root: Path) -> dict[str, object]:
    """Observe official progress without making archive a source prerequisite."""
    if not openspec_profile_enabled(root):
        return {
            "verdict": "pass",
            "state": "not_applicable",
            "root": root.resolve().as_posix(),
            "completed_changes": [],
            "changes": [],
            "required_gaps": [],
            "commands": {},
        }
    base_command = openspec_cli.openspec_base_command()
    if base_command is None:
        required_gaps = ["openspec_official_cli_missing"]
        list_result: dict[str, Any] = {}
        completed_changes: list[str] = []
        rows = None
    else:
        list_result = openspec_cli.run_json(root, base_command, ("list", "--json"))
        required_gaps = [
            gap
            for blocked, gap in (
                (list_result["exit_code"] != 0, "openspec_list_failed"),
                (bool(list_result["parse_error"]), "openspec_list_json_parse_failed"),
            )
            if blocked
        ]
        rows = None if required_gaps else official_change_rows(list_result["json"])
        if rows is None and not required_gaps:
            required_gaps.append("openspec_list_unreadable")
        completed_changes = (
            [] if rows is None else [item["name"] for item in rows if item["status"] == "complete"]
        )
    return {
        "verdict": "block" if required_gaps else "pass",
        "state": "blocked" if required_gaps else "observed",
        "root": root.resolve().as_posix(),
        "completed_changes": completed_changes,
        "changes": rows or [],
        "required_gaps": required_gaps,
        "commands": {"list": list_result} if list_result else {},
    }
