"""Native carrier observation for linked Work Lane retirement."""

from __future__ import annotations

from pathlib import Path

from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database


def output(root: Path, *args: str) -> str | None:
    """Return stdout for one successful read-only Git observation."""
    completed = run_git(root, *args, check=False)
    return completed.stdout.rstrip("\n") if completed.returncode == 0 else None


def ref_outcome(root: Path, branch: str, expected: str) -> str:
    """Classify one branch ref against its expected retirement prestate."""
    try:
        observed = run_git(
            root,
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/heads/{branch}",
            check=False,
        )
    except OSError:
        return "unavailable"
    if observed.returncode == 0:
        return "expected" if observed.stdout.strip() == expected else "moved"
    return "absent" if observed.returncode == 1 else "unavailable"


def retirement_observation(
    repo: Path, control_root: Path, lane: dict[str, object]
) -> dict[str, str]:
    """Observe the three native carriers after one retirement attempt."""
    branch, expected = (str(lane.get(key) or "") for key in ("branch", "head"))
    return {
        "lease_state": observe_lease(state_database(repo), branch).state,
        "ref_state": ref_outcome(control_root, branch, expected),
        "worktree_state": worktree_outcome(lane),
    }


def retirement_terminal(observed: dict[str, str]) -> bool:
    """Return whether Lease, ref, and worktree are all absent."""
    return observed == {
        "lease_state": "missing",
        "ref_state": "absent",
        "worktree_state": "absent",
    }


def worktree_outcome(lane: dict[str, object]) -> str:
    """Classify one linked worktree against its expected branch and HEAD."""
    path = Path(str(lane.get("path") or ""))
    if not path.exists():
        return "absent"
    branch = output(path, "symbolic-ref", "--short", "HEAD")
    head = output(path, "rev-parse", "HEAD")
    return (
        "expected"
        if branch == str(lane.get("branch") or "") and head == str(lane.get("head") or "")
        else "moved"
    )
