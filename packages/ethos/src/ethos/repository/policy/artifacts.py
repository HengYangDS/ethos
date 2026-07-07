"""Generated artifact topology audit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos_core.contracts.generated_artifact_topology import generated_artifact_contract
from ethos_core.contracts.generated_artifact_topology import path_policy_for

if TYPE_CHECKING:
    from pathlib import Path


_PRUNE_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "node_modules",
    }
)


def generated_artifact_topology_report(root: Path) -> dict[str, object]:
    """Report generated artifact placement drift without mutating the repository."""
    allowed_paths: list[str] = []
    denied_paths: list[str] = []
    review_paths: list[str] = []
    review_gaps: list[str] = []
    required_gaps: list[str] = []

    for path in _candidate_paths(root):
        rel = path.relative_to(root).as_posix()
        policy = path_policy_for(rel)
        decision = str(policy["decision"])
        if decision == "allow":
            allowed_paths.append(rel)
        elif decision == "review":
            review_paths.append(rel)
            review_gap = str(policy.get("required_gap") or "")
            if review_gap:
                review_gaps.append(review_gap)
        elif decision == "deny":
            denied_paths.append(rel)
            required_gap = str(policy.get("required_gap") or "")
            if required_gap:
                required_gaps.append(required_gap)

    allowed_paths.sort()
    denied_paths.sort()
    review_paths.sort()
    review_gaps.sort()
    required_gaps.sort()
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "contract": generated_artifact_contract(),
        "summary": {
            "allowed_path_count": len(allowed_paths),
            "denied_path_count": len(denied_paths),
            "review_path_count": len(review_paths),
            "review_gap_count": len(review_gaps),
        },
        "allowed_paths": allowed_paths,
        "denied_paths": denied_paths,
        "review_paths": review_paths,
        "review_gaps": review_gaps,
        "required_gaps": required_gaps,
    }


def _candidate_paths(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in root.rglob("*"):
        if any(part in _PRUNE_DIRS for part in path.relative_to(root).parts):
            continue
        policy = path_policy_for(path.relative_to(root))
        if (path.is_file() and policy["decision"] != "ignore") or (
            path.is_dir()
            and policy["decision"] == "deny"
            and not any(child.is_file() for child in path.rglob("*"))
        ):
            candidates.append(path)
    return candidates
