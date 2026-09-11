"""Prove-stage domain reducers — pure report logic fed by adapters.

The code-size report is a pure reducer over (role-based policy, tracked files,
per-file effective LOC): it classifies each file into a role (surface / test /
logic), applies its declared limit, and derives the gate verdict. Rules own
strict optional policy compilation, Git supplies inventory, and measure owns
the shared metric. Invalid policy or syntax never becomes a smaller measurement.
"""

from __future__ import annotations

import fnmatch
import shlex
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git_adapter
from ethos.measure import effective_code_lines
from ethos.repository.policy.rules.config import code_size_policy
from ethos.repository.policy.rules.config import load_rules_config
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path


def _role_for(relative: str, surface_globs: list[str]) -> str:
    """Classify a tracked file into its size-policy role."""
    if relative.startswith("tests/") or "/tests/" in relative:
        return "test"
    if any(fnmatch.fnmatchcase(relative, pattern) for pattern in surface_globs):
        return "surface"
    return "logic"


def code_size_report(root: Path) -> dict[str, object]:
    """Derive the code-size gate verdict against the role-based limits."""
    try:
        policy = code_size_policy(load_rules_config(root))
    except (ValueError, TypeError, OSError) as error:
        state = "policy_unavailable" if isinstance(error, OSError) else "policy_invalid"
        return {
            "verdict": "unknown" if isinstance(error, OSError) else "block",
            "state": state,
            "files": [],
            "required_gaps": [f"code_size_{state}"],
            "errors": [{"path": ".ethos/rules.toml", "reason": str(error)}],
            "next_action": _size_repair_command(root, ".ethos/rules.toml"),
        }
    if policy is None:
        return {
            "verdict": "pass",
            "state": "not_configured",
            "files": [],
            "required_gaps": [],
            "next_action": "",
        }
    default_limit = policy.default_effective_max_lines
    test_limit = policy.test_effective_max_lines or default_limit
    surface_limit = policy.surface_effective_max_lines or default_limit
    role_limits = {"test": test_limit, "surface": surface_limit, "logic": default_limit}
    records: list[dict[str, object]] = []
    gaps: list[str] = []
    errors: list[dict[str, str]] = []
    verdict = "pass"
    repair_path = ""
    for relative in git_adapter.git_files(root, "*.py"):
        path = root / relative
        if not path.exists():
            continue
        try:
            effective = effective_code_lines(path)
        except (SyntaxError, UnicodeError, OSError) as error:
            invalid = isinstance(error, (SyntaxError, UnicodeError))
            verdict = "block" if invalid or verdict == "block" else "unknown"
            gaps.append(f"code_size_source_{'invalid' if invalid else 'unavailable'}:{relative}")
            errors.append({"path": relative, "reason": str(error)})
            repair_path = repair_path or relative
            continue
        role = _role_for(relative, policy.surface_path_globs)
        limit = role_limits[role]
        within_limit = effective <= limit
        records.append(
            {
                "path": relative,
                "effective_lines": effective,
                "limit": limit,
                "role": role,
                "category": "test" if role == "test" else "product",
                "within_limit": within_limit,
            }
        )
        if not within_limit:
            verdict = "block"
            gaps.append(f"code_size_exceeded:{relative}:{effective}>{limit}")
            repair_path = repair_path or relative
    return {
        "verdict": verdict,
        "state": "evaluated",
        "default_effective_max_lines": default_limit,
        "surface_effective_max_lines": surface_limit,
        "test_effective_max_lines": test_limit,
        "required_gaps": gaps,
        "errors": errors,
        "next_action": _size_repair_command(root, repair_path) if repair_path else "",
        "files": records,
    }


def _size_repair_command(root: Path, relative: str) -> str:
    """Derive admission for the exact failed carrier, not permission to edit it."""
    return shlex.join(
        [
            "ethos",
            "lane",
            "prewrite",
            relative,
            "--root",
            str(root),
            "--editor-root",
            str(root),
            "--require-editor-root",
            "--json",
        ]
    )


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
