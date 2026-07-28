"""Carrier cleanup transaction for failed cross-host handoff imports."""

from __future__ import annotations

import os
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Callable


from ethos.adapters.mutation.lane_lifecycle.handoff.package import lease_binding
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease_from_connection
from ethos.adapters.store.state.lease.lifecycle.transitions import expected_current_lease
from ethos.adapters.store.state.schema import state_database


def compensate_failed_import(
    *,
    destination: Path,
    manifest: dict[str, Any],
    worktree_path: Path,
    lease: dict[str, Any],
    object_environment: dict[str, str],
    run_git: Callable[..., Any],
    verify_destination_identity: Callable[..., None],
) -> None:
    """Remove only verified import carriers, then revoke the local lease."""
    try:
        binding = lease_binding(str(manifest["source_lane_ref"]), lease)
        with closing(sqlite3.connect(state_database(destination))) as connection:
            connection.execute("pragma foreign_keys = on")
            connection.execute("begin immediate")
            expected_current_lease(connection, request=binding, require_expired=False)
            remove_import_carriers(
                destination,
                manifest,
                worktree_path,
                lease,
                object_environment=object_environment,
                run_git=run_git,
                verify_destination_identity=verify_destination_identity,
            )
            revoke_lease_from_connection(connection, request=binding)
            connection.commit()
    except (OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError, ValueError):
        raise ValueError("handoff_import_compensation_failed") from None


def remove_import_carriers(
    destination: Path,
    manifest: dict[str, Any],
    worktree_path: Path,
    lease: dict[str, Any],
    *,
    object_environment: dict[str, str],
    run_git: Callable[..., Any],
    verify_destination_identity: Callable[..., None],
) -> None:
    """Remove the exact worktree and ref created by a failed import."""
    branch, head = str(manifest["source_lane_ref"]), str(manifest["source_head"])
    present = os.path.lexists(worktree_path)
    record = import_worktree_record(destination, worktree_path, run_git=run_git)
    _require("handoff_import_compensation_failed", holds=present == bool(record))
    if record:
        unsafe = (
            worktree_path.is_symlink()
            or not worktree_path.is_dir()
            or record.get("branch") != branch
            or record.get("HEAD") != head
            or any(flag in record for flag in ("locked", "prunable"))
        )
        _require("handoff_import_compensation_failed", holds=not unsafe)
        verify_destination_identity(
            destination,
            worktree_path,
            manifest,
            lease,
            object_environment=object_environment,
        )
        status = run_git(
            worktree_path,
            "status",
            "--porcelain",
            "-uall",
            "--ignored=matching",
            check=False,
            env=object_environment,
        )
        _require(
            "handoff_import_compensation_failed",
            holds=not status.returncode and not status.stdout.strip(),
        )
        removed = run_git(
            destination,
            "worktree",
            "remove",
            worktree_path.as_posix(),
            check=False,
            env=object_environment,
        )
        _require("handoff_import_compensation_failed", holds=not removed.returncode)
    _require(
        "handoff_import_compensation_failed",
        holds=not os.path.lexists(worktree_path)
        and not import_worktree_record(destination, worktree_path, run_git=run_git),
    )
    ref = f"refs/heads/{branch}"
    observed = run_git(
        destination,
        "show-ref",
        "--verify",
        "--quiet",
        ref,
        check=False,
        env=object_environment,
    )
    _require("handoff_import_compensation_failed", holds=observed.returncode in {0, 1})
    if observed.returncode == 0:
        actual = run_git(destination, "rev-parse", ref, env=object_environment).stdout.strip()
        _require("handoff_import_compensation_failed", holds=actual == head)
        deleted = run_git(
            destination,
            "update-ref",
            "-d",
            ref,
            head,
            check=False,
            env=object_environment,
        )
        _require("handoff_import_compensation_failed", holds=not deleted.returncode)
    absent = run_git(
        destination,
        "show-ref",
        "--verify",
        "--quiet",
        ref,
        check=False,
        env=object_environment,
    )
    _require("handoff_import_compensation_failed", holds=absent.returncode == 1)


def import_worktree_record(
    destination: Path, target: Path, *, run_git: Callable[..., Any]
) -> dict[str, str]:
    """Return the unique Git worktree record for a destination path."""
    listed = run_git(destination, "worktree", "list", "--porcelain", check=False)
    _require("handoff_import_compensation_failed", holds=not listed.returncode)
    records = [
        dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        for block in listed.stdout.split("\n\n")
        if block.strip()
    ]
    _require(
        "handoff_import_compensation_failed",
        holds=all({"worktree", "HEAD"} <= record.keys() for record in records),
    )
    matches = [
        record for record in records if Path(record["worktree"]).resolve() == target.resolve()
    ]
    _require("handoff_import_compensation_failed", holds=len(matches) <= 1)
    record = matches[0] if matches else {}
    if record:
        record["branch"] = record.get("branch", "").removeprefix("refs/heads/")
    return record


def _require(gap: str, *, holds: bool) -> None:
    if not holds:
        raise ValueError(gap)
