"""Compile and recognize OpenSpec successor Commitment lineage."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import first_parent_successor
from ethos.contracts.semantic import Commitment
from ethos.repository.openspec.identifiers import active_change_commitment
from ethos.repository.openspec.identifiers import active_change_scope

if TYPE_CHECKING:
    from pathlib import Path


def successor_commitment(
    root: Path,
    *,
    change: str,
    intent: str,
    scope: tuple[str, ...],
    predecessor: Commitment,
    predecessors: tuple[str, ...],
    selected_attestations: tuple[str, ...],
) -> Commitment:
    """Construct one bounded successor Change Commitment."""
    return Commitment(
        schema_version=2,
        id=f"change:{change}",
        intent=intent.strip(),
        subjects=(load_repository_commitment(root).id,),
        scope=_successor_scope(change, scope),
        invariants=(),
        acceptance=(),
        risks=(),
        authority_refs=(),
        predecessors=_canonical_predecessors(
            current=predecessor.digest(),
            additional=predecessors,
        ),
        selected_attestations=selected_attestations,
        dependencies=(),
        hypotheses=(),
        falsifiers=(),
        experiment_protocols=(),
    )


def committed_successor_mismatch(
    root: Path,
    *,
    change: str,
    previous_head: str,
    current_predecessor: str,
    intent: str,
    scope: tuple[str, ...],
    predecessors: tuple[str, ...],
    selected_attestations: tuple[str, ...],
) -> bool:
    """Return whether a committed successor differs from the requested semantics."""
    head = current_tracked_head(root)
    successor = first_parent_successor(root, previous_head, head)
    if not successor:
        return False
    carrier = active_change_commitment(change)
    try:
        started = load_commitment(
            root,
            carrier=carrier,
            change_id=change,
            tree_ref=successor,
        )
    except ValueError:
        return False
    try:
        current = load_commitment(
            root,
            carrier=carrier,
            change_id=change,
            tree_ref=head,
        )
    except ValueError:
        return True
    return (
        current.digest() != started.digest()
        or started.intent != intent.strip()
        or started.scope != _successor_scope(change, scope)
        or started.predecessors
        != _canonical_predecessors(
            current=current_predecessor,
            additional=predecessors,
        )
        or started.selected_attestations != tuple(sorted(set(selected_attestations)))
    )


def _canonical_predecessors(
    *,
    current: str,
    additional: tuple[str, ...],
) -> tuple[str, ...]:
    for digest in (current, *additional):
        try:
            Commitment.validate_digest_set((digest,))
        except ValueError as error:
            message = f"change_lineage_predecessor_invalid:{digest}"
            raise ValueError(message) from error
    if len(additional) != len(set(additional)):
        message = "change_lineage_predecessor_duplicate"
        raise ValueError(message)
    if current in additional:
        message = "change_lineage_current_predecessor_redeclared"
        raise ValueError(message)
    return Commitment.validate_digest_set(tuple(sorted((current, *additional))))


def _successor_scope(change: str, scope: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {active_change_scope(change), *scope},
            key=lambda value: json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode(),
        )
    )
