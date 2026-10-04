"""Explicit semantic-contract values shared by tests."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment

if TYPE_CHECKING:
    from typing import Any


def occurrence_attestation(ordinal: int, *, payload_bytes: int = 0) -> Attestation:
    """Create one deterministic occurrence without coupling test modules together."""
    occurrence = {"ordinal": ordinal, "source": "test"}
    if payload_bytes:
        occurrence["text"] = "x" * payload_bytes
    return attestation_fixture(
        predicate="observation:repository",
        verifier="agent:test:attestation-set",
        subject=f"input:occurrence:{ordinal}",
        issued_at=datetime(2026, 8, 14, tzinfo=UTC),
        payload_kind="input:feedback",
        payload_body={"occurrence": occurrence},
        evidence_refs=(f"evidence:test:{ordinal}",),
    )


def attestation_fixture(
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


def commitment_fixture(**fields: object) -> Commitment:
    """Build one minimal compiled Commitment without compatibility fields."""
    return Commitment.model_validate(
        {"schema_version": 3, "acceptance": ("acceptance:fixture",), **fields}
    )


def reissue_attestation(record: Attestation, **updates: object) -> Attestation:
    body = updates.pop("body", None)
    payload = record.model_dump(mode="python", exclude={"id"})
    if body is not None:
        payload["payload"] = {"kind": record.payload.kind, "body": body}
    return Attestation.issue(payload | updates)
