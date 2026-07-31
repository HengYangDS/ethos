"""Admit current proof Attestations for one exact repository query."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import scan_attestations
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.contracts.authority import AuthorityQuery
from ethos.contracts.authority import CarrierDescriptor
from ethos.contracts.authority import resolve_authority
from ethos.repository.policy.gates import resolve_gate_policy

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def proof_attestation(
    root: Path, head: str, *, store: Path
) -> tuple[Attestation | None, list[str]]:
    """Return the current repository proof or its fail-closed gaps."""
    attestations, store_gaps = scan_attestations(store)
    candidates = tuple(
        attestation
        for attestation in attestations
        if attestation.predicate == "proof:execution"
        and attestation.subject == f"git:commit:{head}"
    )
    if store_gaps or not candidates:
        return None, store_gaps or ["proof_not_proven"]
    validity = datetime.now(UTC)
    current = tuple(item for item in candidates if _current_at(item, validity))
    if not current:
        return None, ["unknown_required_fact"]
    evaluated = [(item, _candidate_gaps(root, head, store, item)) for item in current]
    integrity = [
        gap
        for _item, gaps in evaluated
        for gap in gaps
        if (
            gap.startswith("proof_attestation_")
            or gap in {"model_gap", "proof_policy_digest_stale"}
        )
        and gap
        not in {
            "proof_attestation_verdict_block",
            "proof_attestation_verdict_unknown",
            "proof_attestation_check_not_passed",
        }
    ]
    if integrity:
        return None, list(dict.fromkeys(integrity))
    valid = tuple(item for item, gaps in evaluated if not gaps)
    if valid:
        descriptors = tuple(_descriptor(item, validity) for item in valid)
        query = _query(head, validity)
        mismatched = tuple(descriptor for descriptor in descriptors if descriptor.query != query)
        if mismatched:
            if len(mismatched) != len(descriptors):
                return None, ["contradiction"]
            mismatch_gaps = [
                gap
                for descriptor in mismatched
                for gap, differs in (
                    ("proof_attestation_scope_mismatch", descriptor.query.scope != query.scope),
                    ("proof_attestation_plane_mismatch", descriptor.query.plane != query.plane),
                    (
                        "proof_attestation_context_mismatch",
                        descriptor.query.context != query.context,
                    ),
                )
                if differs
            ]
            return None, list(dict.fromkeys(mismatch_gaps)) or ["model_gap"]
        resolution = resolve_authority(query, descriptors)
        selected = max(valid, key=lambda item: (item.issued_at, item.id))
        result = (selected, [])
        if resolution.verdict != "pass":
            result = (None, list(resolution.required_gaps))
        return result
    return None, max(evaluated, key=lambda item: (item[0].issued_at, item[0].id))[1]


def _current_at(attestation: Attestation, instant: datetime) -> bool:
    return (attestation.valid_from or attestation.issued_at) <= instant and (
        attestation.valid_until is None or instant <= attestation.valid_until
    )


def _candidate_gaps(root: Path, head: str, store: Path, attestation: Attestation) -> list[str]:
    if attestation.subject != f"git:commit:{head}" or attestation.statement.get("head") != head:
        return ["proof_attestation_head_mismatch"]
    try:
        plan = plan_from_statement(attestation)
    except (TypeError, ValueError) as error:
        return [str(error)]
    if plan.facts.get("head") != head:
        return ["proof_attestation_plan_head_mismatch"]
    checks, gaps = artifact_checks(store, attestation)
    if gaps or checks is None:
        return gaps
    return [
        *proof_statement_gaps(attestation, checks),
        *_policy_gaps(root, head, checks, policy_digest=plan.inputs.policy),
    ]


def _policy_gaps(
    root: Path,
    head: str,
    checks: tuple[dict[str, object], ...],
    *,
    policy_digest: str,
) -> list[str]:
    policy = resolve_gate_policy(root, tree_ref=head)
    present = {str(check["action_id"]) for check in checks}
    missing = sorted(gate_id for gate_id in policy.gate_ids if gate_id not in present)
    selected = resolve_gate_policy(
        root, tree_ref=head, gate_ids=tuple(str(check["action_id"]) for check in checks)
    )
    return [
        *(["proof_policy_digest_stale"] if selected.digest != policy_digest else []),
        *([f"proof_incomplete:{','.join(missing)}"] if missing else []),
        *selected.conformance_gaps(list(checks)),
    ]


def _query(
    head: str,
    validity: datetime,
    *,
    scope: tuple[str, ...] = ("repository",),
    plane: str = "local",
    boundary: str = "repository",
) -> AuthorityQuery:
    return AuthorityQuery(
        subject=f"git:commit:{head}",
        predicate="proof:execution",
        scope=scope,
        plane=plane,
        validity=validity,
        context=(("boundary", boundary),),
    )


def _descriptor(attestation: Attestation, validity: datetime) -> CarrierDescriptor:
    statement = attestation.model_dump(mode="json")["statement"]
    bindings = tuple(
        (name, value)
        for name in (
            "commitment_digest",
            "facts_digest",
            "plan_digest",
            "policy_digest",
            "effect_digest",
        )
        if (value := getattr(attestation, name))
    )
    return CarrierDescriptor(
        role="fact",
        declared_authority=True,
        query=_query(
            attestation.subject.removeprefix("git:commit:"),
            validity,
            scope=tuple(str(item) for item in statement["scope"]),
            plane=str(statement["plane"]),
            boundary=str(statement["boundary"]),
        ),
        assertion={
            "claim": statement.get("claim"),
            "repository": statement.get("repository"),
            "scope": statement.get("scope"),
            "plane": statement.get("plane"),
            "context": statement.get("context"),
            "boundary": statement.get("boundary"),
            "required_gaps": statement.get("required_gaps"),
            "verifier": attestation.verifier,
        },
        bindings=bindings,
        source=f"attestation:{attestation.id}",
        valid_from=attestation.valid_from or attestation.issued_at,
        valid_until=attestation.valid_until,
    )


def plan_for_attestation(root: Path, attestation: Attestation, *, store: Path):
    """Return the exact transient plan after current proof admission."""
    selected, gaps = proof_attestation(
        root, attestation.subject.removeprefix("git:commit:"), store=store
    )
    if gaps or selected is None or selected.id != attestation.id:
        raise ValueError(gaps[0] if gaps else "proof_attestation_not_current")
    return plan_from_statement(attestation)
