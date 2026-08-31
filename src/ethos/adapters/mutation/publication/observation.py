"""Observe exact remote publication refs without inventing missing facts."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git
from ethos.adapters.repo.git_object import zero_oid

if TYPE_CHECKING:
    from pathlib import Path

REMOTE_REF_OBSERVATION_TIMEOUT_SECONDS = 30


def observe_remote_ref(root: Path, remote: str, ref: str) -> dict[str, object]:
    """Observe one exact remote ref as present, absent, or unavailable."""
    zero = zero_oid(root)
    peeled_ref = f"{ref}^{{}}" if ref.startswith("refs/tags/") else ""
    args = ("ls-remote", remote, ref, *((peeled_ref,) if peeled_ref else ()))
    try:
        completed = git.run_network_git(
            root,
            *args,
            timeout=REMOTE_REF_OBSERVATION_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        stderr = (
            error.stderr.decode(errors="replace")
            if isinstance(error.stderr, bytes)
            else error.stderr
        )
        return {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "reason": "timeout",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "command": list(error.cmd),
            "cwd": root.resolve().as_posix(),
            "timeout_seconds": REMOTE_REF_OBSERVATION_TIMEOUT_SECONDS,
            "stderr": (stderr or "").strip(),
        }
    except git.GitExecutionError as error:
        return {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "reason": error.code,
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "command": ["git", *args],
            "cwd": root.resolve().as_posix(),
            "timeout_seconds": REMOTE_REF_OBSERVATION_TIMEOUT_SECONDS,
            "stderr": error.reason,
        }
    if completed.returncode != 0:
        return {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "reason": "ls_remote_failed",
            "exit_code": completed.returncode,
            "command": list(completed.args),
            "cwd": root.resolve().as_posix(),
            "timeout_seconds": REMOTE_REF_OBSERVATION_TIMEOUT_SECONDS,
            "stderr": completed.stderr.strip(),
        }
    rows = tuple(line.split() for line in completed.stdout.splitlines() if line.strip())
    if not rows:
        return {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "absent",
            "object_oid": zero,
            "peeled_commit": zero,
            "tree_oid": zero,
            "exit_code": 0,
            "stderr": "",
        }
    values = {row[1]: row[0] for row in rows if len(row) == 2}
    if len(values) != len(rows) or ref not in values or set(values) - {ref, peeled_ref}:
        return {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "reason": "remote_ref_observation_ambiguous",
            "exit_code": 1,
            "command": list(completed.args),
            "cwd": root.resolve().as_posix(),
            "timeout_seconds": REMOTE_REF_OBSERVATION_TIMEOUT_SECONDS,
            "stderr": "remote_ref_observation_ambiguous",
        }
    return {
        "kind": "git_remote_ref_observation",
        "remote": remote,
        "ref": ref,
        "state": "present",
        "object_oid": values[ref],
        "peeled_commit": values.get(peeled_ref, values[ref]),
        "tree_oid": git.current_tree(root, values.get(peeled_ref, values[ref])),
        "exit_code": 0,
        "stderr": "",
    }
