"""Resolve governed Change predecessors from one exact Git tree."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.git import run_git
from ethos.repository.openspec.identifiers import parse_change_commitment

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment


def resolve_predecessor_commitments(
    repo: Path,
    *,
    tree_ref: str,
    predecessors: tuple[str, ...],
) -> tuple[Commitment, ...]:
    """Resolve exact predecessor Commitments from one immutable Git tree."""
    if not predecessors:
        return ()
    listed = run_git(
        repo,
        "ls-tree",
        "-r",
        "--name-only",
        tree_ref,
        "--",
        "openspec/changes",
        check=False,
        observation=True,
    )
    if listed.returncode:
        message = "change_lineage_tree_unreadable"
        raise ValueError(message)
    requested = set(predecessors)
    resolved: dict[str, list[Commitment]] = {}
    for carrier in listed.stdout.splitlines():
        if parse_change_commitment(carrier) is None:
            continue
        try:
            commitment = load_commitment(repo, carrier=carrier, tree_ref=tree_ref)
        except ValueError:
            continue
        digest = commitment.digest()
        if digest in requested:
            resolved.setdefault(digest, []).append(commitment)
    if missing := next((digest for digest in predecessors if digest not in resolved), ""):
        message = f"change_lineage_predecessor_missing:{missing}"
        raise ValueError(message)
    if ambiguous := next((digest for digest in predecessors if len(resolved[digest]) != 1), ""):
        message = f"change_lineage_predecessor_ambiguous:{ambiguous}"
        raise ValueError(message)
    return tuple(resolved[digest][0] for digest in predecessors)
