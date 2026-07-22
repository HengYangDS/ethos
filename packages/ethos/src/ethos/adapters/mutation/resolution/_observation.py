"""Recomputed Work Lane observations for exceptional resolution."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.store.state.lease.projection import active_leases
from ethos_core.contracts.resolution.lane import LaneObservation


def observe_lane(root: Path, branch: str) -> tuple[LaneObservation, list[str]]:
    """Observe one lane from current Git and lease state."""
    registered = worktree(root, branch)
    if not registered:
        empty = hashlib.sha256(b"").hexdigest()
        return LaneObservation(
            lane_ref=branch or "unknown",
            head="0" * 40,
            lane_incarnation_id="missing",
            path=root.resolve().as_posix(),
            dirty=True,
            foreign=True,
            orphan=True,
            ambiguous=True,
            tracked_digest=empty,
            untracked_digest=empty,
        ), ["lane_resolution_target_missing"]
    path = Path(registered["worktree"])
    head = git_output(root, "rev-parse", f"refs/heads/{branch}")
    matching = [lease for lease in leases(root) if lease.get("subject") == branch]
    lease = matching[0] if len(matching) == 1 else {}
    holder = str(lease.get("holder_ref") or "")
    incarnation = str(lease.get("lane_incarnation_id") or "") or (
        "decision-incarnation:"
        + hashlib.sha256(f"{branch}\0{head}\0{path.resolve().as_posix()}".encode()).hexdigest()
    )
    return LaneObservation(
        lane_ref=branch,
        head=head,
        lane_incarnation_id=incarnation,
        holder_ref=holder,
        path=path.resolve().as_posix(),
        dirty=bool(git_output(path, "status", "--porcelain", check=False)),
        foreign=not bool(holder),
        orphan=not bool(matching),
        ambiguous=len(matching) > 1,
        tracked_digest=hashlib.sha256(
            git_output(path, "diff", "--binary", "HEAD", "--", check=False).encode()
        ).hexdigest(),
        untracked_digest=untracked_digest(path),
    ), []


def worktree(root: Path, branch: str) -> dict[str, str]:
    """Return the registered worktree row for one branch."""
    rows, current = [], {}
    lines = git_output(root, "worktree", "list", "--porcelain", check=False).splitlines()
    for line in [*lines, ""]:
        if line:
            key, _, value = line.partition(" ")
            current[key] = value
        elif current:
            rows.append(current)
            current = {}
    return next((row for row in rows if row.get("branch") == f"refs/heads/{branch}"), {})


def leases(root: Path) -> list[dict[str, Any]]:
    """Return active leases from the primary repository control store."""
    common = Path(git_output(root, "rev-parse", "--git-common-dir"))
    control_root = (common if common.is_absolute() else root / common).resolve().parent
    return active_leases(control_root / ".ethos/state/state.sqlite")


def untracked_digest(path: Path) -> str:
    """Digest all non-ignored untracked bytes in stable path order."""
    inventory = untracked_files(path)
    if inventory is None:
        return hashlib.sha256(b"unavailable").hexdigest()
    digest = hashlib.sha256()
    for raw in inventory:
        file_path = path / raw.decode(errors="surrogateescape")
        digest.update(
            raw + b"\0" + (file_path.read_bytes() if file_path.is_file() else b"") + b"\0"
        )
    return digest.hexdigest()


def untracked_files(path: Path) -> list[bytes] | None:
    """Return sorted non-ignored untracked paths or None when Git cannot enumerate."""
    completed = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=path,
        check=False,
        capture_output=True,
    )
    return (
        None
        if completed.returncode
        else sorted(item for item in completed.stdout.split(b"\0") if item)
    )


def git_output(root: Path, *args: str, check: bool = True) -> str:
    """Run one read-only Git command and return stripped stdout."""
    completed = run_git(root, *args, check=False)
    if check and completed.returncode:
        raise ValueError(completed.stderr.strip() or "git_command_failed")
    return completed.stdout.strip()
