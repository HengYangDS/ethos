"""Prove-stage domain reducers — pure report logic fed by adapters.

The code-size report is a pure reducer over (role-based policy, tracked files,
per-file effective LOC): it classifies each file into a role (surface / test /
logic), applies that role's limit (capped by a global hard ceiling), and derives
the gate verdict. Policy is loaded by adapters.config, the file list by
adapters.git, the metric by the kernel measure.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

from ethos.adapters import git as _git
from ethos.adapters.config import code_size_policy
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.measure import effective_code_lines

if TYPE_CHECKING:
    from pathlib import Path


def _role_for(relative: str, surface_globs: tuple[str, ...]) -> str:
    """Classify a tracked file into its size-policy role."""
    if relative.startswith("tests/") or "/tests/" in relative:
        return "test"
    if any(fnmatch.fnmatchcase(relative, pattern) for pattern in surface_globs):
        return "surface"
    return "logic"


def code_size_report(root: Path) -> dict[str, object]:
    """Derive the code-size gate verdict against the role-based ratchet policy."""
    policy = code_size_policy(root)
    default_limit = int(policy.get("default_effective_max_lines") or 400)
    test_limit = int(policy.get("test_effective_max_lines") or default_limit)
    surface_limit = int(policy.get("surface_effective_max_lines") or default_limit)
    global_hard = int(policy.get("global_hard_effective_max_lines") or 0)
    surface_globs = tuple(
        str(pattern) for pattern in policy.get("surface_path_globs", []) if pattern
    )
    role_limits = {"test": test_limit, "surface": surface_limit, "logic": default_limit}
    exception_limits = {
        str(item.get("path")): int(item.get("effective_max_lines") or default_limit)
        for item in policy.get("exception", [])
        if isinstance(item, dict) and item.get("path")
    }
    records: list[dict[str, object]] = []
    gaps: list[str] = []
    for relative in _git.git_files(root, "*.py"):
        path = root / relative
        effective = effective_code_lines(path)
        role = _role_for(relative, surface_globs)
        if relative in exception_limits:
            # An explicit ratchet exception is known, tracked, shrinking debt — it
            # is allowed above the global ceiling until it dissolves. It may only
            # shrink (pinned to current size), so it still converges downward.
            limit = exception_limits[relative]
        else:
            # Role default, capped by the global hard ceiling so no role label buys
            # unbounded growth.
            role_limit = role_limits[role]
            limit = min(role_limit, global_hard) if global_hard else role_limit
        ok = effective <= limit
        records.append(
            {
                "path": relative,
                "effective_lines": effective,
                "limit": limit,
                "role": role,
                "category": "test" if role == "test" else "product",
                "exception": relative in exception_limits,
                "ok": ok,
            }
        )
        if not ok:
            gaps.append(f"code_size_exceeded:{relative}:{effective}>{limit}")
    return {
        "ok": not gaps,
        "default_effective_max_lines": default_limit,
        "surface_effective_max_lines": surface_limit,
        "test_effective_max_lines": test_limit,
        "global_hard_effective_max_lines": global_hard,
        "required_gaps": gaps,
        "files": records,
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
        "ok": bool(validation["ok"]),
        "required_gaps": list(validation["required_gaps"]),
    }


def workspace_status_validation(repo: Path, payload: dict[str, object]) -> dict[str, object]:
    """Validate a workspace-status payload against its schema."""
    return command_data_validation(
        repo, schema_name="workspace-status.schema.json", payload=payload
    )


def workspace_status_validation_gaps(validation: dict[str, object]) -> tuple[str, ...]:
    """Prefix workspace-status schema gaps for surfacing in required_gaps."""
    return tuple(f"workspace_status_schema:{gap}" for gap in validation["required_gaps"])
