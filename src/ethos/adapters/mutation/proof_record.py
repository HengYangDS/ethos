"""Read one proof Attestation by its own record: its integrity, never a later runtime's policy."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.repo.git import current_tree
from ethos.contracts.proof.plan import archive_scope_gaps
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan


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
    """Admit the proof a release record embeds, verified as that record bound it (DR-0018).

    The embedded copy is the content-addressed Attestation made at release time, so it is
    verified itself and never looked up in the set, whose member ends once no tag pins its
    commit. `head` is the commit being published; a re-created tag's proof is verified on the
    original commit that its release record names.
    """
    embedded = {key: value for key, value in recorded.items() if key != "proven_commit"}
    if embedded.get("predicate") != "proof:execution" or embedded.get("verdict") != "pass":
        return (), ["release_qualification_missing"]
    try:
        bound = Attestation.model_validate(mutable_json(embedded))
    except (TypeError, ValueError):
        return (), ["release_qualification_unverified"]
    gaps = proof_query_gaps(bound) or (
        [] if proof_current_at(bound, datetime.now(UTC)) else ["unknown_required_fact"]
    )
    if gaps:
        return (), gaps
    proven = str(recorded.get("proven_commit") or head)
    plan, checks, gaps = proof_integrity(root, proven, store, bound)
    if not gaps and plan is not None and canonical_json_digest(plan.policy) != plan.inputs.policy:
        gaps = ["proof_attestation_recorded_policy_inconsistent"]
    if gaps or checks is None:
        return (), gaps or ["proof_attestation_artifact_missing"]
    return (bound,), []
