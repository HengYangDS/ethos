"""Current and historical lane-resolution record root locations."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.adapters.mutation.resolution._shared import record_destination_safe
from ethos_core.contracts.branch.roles import load_branch_role_policy

_CURRENT_RECORD_ROOT = Path("recovery/lane-resolution-v2")
_HISTORICAL_RECORD_ROOT = Path("recovery/lane-resolution")
_WORKTREE_HISTORY_ROOT = Path("build/artifacts/lane-resolution")
_CONTROL_ROOT_UNAVAILABLE = "lane_resolution_accepted_control_root_unavailable"


def accepted_control_root(root: Path) -> Path:
    """Return the registered checkout for the configured accepted branch."""
    primary_root = _primary_control_root(root)
    accepted_ref = f"refs/heads/{load_branch_role_policy(primary_root).accepted_branch}"
    accepted_head = _git_output(primary_root, "rev-parse", "--verify", accepted_ref)
    if not accepted_head:
        raise ValueError(_CONTROL_ROOT_UNAVAILABLE)
    for current in _registered_worktrees(primary_root):
        if current.get("branch") != accepted_ref:
            continue
        candidate = Path(current.get("worktree", "")).resolve()
        if candidate.is_dir() and _git_output(candidate, "rev-parse", "HEAD") == accepted_head:
            return candidate
    raise ValueError(_CONTROL_ROOT_UNAVAILABLE)


def current_record_root(root: Path) -> Path:
    """Return the sole versioned root authorized for current records."""
    control_root = accepted_control_root(root)
    return control_root.parent / f"{control_root.name}-records" / _CURRENT_RECORD_ROOT


def historical_record_roots(root: Path) -> tuple[Path, ...]:
    """Return deduplicated read-only predecessor record locations."""
    control_root = accepted_control_root(root)
    candidates = (
        control_root.parent / f"{control_root.name}-records" / _HISTORICAL_RECORD_ROOT,
        *(
            Path(record["worktree"]).absolute() / _WORKTREE_HISTORY_ROOT
            for record in _registered_worktrees(root)
            if record.get("worktree") and Path(record["worktree"]).is_dir()
        ),
    )
    return tuple(dict.fromkeys(path.absolute() for path in candidates))


def canonical_record_path(root: Path, path: Path) -> bool:
    """Return whether a decision is a direct JSON child of its current category."""
    try:
        decision_root = current_record_root(root) / "decisions"
    except ValueError:
        return False
    candidate = path.absolute()
    return (
        candidate.parent == decision_root.absolute()
        and candidate.suffix == ".json"
        and record_destination_safe(decision_root, candidate)
    )


def _primary_control_root(root: Path) -> Path:
    common_raw = _git_output(root, "rev-parse", "--git-common-dir")
    if not common_raw:
        raise ValueError(_CONTROL_ROOT_UNAVAILABLE)
    common = Path(common_raw)
    if not common.is_absolute():
        common = root / common
    primary = common.resolve().parent
    if not primary.is_dir():
        raise ValueError(_CONTROL_ROOT_UNAVAILABLE)
    return primary


def _registered_worktrees(root: Path) -> list[dict[str, str]]:
    completed = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise ValueError(_CONTROL_ROOT_UNAVAILABLE)
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in [*completed.stdout.splitlines(), ""]:
        if line:
            key, _, value = line.partition(" ")
            current[key] = value
            continue
        if current:
            records.append(current)
        current = {}
    return records


def _git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""
