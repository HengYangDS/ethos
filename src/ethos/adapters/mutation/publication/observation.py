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
    """Observe one exact ref through the same peer-set reader."""
    return observe_remote_refs(root, remote, (ref,))[ref]


def observe_remote_refs(
    root: Path, remote: str, refs: tuple[str, ...]
) -> dict[str, dict[str, object]]:
    """Read one peer's requested refs in one bounded native advertisement."""
    refs = tuple(dict.fromkeys(refs))
    if not refs:
        return {}
    zero = zero_oid(root)
    patterns = (*refs, *(f"{ref}^{{}}" for ref in refs if ref.startswith("refs/tags/")))
    args = ("ls-remote", remote, *patterns)
    failure: dict[str, object]
    try:
        completed = git.run_network_git(root, *args, timeout=REMOTE_REF_OBSERVATION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        stderr = (
            error.stderr.decode(errors="replace")
            if isinstance(error.stderr, bytes)
            else error.stderr
        )
        failure = {
            "reason": "timeout",
            "command": list(error.cmd),
            "stderr": (stderr or "").strip(),
        }
    except git.GitExecutionError as error:
        failure = {"reason": error.code, "command": ["git", *args], "stderr": error.reason}
    else:
        rows = tuple(line.split() for line in completed.stdout.splitlines() if line.strip())
        values = {row[1]: row[0] for row in rows if len(row) == 2}
        ambiguous = (
            len(values) != len(rows)
            or bool(set(values) - set(patterns))
            or any(ref.endswith("^{}") and ref[:-3] not in values for ref in values)
        )
        if completed.returncode == 0 and not ambiguous:
            return _present_refs(root, remote, refs, values, zero)
        reason = "ls_remote_failed" if completed.returncode else "remote_ref_observation_ambiguous"
        failure = {
            "reason": reason,
            "exit_code": completed.returncode or 1,
            "command": list(completed.args),
            "stderr": completed.stderr.strip() if completed.returncode else reason,
        }
    return {
        ref: {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "cwd": root.resolve().as_posix(),
            "timeout_seconds": REMOTE_REF_OBSERVATION_TIMEOUT_SECONDS,
            **failure,
        }
        for ref in refs
    }


def _present_refs(
    root: Path, remote: str, refs: tuple[str, ...], values: dict[str, str], zero: str
) -> dict[str, dict[str, object]]:
    """Project present and absent refs, resolving each advertised commit tree once."""
    trees = {zero: zero}
    observations: dict[str, dict[str, object]] = {}
    for ref in refs:
        object_oid = values.get(ref, zero)
        peeled = values.get(f"{ref}^{{}}", object_oid)
        if peeled not in trees:
            trees[peeled] = git.current_tree(root, peeled)
        observations[ref] = {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "present" if ref in values else "absent",
            "object_oid": object_oid,
            "peeled_commit": peeled,
            "tree_oid": trees[peeled],
            "exit_code": 0,
            "stderr": "",
        }
    return observations
