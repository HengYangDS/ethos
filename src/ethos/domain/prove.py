"""Prove-stage domain reducers — pure report logic fed by adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path


def workspace_status_validation(repo: Path, payload: dict[str, object]) -> dict[str, object]:
    """Validate a workspace-status payload against its schema."""
    schema_name = "workspace-status.schema.json"
    validation = validate_schema_instance(schema_name, payload, root=repo)
    return {
        "kind": "schema_validation",
        "target": "data",
        "schema": schema_name,
        "verdict": validation["verdict"],
        "required_gaps": list(validation["required_gaps"]),
    }


def workspace_status_validation_gaps(validation: dict[str, object]) -> tuple[str, ...]:
    """Prefix workspace-status schema gaps for surfacing in required_gaps."""
    return tuple(
        f"workspace_status_schema:{gap}"
        for gap in cast("list[object]", validation["required_gaps"])
    )
