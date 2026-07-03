"""Prove-stage domain reducers — pure report logic fed by adapters.

The code-size report is a pure reducer over (policy, tracked files, per-file
effective LOC): it takes the policy (loaded by adapters.config), the file list
(adapters.git), and the metric (kernel measure), and derives the gate verdict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos_core.measure import effective_code_lines

from ethos.adapters import git as _git
from ethos.adapters.config import code_size_policy

if TYPE_CHECKING:
    from pathlib import Path


def code_size_report(root: Path) -> dict[str, object]:
    """Derive the code-size gate verdict against the ratchet policy."""
    policy = code_size_policy(root)
    default_limit = int(policy.get("default_effective_max_lines") or 400)
    test_limit = int(policy.get("test_effective_max_lines") or default_limit)
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
        is_test = relative.startswith("tests/") or "/tests/" in relative
        category_limit = test_limit if is_test else default_limit
        limit = exception_limits.get(relative, category_limit)
        ok = effective <= limit
        records.append(
            {
                "path": relative,
                "effective_lines": effective,
                "limit": limit,
                "category": "test" if is_test else "product",
                "exception": relative in exception_limits,
                "ok": ok,
            }
        )
        if not ok:
            gaps.append(f"code_size_exceeded:{relative}:{effective}>{limit}")
    return {
        "ok": not gaps,
        "default_effective_max_lines": default_limit,
        "test_effective_max_lines": test_limit,
        "required_gaps": gaps,
        "files": records,
    }
