"""Read one proof Attestation by its own record: its integrity, never a later runtime's policy."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import current_tree
from ethos.contracts.proof.plan import archive_scope_gaps
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Attestation


def proof_current_at(attestation: Attestation, instant: datetime) -> bool:
    """Return whether the Attestation's own validity window holds at one instant."""
    return (attestation.valid_from or attestation.issued_at) <= instant and (
        attestation.valid_until is None or instant <= attestation.valid_until
    )


def proof_query_gaps(attestation: Attestation) -> list[str]:
    """Name every way a proof statement is not a local repository proof."""
    statement = attestation.payload.body
    return [
        gap
        for gap, mismatch in (
            ("proof_attestation_scope_mismatch", statement.get("scope") != ("repository",)),
            ("proof_attestation_plane_mismatch", statement.get("plane") != "local"),
            (
                "proof_attestation_context_mismatch",
                statement.get("context") != {"boundary": "repository"},
            ),
        )
        if mismatch
    ]


def proof_integrity(
    root: Path,
    head: str,
    store: Path,
    attestation: Attestation,
    *,
    lane_gaps: Callable[[Mapping[str, object]], list[str]] | None = None,
) -> tuple[TransitionPlan | None, tuple[dict[str, Any], ...] | None, list[str]]:
    """Check the subject, plan, live tree, scope, artifact custody and recorded results."""
    if attestation.subject != f"git:commit:{head}":
        return None, None, ["proof_attestation_head_mismatch"]
    try:
        plan = plan_from_statement(attestation)
    except (TypeError, ValueError) as error:
        return None, None, [str(error)]
    gaps = [
        "proof_attestation_plan_head_mismatch"
        if plan.facts.get("head") != head
        else "proof_attestation_live_tree_mismatch"
        if current_tree(root, head) != plan.facts.get("tree")
        else ""
    ]
    gaps = [gap for gap in gaps if gap]
    if lane_gaps is not None:
        gaps.extend(lane_gaps(plan.facts))
    if not gaps:
        gaps.extend(archive_scope_gaps(plan.facts, plan.prior_attestations))
    if gaps:
        return plan, None, gaps
    checks, gaps = artifact_checks(store, attestation)
    if checks is not None and not gaps:
        gaps = proof_statement_gaps(attestation, checks)
    return plan, checks, list(gaps)


def recorded_proof(
    root: Path, head: str, store: Path, recorded: Mapping[str, object]
) -> tuple[tuple[Attestation, ...], list[str]]:
    """Admit the one proof a release record bound, verified as recorded under this runtime."""
    try:
        _selected_root, attestations = read_attestation_set(root)
    except ValueError as error:
        return (), [str(error)]
    bound = next((item for item in attestations if item.id == recorded.get("id")), None)
    gaps = _binding_gaps(bound, recorded)
    if bound is None or gaps:
        return (), gaps
    plan, checks, gaps = proof_integrity(root, head, store, bound)
    if not gaps and plan is not None and canonical_json_digest(plan.policy) != plan.inputs.policy:
        gaps = ["proof_attestation_recorded_policy_inconsistent"]
    if gaps or checks is None:
        return (), gaps or ["proof_attestation_artifact_missing"]
    return (bound,), []


def _binding_gaps(bound: Attestation | None, recorded: Mapping[str, object]) -> list[str]:
    """Require the set member the release record names, byte-equal to its embedded copy."""
    if bound is None or bound.predicate != "proof:execution":
        return ["release_qualification_missing"]
    if mutable_json(bound.model_dump(mode="json")) != mutable_json(recorded):
        return ["release_qualification_binding_mismatch"]
    if gaps := proof_query_gaps(bound):
        return gaps
    return [] if proof_current_at(bound, datetime.now(UTC)) else ["unknown_required_fact"]
