"""Local fallback evidence: publish's own admission of the proof Attestation for its head.

The proof runs the owner's declared gates, so it is the evidence a publish without a reachable
peer falls back to. Hosted CI status is never claimed.
"""

from __future__ import annotations

from collections.abc import Mapping

_TEXT = {
    "admitted": "the proof Attestation for this head is the local fallback evidence",
    "missing": "no proof Attestation admits this head; run the full proof",
    "unavailable": "no proof is admitted until local publish admission passes",
    "not_required": "a review target needs no proof Attestation",
}


def fallback_projection(proof_admission: Mapping[str, object]) -> dict[str, object]:
    """Project publish's proof admission as fallback evidence; an unknown state is unavailable."""
    state = str(proof_admission.get("state") or "")
    state = state if state in _TEXT else "unavailable"
    attestation = proof_admission.get("attestation")
    identity = attestation.get("id") if isinstance(attestation, Mapping) else ""
    return {
        "kind": "local_ci_fallback",
        "evidence_class": "local_fallback",
        "hosted_ci_status_claimed": False,
        "state": state,
        "text": _TEXT[state],
        "attestation_id": str(identity or "") if state == "admitted" else "",
        "next_action": str(proof_admission.get("next_action") or ""),
    }
