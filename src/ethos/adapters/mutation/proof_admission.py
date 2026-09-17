"""Admit proof Attestations for one exact local repository query."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.lifecycle.archive_transition import attested_archive_transition
from ethos.adapters.openspec.observation import active_change_names_in_ref
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.proof.plan import archive_scope_gaps
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation
    from ethos.repository.policy.gates import ResolvedGatePolicy


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
    repository_transition: bool = False,
    store: Path,
) -> tuple[Attestation | None, list[str]]:
    """Return one deterministic member of the current exact proof set."""
    admitted, gaps = _admitted_proofs(
        root,
        head,
        repository_transition=repository_transition,
        store=store,
    )
    return (min(admitted, key=lambda item: item.id), []) if admitted else (None, gaps)


def _admitted_proofs(
    root: Path,
    head: str,
    *,
    repository_transition: bool,
    store: Path,
) -> tuple[tuple[Attestation, ...], list[str]]:
    try:
        _selected_root, attestations = read_attestation_set(root)
    except ValueError as error:
        return (), [str(error)]
    matching, gaps = _selected_candidates(head, attestations)
    if gaps:
        return (), gaps
    canonical_policies = (
        ("full", resolve_gate_policy(root, tree_ref=head, full=True)),
        ("default", resolve_gate_policy(root, tree_ref=head)),
    )
    evaluated = tuple(
        (
            item,
            *_candidate_evaluation(
                root,
                head,
                store,
                item,
                canonical_policies=canonical_policies,
                repository_transition=repository_transition,
                attestations=attestations,
            ),
        )
        for item in matching
    )
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
    full_required = canonical_policies[0][1].digest != canonical_policies[1][1].digest
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


def _selected_candidates(
    head: str,
    attestations: tuple[Attestation, ...],
) -> tuple[tuple[Attestation, ...], list[str]]:
    candidates = tuple(
        item
        for item in attestations
        if item.predicate == "proof:execution" and item.subject == f"git:commit:{head}"
    )
    if not candidates:
        return (), ["proof_not_proven"]
    current = tuple(item for item in candidates if _current_at(item, datetime.now(UTC)))
    if not current:
        return (), ["unknown_required_fact"]
    matching = tuple(item for item in current if not _query_gaps(item))
    if matching:
        return matching, []
    return (), list(dict.fromkeys(gap for item in current for gap in _query_gaps(item)))


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


def _bindings(attestation: Attestation) -> tuple[str, ...]:
    return tuple(getattr(attestation, name) for name in _BINDINGS)


def _source_intent_gaps(
    root: Path, head: str, attestation: Attestation, attestations: tuple[Attestation, ...]
) -> list[str]:
    """Match carried acceptance to official meaning at the exact source object."""
    try:
        plan = plan_from_statement(attestation)
        if not openspec_profile_enabled(root, tree_ref=head):
            return [] if plan.commitment is None else ["proof_source_intent_mismatch"]
        if plan.commitment is None:
            observed = active_change_names_in_ref(root, head)
            gaps = list(string_sequence(observed.get("required_gaps")))
            if gaps:
                return gaps
            intent_present = bool(observed["changes"]) or (
                attested_archive_transition(root, head=head, attestations=attestations) is not None
            )
            return ["proof_source_intent_mismatch"] if intent_present else []
        carried = Commitment.model_validate(mutable_json(plan.commitment))
        source = load_openspec_commitment(
            root,
            tree_ref=head,
            change_id=carried.id.removeprefix("change:"),
            attestations=attestations,
        )
    except (TypeError, ValueError) as error:
        return [f"proof_source_intent_unavailable:{error}"]
    return [] if source == carried else ["proof_source_intent_mismatch"]


def _assertion_digest(attestation: Attestation) -> str:
    statement = attestation.payload.body
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


def _lane_proof_gaps(root: Path, facts: Mapping[str, object]) -> list[str]:
    """Match authoring evidence to its lane and independently current Lease."""
    values = facts.get("values")
    generation = values.get("lease_generation") if isinstance(values, Mapping) else None
    branch = current_branch(root)
    if load_branch_role_policy(root).role_for_branch(branch) == ROLE_WORK_LANE and (
        not isinstance(generation, Mapping) or generation.get("lane_ref") != branch
    ):
        return ["proof_lane_mismatch"]
    if isinstance(generation, Mapping):
        current_lease = leases_by_branch(root).get(str(generation.get("lane_ref") or ""), {})
        if current_lease.get("lease_state") != "valid" or mutable_json(generation) != mutable_json(
            lease_generation(current_lease)
        ):
            return ["proof_lease_generation_stale"]
    return []


def _candidate_evaluation(
    root: Path,
    head: str,
    store: Path,
    attestation: Attestation,
    *,
    canonical_policies: tuple[tuple[str, ResolvedGatePolicy], ...],
    repository_transition: bool,
    attestations: tuple[Attestation, ...],
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
    if not repository_transition:
        gaps.extend(_lane_proof_gaps(root, plan.facts))
    if gaps:
        return "", gaps
    gaps.extend(archive_scope_gaps(plan.facts, plan.prior_attestations))
    if gaps:
        return "", gaps
    checks, gaps = artifact_checks(store, attestation)
    if checks is not None and not gaps:
        gaps = proof_statement_gaps(attestation, checks)
    if not gaps and checks is not None and repository_transition:
        gaps = _source_intent_gaps(root, head, attestation, attestations)
    if gaps or checks is None:
        return "", gaps
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
