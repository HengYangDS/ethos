"""Algebraic invariants for proof TransitionPlan closures."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.semantic import Facts

_FACT_FIELDS = {
    "change_id",
    "changed_paths",
    "gate_ids",
    "lease_generation",
    "path_attributions",
    "selected_carrier",
}


def archive_authority_valid(value: object) -> bool:
    """Return whether one proof carries a complete selected archive effect projection."""
    if not isinstance(value, Mapping):
        return False
    authorized = value.get("authorized_paths")
    before = value.get("input")
    output = value.get("output")
    effect_identity = value.get("effect_identity")
    digests = (
        value.get("attestation_id"),
        value.get("commitment_digest"),
        value.get("effect_digest"),
        effect_identity,
    )
    return (
        value.get("predicate") == "effect:openspec-archive"
        and all(
            isinstance(digest, str) and len(digest) == 64 and set(digest) <= set("0123456789abcdef")
            for digest in digests
        )
        and isinstance(before, Mapping)
        and before.get("effect_identity") == effect_identity
        and isinstance(output, Mapping)
        and isinstance(authorized, tuple | list)
        and bool(authorized)
        and all(isinstance(path, str) and path for path in authorized)
        and len(set(authorized)) == len(authorized)
        and tuple(output.get("changed_paths", ())) == tuple(authorized)
    )


def archive_scope_gaps(
    facts: Mapping[str, object], prior_attestations: Mapping[str, object]
) -> tuple[str, ...]:
    """Require one exact archive effect identity to authorize changed paths."""
    archive = prior_attestations.get("openspec_archive")
    if archive is None:
        return ()
    if not archive_authority_valid(archive) or not isinstance(archive, Mapping):
        return ("proof_archive_scope_stale",)
    authorized_value = archive.get("authorized_paths")
    authorized = (
        tuple(str(path) for path in authorized_value)
        if isinstance(authorized_value, tuple | list)
        else ()
    )
    values = facts.get("values")
    fact_values = values if isinstance(values, Mapping) else {}
    changed = fact_values.get("changed_paths")
    changed_paths = (
        tuple(str(path) for path in changed)
        if isinstance(changed, tuple | list) and all(isinstance(path, str) for path in changed)
        else ()
    )
    return () if set(authorized).issubset(changed_paths) else ("proof_archive_scope_stale",)


def commitment_fact_gaps(
    commitment: Commitment,
    facts: Facts,
    prior_attestations: Mapping[str, object],
) -> tuple[str, ...]:
    """Return commitment/fact authority gaps for one proof closure."""
    gaps: list[str] = []
    archive = prior_attestations.get("openspec_archive")
    authorized = (
        tuple(str(path) for path in archive.get("authorized_paths", ()))
        if isinstance(archive, Mapping)
        else ()
    )
    if commitment.subjects and facts.repository not in commitment.subjects:
        gaps.append("repository_subject_mismatch")
    changed = facts.values.get("changed_paths", ())
    gaps.extend(archive_scope_gaps(facts.model_dump(mode="python"), prior_attestations))
    if commitment.scope and (
        not isinstance(changed, tuple | list) or any(not _valid_path(path) for path in changed)
    ):
        gaps.append("changed_paths_invalid")
    elif commitment.scope and any(
        path not in authorized
        and not any(repository_path_matches(path, pattern) for pattern in commitment.scope)
        for path in changed
        if isinstance(path, str)
    ):
        gaps.append("change_scope_exceeded")
    return tuple(gaps)


def validate_proof_plan(
    plan: TransitionPlan,
    commitment: Commitment,
    facts: Facts,
) -> None:
    """Reject a proof plan whose carried semantic projections diverge."""
    policy = mutable_json(plan.policy)
    gates = policy.get("gates") if isinstance(policy, dict) else None
    fact_gate_ids = facts.values.get("gate_ids")
    if fact_gate_ids is None:
        return
    effect = mutable_json(plan.effect)
    expected_effect = {
        "operation": "proof.execute",
        "commitment": plan.inputs.commitment,
        "facts": plan.inputs.facts,
        "policy": plan.inputs.policy,
        "nodes": [node.model_dump(mode="json") for node in plan.nodes],
    }
    if effect != mutable_json(expected_effect):
        message = "transition_plan_effect_mismatch"
        raise ValueError(message)
    semantic_gaps = commitment_fact_gaps(commitment, facts, plan.prior_attestations)
    if any(gap not in plan.required_gaps for gap in semantic_gaps):
        message = "transition_plan_semantics_mismatch"
        raise ValueError(message)
    policy_gaps = policy.get("gaps") if isinstance(policy, dict) else None
    if not isinstance(gates, list) or not isinstance(policy_gaps, list):
        message = "transition_plan_policy_invalid"
        raise TypeError(message)
    if set(facts.values) - _FACT_FIELDS:
        message = "transition_plan_model_gap"
        raise ValueError(message)
    if (
        not _policy_matches_plan(gates, plan)
        or not isinstance(fact_gate_ids, tuple | list)
        or tuple(fact_gate_ids) != tuple(node.id for node in plan.nodes)
        or any(not isinstance(gap, str) or not gap for gap in policy_gaps)
        or any(gap not in plan.required_gaps for gap in policy_gaps)
    ):
        message = "transition_plan_policy_node_mismatch"
        raise ValueError(message)


def _policy_matches_plan(gates: list[object], plan: TransitionPlan) -> bool:
    if any(not isinstance(gate, dict) for gate in gates):
        message = "transition_plan_policy_invalid"
        raise TypeError(message)
    try:
        expected = {
            gate["id"]: (
                tuple(string_sequence(gate["execution_identity"])),
                tuple(sorted(string_sequence(gate["depends_on"]))),
            )
            for gate in gates
            if isinstance(gate, dict)
        }
    except (KeyError, TypeError, ValueError) as error:
        message = "transition_plan_policy_invalid"
        raise ValueError(message) from error
    return len(expected) == len(gates) == len(plan.nodes) and all(
        expected.get(node.id) == (node.command, node.depends_on) for node in plan.nodes
    )


def _valid_path(path: object) -> bool:
    return (
        isinstance(path, str)
        and bool(path)
        and "\\" not in path
        and not PurePosixPath(path).is_absolute()
        and ".." not in PurePosixPath(path).parts
    )
