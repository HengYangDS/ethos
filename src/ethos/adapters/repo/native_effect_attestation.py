"""Issue and decode typed evidence for exact native repository effects."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest

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
    commitment_digest: str | None,
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
