"""Trust-claim closeout reducers for land-stage reporting."""

from __future__ import annotations

from typing import cast


def command_is_executed_proof(command: object) -> bool:
    """True when a prove command carries the --execute flag (executed proof)."""
    text = str(command)
    return "prove" in text and "--execute" in text


def trust_closeout_package(
    *,
    workspace: dict[str, object],
    claims: dict[str, object],
) -> dict[str, object]:
    """Assess trust-claim closeout readiness (promotion + executed-proof evidence)."""
    closeout_support = workspace.get("closeout_support")
    closeout = closeout_support if isinstance(closeout_support, dict) else {}
    trust_claims = [
        claim
        for claim in cast("dict[str, object]", claims.get("claims", {})).values()
        if isinstance(claim, dict) and claim.get("trust_envelope")
    ]
    envelopes = cast(
        "list[dict[str, object]]",
        [
            cast("dict[str, object]", claim)["trust_envelope"]
            for claim in trust_claims
            if isinstance(claim.get("trust_envelope"), dict)
        ],
    )
    envelope_gaps = [
        gap
        for envelope in envelopes
        for gap in cast("list[object]", envelope.get("required_gaps", []))
        if isinstance(envelope, dict)
    ]
    promotion_ready = (
        bool(envelopes)
        and not envelope_gaps
        and all(
            isinstance(envelope.get("promotion"), dict)
            and cast("dict[str, object]", envelope["promotion"]).get("ready") is True
            for envelope in envelopes
        )
    )
    executed_proof_evidence = any(
        command_is_executed_proof(command)
        for envelope in envelopes
        if isinstance(envelope.get("evidence"), dict)
        for command in cast(
            "list[object]",
            cast("dict[str, object]", envelope["evidence"]).get("commands", []),
        )
    )
    gaps: list[str] = []
    if not claims.get("ok"):
        gaps.extend(str(gap) for gap in cast("list[object]", claims.get("required_gaps", [])))
    if not envelopes:
        gaps.append("trust_claim_missing")
    if not promotion_ready:
        gaps.append("promotion_readiness_missing")
    if not executed_proof_evidence:
        gaps.append("executed_proof_missing")
    if (
        workspace.get("role") == "work_lane"
        and closeout.get("supported") is True
        and closeout.get("claim_binding") != "bound"
    ):
        gaps.append(f"work_lane_claim_binding_missing:{workspace.get('branch')}")
    return {
        "kind": "trust_closeout",
        "claim_report_ok": bool(claims.get("ok")),
        "trust_claim_count": len(envelopes),
        "promotion_ready": promotion_ready,
        "executed_proof_evidence": executed_proof_evidence,
        "work_lane": {
            "branch": str(workspace.get("branch") or ""),
            "claim_id": str(closeout.get("claim_id") or ""),
            "claim_binding": str(closeout.get("claim_binding") or "unbound"),
        },
        "blocking": bool(gaps),
        "required_gaps": gaps,
    }
