"""Admit proof Attestations for one exact local repository query."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import scan_attestations
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.proof.plan import archive_scope_gaps
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


_BINDINGS = (
    "commitment_digest",
    "facts_digest",
    "plan_digest",
    "policy_digest",
    "effect_digest",
)


def proof_attestation(
    root: Path,
    head: str,
    *,
    store: Path,
) -> tuple[Attestation | None, list[str]]:
    """Return one deterministic member of the current exact proof set."""
    admitted, gaps = _admitted_proofs(root, head, store=store)
    return (min(admitted, key=lambda item: item.id), []) if admitted else (None, gaps)


def _admitted_proofs(
    root: Path,
    head: str,
    *,
    store: Path,
) -> tuple[tuple[Attestation, ...], list[str]]:
    attestations, store_gaps = scan_attestations(store)
    candidates = tuple(
        item
        for item in attestations
        if item.predicate == "proof:execution" and item.subject == f"git:commit:{head}"
    )
    if store_gaps or not candidates:
        return (), store_gaps or ["proof_not_proven"]
    instant = datetime.now(UTC)
    current = tuple(item for item in candidates if _current_at(item, instant))
    if not current:
        return (), ["unknown_required_fact"]
    matching = tuple(item for item in current if not _query_gaps(item))
    if not matching:
        return (), list(dict.fromkeys(gap for item in current for gap in _query_gaps(item)))
    evaluated = tuple((item, *_candidate_evaluation(root, head, store, item)) for item in matching)
    integrity = _integrity_gaps(evaluated)
    if integrity:
        return (), integrity
    valid_by_floor = {
        floor: tuple(
            item
            for item, item_floor, item_gaps in evaluated
            if item_floor == floor and not item_gaps
        )
        for floor in ("full", "default")
    }
    full_required = (
        resolve_gate_policy(root, tree_ref=head, full=True).digest
        != resolve_gate_policy(root, tree_ref=head).digest
    )
    valid = (
        valid_by_floor["full"]
        if full_required
        else next((items for items in valid_by_floor.values() if items), ())
    )
    if not valid:
        set_gaps = (
            ["full_proof_required"]
            if full_required and valid_by_floor["default"]
            else list(
                dict.fromkeys(gap for _item, _floor, item_gaps in evaluated for gap in item_gaps)
            )
        )
    elif len({_bindings(item) for item in valid}) > 1:
        set_gaps = ["stale_binding"]
    elif len({_assertion_digest(item) for item in valid}) > 1:
        set_gaps = ["contradiction"]
    else:
        set_gaps = []
    return ((), set_gaps) if set_gaps else (valid, [])


def _integrity_gaps(evaluated: tuple[tuple[Attestation, str, list[str]], ...]) -> list[str]:
    ignored = {
        "proof_attestation_verdict_block",
        "proof_attestation_verdict_unknown",
        "proof_attestation_check_not_passed",
    }
    return list(
        dict.fromkeys(
            gap
            for _item, _floor, gaps in evaluated
            for gap in gaps
            if (
                gap.startswith("proof_attestation_")
                or gap in {"model_gap", "proof_policy_digest_stale"}
            )
            and gap not in ignored
        )
    )


def _current_at(attestation: Attestation, instant: datetime) -> bool:
    return (attestation.valid_from or attestation.issued_at) <= instant and (
        attestation.valid_until is None or instant <= attestation.valid_until
    )


def _query_gaps(attestation: Attestation) -> list[str]:
    statement = attestation.statement
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


def _bindings(attestation: Attestation) -> tuple[str, ...]:
    return tuple(getattr(attestation, name) for name in _BINDINGS)


def _assertion_digest(attestation: Attestation) -> str:
    statement = attestation.statement
    return canonical_json_digest(
        {
            "claim": statement.get("claim"),
            "scope": statement.get("scope"),
            "plane": statement.get("plane"),
            "context": statement.get("context"),
            "boundary": statement.get("boundary"),
            "required_gaps": statement.get("required_gaps"),
            "verifier": attestation.verifier,
        }
    )


def _candidate_evaluation(
    root: Path, head: str, store: Path, attestation: Attestation
) -> tuple[str, list[str]]:
    if attestation.subject != f"git:commit:{head}":
        return "", ["proof_attestation_head_mismatch"]
    try:
        plan = plan_from_statement(attestation)
    except (TypeError, ValueError) as error:
        return "", [str(error)]
    gaps = [
        "proof_attestation_plan_head_mismatch"
        if plan.facts.get("head") != head
        else "proof_attestation_live_tree_mismatch"
        if current_tree(root, head) != plan.facts.get("tree")
        else ""
    ]
    gaps = [gap for gap in gaps if gap]
    values = plan.facts.get("values")
    fact_values = values if isinstance(values, Mapping) else {}
    generation = fact_values.get("lease_generation")
    if isinstance(generation, Mapping):
        branch = str(generation.get("branch") or "")
        current_lease = leases_by_branch(root).get(branch, {})
        if (
            current_lease.get("lease_state") != "valid"
            or current_lease.get("commitment_binding") != "bound"
            or mutable_json(generation) != mutable_json(lease_generation(current_lease))
        ):
            gaps.append("proof_lease_generation_stale")
    if gaps:
        return "", gaps
    gaps.extend(archive_scope_gaps(plan.facts, plan.prior_attestations))
    if gaps:
        return "", gaps
    checks, gaps = artifact_checks(store, attestation)
    if checks is not None and not gaps:
        gaps = proof_statement_gaps(attestation, checks)
    if gaps or checks is None:
        return "", gaps
    canonical_policies = (
        ("full", resolve_gate_policy(root, tree_ref=head, full=True)),
        ("default", resolve_gate_policy(root, tree_ref=head)),
    )
    floor = next(
        (
            name
            for name, policy in canonical_policies
            if plan.inputs.policy == policy.digest
            and plan.nodes == policy.nodes
            and canonical_json_digest(plan.policy) == policy.digest
        ),
        "",
    )
    return (floor, []) if floor else ("", ["proof_attestation_repository_policy_mismatch"])
