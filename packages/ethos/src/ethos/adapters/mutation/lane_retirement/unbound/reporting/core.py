"""Result envelopes for exceptional unbound Work Lane retirement."""

from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
import ethos.adapters.mutation.lane_retirement.unbound.observation.core as observation


def report(  # noqa: PLR0913, RUF100 - exact reporting preserves bound state dimensions
    *,
    branch: str,
    expect_head: str,
    reason: str,
    chronicle_ref: str,
    apply: bool,
    authorized: bool,
    break_glass: bool,
    confirm_irreversible: bool,
    owner_unavailable_recovery: bool,
    partial_effect_reconciliation: bool = False,
    holder_ref: str = "",
    observed: dict[str, object],
    gaps: list[str],
) -> dict[str, object]:
    """Build the stable public dry-run or blocked transition envelope."""
    state = (
        "ready_to_reconcile_ref_absent_owner_unavailable_lease"
        if partial_effect_reconciliation
        else "ready_to_retire_unbound_exceptional"
    )
    return {
        "ok": not gaps,
        "state": state if not gaps else "blocked",
        "branch": branch,
        "head": str(observed["head"]),
        "accepted_head": str(observed["accepted_head"]),
        "relation_to_accepted": str(observed["relation_to_accepted"]),
        "claim_id": str(observed["claim_id"]),
        "claim_binding": str(observed["claim_binding"]),
        "reason": reason,
        "chronicle_ref": chronicle_ref,
        "owner_unavailable_recovery": owner_unavailable_recovery,
        "partial_effect_reconciliation": partial_effect_reconciliation,
        "observation": observation.public_observation(observed),
        "mutation": mutation(
            branch=branch,
            expect_head=expect_head,
            reason=reason,
            chronicle_ref=chronicle_ref,
            apply=apply,
            confirmed=authorized and break_glass and confirm_irreversible,
            observed=observed,
            break_glass=break_glass,
            confirm_irreversible=confirm_irreversible,
            owner_unavailable_recovery=owner_unavailable_recovery,
            partial_effect_reconciliation=partial_effect_reconciliation,
            holder_ref=holder_ref,
            gaps=gaps,
        ),
        "required_gaps": sorted(set(gaps)),
    }


def mutation(  # noqa: PLR0913, RUF100 - exact mutation envelope preserves bound state dimensions
    *,
    branch: str,
    expect_head: str,
    reason: str,
    chronicle_ref: str,
    apply: bool,
    confirmed: bool,
    observed: dict[str, object],
    break_glass: bool,
    confirm_irreversible: bool,
    owner_unavailable_recovery: bool,
    partial_effect_reconciliation: bool = False,
    holder_ref: str = "",
    gaps: list[str],
) -> dict[str, object]:
    """Build the admission-bound mutation envelope without minting authority."""
    chronicle = cast("dict[str, object]", observed["chronicle"])
    command = (
        "lane-retire-reconcile-ref-absent"
        if partial_effect_reconciliation
        else "lane-retire-unbound"
    )
    action = (
        "lane.retire.unbound.ref_absent_owner_unavailable_reconciliation"
        if partial_effect_reconciliation
        else "lane.retire.unbound.exceptional"
    )
    return lane_retirement_shared.retire_mutation_envelope(
        command=command,
        action=action,
        branch=branch,
        expect_head=expect_head,
        apply=apply,
        confirmed=confirmed,
        required_gaps=gaps,
        holder_ref=holder_ref,
        extra_state={
            "reason": reason,
            "accepted_head": str(observed["accepted_head"]),
            "claim_id": str(observed["claim_id"]),
            "claim_binding": str(observed["claim_binding"]),
            "chronicle_ref": chronicle_ref,
            "chronicle_sha256": str(chronicle["sha256"]),
            "chronicle_claim_id": str(chronicle["target_claim"]),
            "chronicle_claim_sha256": str(chronicle["claim_sha256"]),
            "break_glass": break_glass,
            "confirm_irreversible": confirm_irreversible,
            "owner_unavailable_recovery": owner_unavailable_recovery,
            "partial_effect_reconciliation": partial_effect_reconciliation,
            "observation_sha256": str(observed["observation_sha256"]),
        },
    )


def blocked(report_payload: dict[str, object], gaps: list[str]) -> dict[str, object]:
    """Add exact post-admission gaps while preserving the original evidence."""
    all_gaps = sorted({*cast("list[str]", report_payload.get("required_gaps", [])), *gaps})
    return {**report_payload, "ok": False, "state": "blocked", "required_gaps": all_gaps}
