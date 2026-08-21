"""Issue and decode typed evidence for exact native repository effects."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import NamedTuple
from typing import cast

from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.value import JsonObject


class NativeEffect(NamedTuple):
    """Exact subject and observations for one non-CAS effect."""

    predicate: str
    operation: str
    command: tuple[str, ...]
    subject: JsonObject
    before: JsonObject
    after: JsonObject


def issue_native_effect(
    _root: Path,
    *,
    effect: NativeEffect,
    state: str,
    commitment_digest: str,
    repository_id: str,
    issued_at: datetime | None = None,
) -> Attestation:
    """Issue one digest-bound effect Attestation from exact pre/post facts."""
    payload = effect._asdict()
    effect_digest = canonical_json_digest(payload)
    result = native_effect_result(state)
    issued = issued_at or datetime.now(UTC)
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": effect.predicate,
            "verifier": "git",
            "subject": f"{effect.predicate}:{effect_digest}",
            "issued_at": issued,
            "valid_from": issued,
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": "effect:native",
                "body": {
                    "claim": {"operation": effect.operation, "effect": effect_digest},
                    "repository": repository_id,
                    "command": effect.command,
                    "input": effect.before,
                    "result": result,
                    "output": effect.after,
                    "input_digest": canonical_json_digest(effect.before),
                    "output_digest": canonical_json_digest(
                        {"result": result, "output": effect.after}
                    ),
                    "freshness": {
                        "mode": "semantic_scope",
                        "repository": repository_id,
                        "subject": effect.subject,
                        **effect.subject,
                        "output_digest": canonical_json_digest(effect.after),
                    },
                },
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": commitment_digest,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": effect_digest,
            "mints_authority": False,
        }
    )


def native_effect_result(state: str) -> dict[str, object]:
    """Return one closed execution-state projection."""
    executed = state in {"applied", "recognized"}
    return {"state": state, "executed": executed, "exit_code": 0 if executed else None}


def native_effect_components(
    attestation: Attestation,
    predicate: str,
) -> tuple[JsonObject, JsonObject, JsonObject, JsonObject, JsonObject, JsonObject] | None:
    """Decode one current native-effect Attestation envelope."""
    now = datetime.now(UTC)
    if not (
        attestation.verdict == "pass"
        and attestation.predicate == predicate
        and attestation.payload.kind == "effect:native"
        and attestation.verifier == "git"
        and (attestation.valid_from or attestation.issued_at) <= now
        and (attestation.valid_until is None or now <= attestation.valid_until)
        and attestation.commitment_digest is not None
        and attestation.effect_digest is not None
    ):
        return None
    statement = attestation.payload.body
    values = tuple(
        _semantic_mapping(statement.get(name))
        for name in ("input", "output", "claim", "result", "freshness")
    )
    if any(value is None for value in values):
        return None
    before, output, claim, result, freshness = cast(
        "tuple[JsonObject, JsonObject, JsonObject, JsonObject, JsonObject]", values
    )
    return statement, before, output, claim, result, freshness


def native_effect_projection(
    attestation: Attestation,
    statement: JsonObject,
    claim: JsonObject,
    result: JsonObject,
    freshness: JsonObject,
    before: object,
    output: JsonObject,
) -> JsonObject:
    """Project one validated native-effect Attestation."""
    projection = {
        "predicate": attestation.predicate,
        "attestation_id": attestation.id,
        "commitment_digest": attestation.commitment_digest,
        "effect_digest": attestation.effect_digest,
        "repository": statement.get("repository"),
        "claim": claim,
        "result": result,
        "input": before,
        "output": output,
        "freshness": freshness,
    }
    if isinstance(before, Mapping) and isinstance(before.get("effect_identity"), str):
        projection["effect_identity"] = before["effect_identity"]
    return projection


def native_effect_digest(
    attestation: Attestation,
    claim: JsonObject,
    freshness: JsonObject,
    before: object,
    output: JsonObject,
) -> str:
    """Return the canonical identity of one native effect."""
    return canonical_json_digest(
        {
            "predicate": attestation.predicate,
            "operation": claim.get("operation"),
            "command": attestation.payload.body.get("command"),
            "subject": freshness.get("subject"),
            "before": before,
            "after": output,
        }
    )


def _semantic_mapping(value: object) -> JsonObject | None:
    normalized = mutable_json(value)
    return normalized if isinstance(normalized, dict) else None
