"""Attest terminal remote-publication effects."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import record_attestations
from ethos.contracts.semantic import Attestation

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.publication import PublicationEffect
    from ethos.contracts.verdict import Verdict


def terminal_publication_result(
    *,
    root: Path,
    plan: TransitionPlan,
    effect: PublicationEffect,
    verdict: Verdict,
    state: str,
    required_gaps: tuple[str, ...],
    observations: dict[str, dict[str, object]],
    applied: tuple[str, ...],
    failed: str,
    pending: tuple[str, ...],
    attempts: tuple[dict[str, object], ...],
) -> dict[str, object]:
    """Record and project one terminal publication result."""
    partial_effects = {
        "applied_peers": list(applied),
        "failed_peer": failed,
        "pending_peers": list(pending),
    }
    statement = {
        "claim": {"operation": effect.operation, "verdict": verdict},
        "plan": plan.model_dump(mode="json"),
        "effect": effect.model_dump(mode="json"),
        "state": state,
        "required_gaps": list(required_gaps),
        "observations": observations,
        "partial_effects": partial_effects,
        "attempts": list(attempts),
        "cross_provider_atomicity_claimed": False,
    }
    attestation = Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "publication:remote-effect",
            "verifier": "ethos:remote-publication-executor",
            "subject": f"git:{effect.source.kind}:{effect.source.object_oid}",
            "issued_at": datetime.now(UTC),
            "valid_from": None,
            "valid_until": None,
            "verdict": verdict,
            "payload": {"kind": "publication:remote-effect", "body": statement},
            "relations": (),
            "advisories": (),
            "commitment_digest": plan.inputs.commitment,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": effect.digest(),
            "evidence_refs": tuple(
                sorted(
                    f"git:{target.remote}:{update.target_ref}:{update.desired}"
                    for target in effect.targets
                    for update in target.updates
                )
            ),
            "mints_authority": False,
        }
    )
    selected = record_attestations(root, (attestation,))
    return {
        "state": state,
        "required_gaps": list(required_gaps),
        "observations": observations,
        "partial_effects": partial_effects,
        "attempts": list(attempts),
        "attestation": {"id": attestation.id, "set_root": selected["root"]},
    }
