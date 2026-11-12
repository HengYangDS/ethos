"""Observe a peer's exact publication refs, or every ref under its namespaces, inventing no fact.

One bounded `ls-remote` answers each request. A failure keeps its exact command, cwd and exit or
timeout state, and never the peer's stderr, which can echo a private host or path. An observation
returns states and records nothing; the commands with write authority record what they observe.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from dataclasses import field
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git
from ethos.adapters.repo.git_object import zero_oid
from ethos.repository.paradigm.parameters import seconds

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class RemoteListing:
    """A peer's refs under the requested patterns, or the failure that left them unknown.

    A tag's peeled commit is listed as `<ref>^{}`.
    """

    refs: Mapping[str, str] = field(default_factory=dict)
    failure: Mapping[str, object] | None = None


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
    patterns = (*refs, *(f"{ref}^{{}}" for ref in refs if ref.startswith("refs/tags/")))
    listed = _advertisement(root, remote, patterns, exact=True)
    if listed.failure is None:
        return _present_refs(root, remote, refs, listed.refs, zero_oid(root))
    return {
        ref: {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            **listed.failure,
        }
        for ref in refs
    }


def observe_remote_namespaces(root: Path, remote: str, patterns: tuple[str, ...]) -> RemoteListing:
    """List every ref one peer advertises that a glob pattern matches whole; none lists all."""
    return _advertisement(root, remote, patterns, exact=False)


def _advertisement(
    root: Path, remote: str, patterns: tuple[str, ...], *, exact: bool
) -> RemoteListing:
    """Run one bounded `ls-remote` and parse it; an exact request admits no other ref."""
    args = ("ls-remote", remote, *patterns)
    bound = seconds("git")
    boundary: dict[str, object] = {"cwd": root.resolve().as_posix(), "timeout_seconds": bound}
    try:
        completed = git.run_network_git(root, *args, timeout=bound)
    except subprocess.TimeoutExpired as error:
        return RemoteListing(failure={"reason": "timeout", "command": list(error.cmd), **boundary})
    except git.GitExecutionError as error:
        return RemoteListing(failure={"reason": error.code, "command": ["git", *args], **boundary})
    values = _rows(completed, patterns, exact=exact)
    if values is not None:
        return RemoteListing(refs=values)
    reason = "ls_remote_failed" if completed.returncode else "remote_ref_observation_ambiguous"
    exit_code = completed.returncode or 1
    command = list(completed.args)
    return RemoteListing(
        failure={"reason": reason, "exit_code": exit_code, "command": command, **boundary}
    )


def _rows(
    completed: subprocess.CompletedProcess[str], patterns: tuple[str, ...], *, exact: bool
) -> dict[str, str] | None:
    """Parse an advertisement; a failed run, a repeated or malformed row or a stray ref is None.

    An exact request admits no other ref; a namespace listing keeps the refs a pattern matches
    whole, since `ls-remote` also matches a pattern against the tail of a longer ref.
    """
    rows = tuple(line.split() for line in completed.stdout.splitlines() if line.strip())
    values = {row[1]: row[0] for row in rows if len(row) == 2}
    stray = exact and bool(set(values) - set(patterns))
    unpeeled = any(ref.endswith("^{}") and ref[:-3] not in values for ref in values)
    if completed.returncode or len(values) != len(rows) or stray or unpeeled:
        return None
    if exact or not patterns:
        return values
    return {ref: oid for ref, oid in values.items() if any(fnmatchcase(ref, p) for p in patterns)}


def _present_refs(
    root: Path, remote: str, refs: tuple[str, ...], values: Mapping[str, str], zero: str
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
        }
    return observations
