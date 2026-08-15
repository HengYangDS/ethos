"""Explicit semantic-v2 values shared by tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any


def attestation_v2(
    *,
    predicate: str,
    verifier: str,
    subject: str,
    issued_at: datetime,
    payload_kind: str,
    payload_body: dict[str, Any],
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    verdict: str = "pass",
    relations: tuple[Any, ...] = (),
    advisories: tuple[str, ...] = (),
    evidence_refs: tuple[str, ...] = (),
    commitment_digest: str | None = None,
    facts_digest: str | None = None,
    plan_digest: str | None = None,
    policy_digest: str | None = None,
    effect_digest: str | None = None,
    **invalid: object,
) -> Attestation:
    """Issue one complete Attestation v2 without preserving v1 fields."""
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": predicate,
            "verifier": verifier,
            "subject": subject,
            "issued_at": issued_at,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "verdict": verdict,
            "payload": {"kind": payload_kind, "body": payload_body},
            "relations": relations,
            "advisories": advisories,
            "evidence_refs": evidence_refs,
            "commitment_digest": commitment_digest,
            "facts_digest": facts_digest,
            "plan_digest": plan_digest,
            "policy_digest": policy_digest,
            "effect_digest": effect_digest,
            "mints_authority": False,
            **invalid,
        }
    )


def commitment_v2(**fields: object) -> Commitment:
    """Build one complete Commitment v2 without adding production defaults."""
    required = {"schema_version", "id", "intent", "subjects"}
    empty_collections = dict.fromkeys(Commitment.model_fields.keys() - required, ())
    return Commitment.model_validate({"schema_version": 2, **empty_collections, **fields})
