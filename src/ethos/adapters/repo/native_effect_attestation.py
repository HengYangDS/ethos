"""Issue typed evidence for exact non-CAS repository effects."""

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
    root: Path,
    *,
    effect: NativeEffect,
    state: str,
    commitment_digest: str,
    repository_id: str,
) -> Attestation:
    """Issue one digest-bound effect Attestation from exact pre/post facts."""
    payload = effect._asdict()
    effect_digest = canonical_json_digest(payload)
    result = {"state": state, "executed": state == "applied", "exit_code": 0}
    issued = datetime.now(UTC)
    return Attestation.issue(
        {
            "predicate": effect.predicate,
            "verifier": "git",
            "subject": f"{effect.predicate}:{effect_digest}",
            "issued_at": issued,
            "valid_from": issued,
            "verdict": "pass",
            "commitment_digest": commitment_digest,
            "effect_digest": effect_digest,
            "statement": {
                "claim": {"operation": effect.operation, "effect": effect_digest},
                "repository": repository_id,
                "command": effect.command,
                "input": effect.before,
                "result": result,
                "output": effect.after,
                "input_digest": canonical_json_digest(effect.before),
                "output_digest": canonical_json_digest({"result": result, "output": effect.after}),
                "freshness": {
                    "mode": "semantic_scope",
                    "repository": repository_id,
                    "subject": effect.subject,
                    **effect.subject,
                    "output_digest": canonical_json_digest(effect.after),
                },
            },
        }
    )
