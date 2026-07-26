"""Recomputed Work Lane observations for exceptional resolution."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import cast

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos.contracts.resolution.lane import LaneObservation


def observe_lane(root: Path, branch: str) -> tuple[LaneObservation, list[str]]:
    """Observe one lane from the shared Git and lease projections."""
    worktree = next(
        (
            item
            for item in cast("list[dict[str, str]]", workspace_status(root)["worktrees"])
            if item["branch"] == branch
        ),
        {},
    )
    if not worktree:
        empty = hashlib.sha256(b"").hexdigest()
        object_format = run_git(
            root, "rev-parse", "--show-object-format", check=False, observation=True
        ).stdout.strip()
        return LaneObservation(
            lane_ref=branch or "unknown",
            head="0" * (64 if object_format == "sha256" else 40),
            lane_incarnation_id="missing",
            path=root.resolve().as_posix(),
            dirty=True,
            foreign=True,
            orphan=True,
            ambiguous=True,
            tracked_digest=empty,
            untracked_digest=empty,
        ), ["lane_resolution_target_missing"]

    path = Path(worktree["path"])
    head = run_git(root, "rev-parse", f"refs/heads/{branch}", observation=True).stdout.strip()
    lease = leases_by_branch(root).get(branch, {})
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
        dirty=bool(
            run_git(path, "status", "--porcelain", check=False, observation=True).stdout.strip()
        ),
        foreign=not bool(holder),
        orphan=not bool(lease),
        ambiguous=False,
        tracked_digest=hashlib.sha256(
            run_git(
                path,
                "diff",
                "--binary",
                "HEAD",
                "--",
                check=False,
                text=False,
                observation=True,
            ).stdout
        ).hexdigest(),
        untracked_digest=untracked_digest(path),
    ), []


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
    """Return sorted non-ignored untracked paths or ``None`` when unavailable."""
    completed = run_git(
        path,
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        check=False,
        text=False,
        observation=True,
    )
    return (
        None
        if completed.returncode
        else sorted(item for item in completed.stdout.split(b"\0") if item)
    )
