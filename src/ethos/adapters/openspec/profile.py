"""Profile-conditioned OpenSpec lifecycle adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.lifecycle.report import official_change_rows
from ethos.adapters.openspec.observation import (
    protected_branch_active_change_required_gaps as observed_protected_branch_gaps,
)
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


def load_profile_commitment(
    root: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
) -> Commitment:
    """Load the selected active change or the repository base Commitment."""
    if openspec_profile_enabled(root, tree_ref=tree_ref):
        try:
            return load_openspec_commitment(root, change_id=change_id, tree_ref=tree_ref)
        except ValueError as error:
            if change_id is not None or str(error) != "commitment_missing":
                raise
    return load_commitment(root, change_id=change_id, tree_ref=tree_ref)


def load_work_lane_commitment(
    root: Path,
    *,
    lease: dict[str, object],
    change_id: str | None = None,
) -> Commitment:
    """Load current intent or the exact archived carrier bound by the Lease."""
    prior = load_lease_bound_commitment(root, lease=lease)
    selected_change = change_id
    try:
        return load_profile_commitment(root, change_id=selected_change)
    except ValueError as error:
        expected = prior.id.removeprefix("change:") if change_id is None else change_id
        if (
            str(error) not in {"commitment_missing", f"commitment_missing:{expected}"}
            or prior.id != f"change:{expected}"
        ):
            raise
        return prior


def completed_active_changes_report(root: Path) -> dict[str, object]:
    """Return completion facts only when the OpenSpec profile adapter is enabled."""
    if not openspec_profile_enabled(root):
        return {
            "verdict": "pass",
            "state": "not_applicable",
            "root": root.resolve().as_posix(),
            "completed_changes": [],
            "required_gaps": [],
            "commands": {},
        }
    base_command = openspec_cli.openspec_base_command()
    if base_command is None:
        required_gaps = ["openspec_official_cli_missing"]
        list_result: dict[str, Any] = {}
        completed_changes: list[str] = []
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
        required_gaps.extend(
            f"openspec_completed_change_unarchived:{name}" for name in completed_changes
        )
    return {
        "verdict": "block" if required_gaps else "pass",
        "state": "blocked" if required_gaps else "clean",
        "root": root.resolve().as_posix(),
        "completed_changes": completed_changes,
        "required_gaps": required_gaps,
        "commands": {"list": list_result} if list_result else {},
    }


def active_change_names(root: Path) -> list[str]:
    """Discover active changes only inside the selected OpenSpec profile."""
    repo = root.parent if root.name == "openspec" else root
    if not openspec_profile_enabled(repo):
        return []
    changes = repo / "openspec" / "changes"
    if not changes.is_dir():
        return []
    return [
        path.name for path in sorted(changes.iterdir()) if path.is_dir() and path.name != "archive"
    ]


def protected_branch_active_change_required_gaps(root: Path, *, current_branch: str) -> list[str]:
    """Return protected-branch residue only for the selected OpenSpec profile."""
    if not openspec_profile_enabled(root):
        return []
    return observed_protected_branch_gaps(
        root,
        current_branch=current_branch,
    )
