"""Admit proof Attestations for one exact local repository query."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.commitment import load_repository_commitment
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


@dataclass(frozen=True, slots=True)
class ProofQuery:
    """One transient, non-authorizing proof applicability query."""

    repository: str
    head: str
    commitment_digest: str
    operation: str
    floor: str
    scope: tuple[str, ...]
    plane: str
    boundary: str

    def __post_init__(self) -> None:
        if (
            not self.repository.startswith("repository:")
            or len(self.head) not in {40, 64}
            or set(self.head) - set("0123456789abcdef")
            or len(self.commitment_digest) != 64
            or set(self.commitment_digest) - set("0123456789abcdef")
            or self.operation != "candidate.accept"
            or self.floor not in {"default", "full"}
            or self.scope != ("repository",)
            or self.plane != "local"
            or self.boundary != "repository"
        ):
            message = "proof_query_invalid"
            raise ValueError(message)


def proof_attestation(
    root: Path,
    query: str | ProofQuery,
    *,
    store: Path,
) -> tuple[Attestation | None, list[str]]:
    """Return one deterministic member of the current exact proof set."""
    admitted, gaps = _admitted_proofs(root, query, store=store)
    return (min(admitted, key=lambda item: item.id), []) if admitted else (None, gaps)


def _admitted_proofs(
    root: Path,
    query: str | ProofQuery,
    *,
    store: Path,
) -> tuple[tuple[Attestation, ...], list[str]]:
    try:
        _selected_root, attestations = read_attestation_set(root)
    except ValueError as error:
        return (), [str(error)]
    head = query.head if isinstance(query, ProofQuery) else query
    matching, gaps = _matching_proofs(root, head, query, attestations)
    if gaps:
        return (), gaps
    evaluated = tuple((item, *_candidate_evaluation(root, head, store, item)) for item in matching)
    integrity = _integrity_gaps(evaluated)
    if integrity:
        return (), integrity
    return _select_proof_floor(root, head, query, evaluated)


def _matching_proofs(
    root: Path,
    head: str,
    query: str | ProofQuery,
    attestations: tuple[Attestation, ...],
) -> tuple[tuple[Attestation, ...], list[str]]:
    candidates = tuple(
        item
        for item in attestations
        if item.predicate == "proof:execution" and item.subject == f"git:commit:{head}"
    )
    if not candidates:
        return (), ["proof_not_proven"]
    if isinstance(query, ProofQuery) and (query_gaps := _query_environment_gaps(root, query)):
        return (), query_gaps
    current = tuple(item for item in candidates if _current_at(item, datetime.now(UTC)))
    if not current:
        return (), ["unknown_required_fact"]
    matching = tuple(item for item in current if not _query_gaps(item))
    if not matching:
        return (), list(dict.fromkeys(gap for item in current for gap in _query_gaps(item)))
    return _applicable_proofs(query, matching) if isinstance(query, ProofQuery) else (matching, [])


def _select_proof_floor(
    root: Path,
    head: str,
    query: str | ProofQuery,
    evaluated: tuple[tuple[Attestation, str, list[str]], ...],
) -> tuple[tuple[Attestation, ...], list[str]]:
    valid_by_floor = {
        floor: tuple(
            item
            for item, item_floor, item_gaps in evaluated
            if item_floor == floor and not item_gaps
        )
        for floor in ("full", "default")
    }
    full_required = (
        query.floor == "full"
        if isinstance(query, ProofQuery)
        else resolve_gate_policy(root, tree_ref=head, full=True).digest
        != resolve_gate_policy(root, tree_ref=head).digest
    )
    valid = (
        valid_by_floor[query.floor]
        if isinstance(query, ProofQuery)
        else valid_by_floor["full"]
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


def _applicable_proofs(
    query: ProofQuery, candidates: tuple[Attestation, ...]
) -> tuple[tuple[Attestation, ...], list[str]]:
    evaluated: list[tuple[Attestation, list[str]]] = []
    for item in candidates:
        gaps = [
            *(
                ["proof_attestation_commitment_mismatch"]
                if item.commitment_digest != query.commitment_digest
                else []
            ),
        ]
        if not gaps:
            try:
                plan = plan_from_statement(item)
            except (TypeError, ValueError) as error:
                gaps.append(str(error))
            else:
                if plan.facts.get("repository") != query.repository:
                    gaps.append("proof_attestation_repository_mismatch")
        evaluated.append((item, gaps))
    applicable = tuple(item for item, gaps in evaluated if not gaps)
    if applicable:
        return applicable, []
    return (), list(dict.fromkeys(gap for _item, gaps in evaluated for gap in gaps))


def _query_environment_gaps(root: Path, query: ProofQuery) -> list[str]:
    try:
        repository = load_repository_commitment(root, tree_ref=query.head)
    except ValueError as error:
        return [str(error)]
    required_floor = (
        "full"
        if resolve_gate_policy(root, tree_ref=query.head, full=True).digest
        != resolve_gate_policy(root, tree_ref=query.head).digest
        else "default"
    )
    return next(
        (
            [gap]
            for mismatch, gap in (
                (repository.id != query.repository, "proof_query_repository_mismatch"),
                (
                    repository.digest() != query.commitment_digest,
                    "proof_query_commitment_mismatch",
                ),
                (required_floor != query.floor, "proof_query_floor_mismatch"),
            )
            if mismatch
        ),
        [],
    )


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
        ("default", resolve_gate_policy(root, tree_ref=head)),
        ("full", resolve_gate_policy(root, tree_ref=head, full=True)),
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
