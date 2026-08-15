"""Explicit semantic-v2 values shared by tests."""

from __future__ import annotations

from typing import Any

from ethos.contracts.semantic import Commitment


def commitment_v2(
    *,
    id: str,  # noqa: A002 - mirrors the semantic contract field
    intent: str,
    subjects: tuple[str, ...],
    scope: tuple[str, ...] = (),
    invariants: tuple[str, ...] = (),
    acceptance: tuple[str, ...] = (),
    risks: tuple[str, ...] = (),
    authority_refs: tuple[str, ...] = (),
    predecessors: tuple[str, ...] = (),
    selected_attestations: tuple[str, ...] = (),
    dependencies: tuple[Any, ...] = (),
    hypotheses: tuple[Any, ...] = (),
    falsifiers: tuple[Any, ...] = (),
    experiment_protocols: tuple[Any, ...] = (),
    **invalid: object,
) -> Commitment:
    """Build one complete Commitment v2 without adding production defaults."""
    return Commitment.model_validate(
        {
            "schema_version": 2,
            "id": id,
            "intent": intent,
            "subjects": subjects,
            "scope": scope,
            "invariants": invariants,
            "acceptance": acceptance,
            "risks": risks,
            "authority_refs": authority_refs,
            "predecessors": predecessors,
            "selected_attestations": selected_attestations,
            "dependencies": dependencies,
            "hypotheses": hypotheses,
            "falsifiers": falsifiers,
            "experiment_protocols": experiment_protocols,
            **invalid,
        }
    )
