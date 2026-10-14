"""Prove-stage domain reducers — pure report logic fed by adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.git import tracked_paths
from ethos.contracts.verdict import close_verdict
from ethos.repository.paradigm.report import python_size_gaps
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path


def code_size_report(root: Path) -> dict[str, object]:
    """Project the paradigm's Python size obligation for the gate that still names it."""
    gaps = python_size_gaps(root, tracked_paths(root))
    required = [gap.required_gap for gap in gaps]
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required)),
        "state": "evaluated",
        "required_gaps": required,
        "next_action": gaps[0].repair if gaps else "",
    }


def command_data_validation(
    repo: Path,
    *,
    schema_name: str,
    payload: dict[str, object],
) -> dict[str, object]:
    """Validate a command's data payload against a named schema."""
    validation = validate_schema_instance(schema_name, payload, root=repo)
    return {
        "kind": "schema_validation",
        "target": "data",
        "schema": schema_name,
        "verdict": validation["verdict"],
        "required_gaps": list(cast("list[object]", validation["required_gaps"])),
    }


def workspace_status_validation(repo: Path, payload: dict[str, object]) -> dict[str, object]:
    """Validate a workspace-status payload against its schema."""
    return command_data_validation(
        repo, schema_name="workspace-status.schema.json", payload=payload
    )


def workspace_status_validation_gaps(validation: dict[str, object]) -> tuple[str, ...]:
    """Prefix workspace-status schema gaps for surfacing in required_gaps."""
    return tuple(
        f"workspace_status_schema:{gap}"
        for gap in cast("list[object]", validation["required_gaps"])
    )
