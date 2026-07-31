"""Admit proof Attestations for one exact local repository query."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import scan_attestations
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.policy.gates import resolve_gate_policy

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan
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
    expected_plan: TransitionPlan | None = None,
) -> tuple[Attestation | None, list[str]]:
    """Return one deterministic member of the current exact proof set."""
    admitted, gaps = _admitted_proofs(root, head, store=store, expected_plan=expected_plan)
    return (min(admitted, key=lambda item: item.id), []) if admitted else (None, gaps)


def _admitted_proofs(
    root: Path,
    head: str,
    *,
    store: Path,
    expected_plan: TransitionPlan | None = None,
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
    if expected_plan is not None:
        matching = tuple(item for item in matching if _plan_matches(item, expected_plan))
        if not matching:
            return (), ["proof_not_proven"]
    evaluated = tuple((item, _candidate_gaps(root, head, store, item)) for item in matching)
    integrity = _integrity_gaps(evaluated)
    if integrity:
        return (), integrity
    valid = tuple(item for item, item_gaps in evaluated if not item_gaps)
    if not valid:
        return (), list(dict.fromkeys(gap for _item, item_gaps in evaluated for gap in item_gaps))
    bindings = {_bindings(item) for item in valid}
    if len(bindings) > 1:
        return (), ["stale_binding"]
    meanings = {_assertion_digest(item) for item in valid}
    if len(meanings) > 1:
        return (), ["contradiction"]
    return valid, []


def _integrity_gaps(evaluated: tuple[tuple[Attestation, list[str]], ...]) -> list[str]:
    ignored = {
        "proof_attestation_verdict_block",
        "proof_attestation_verdict_unknown",
        "proof_attestation_check_not_passed",
    }
    return list(
        dict.fromkeys(
            gap
            for _item, gaps in evaluated
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


def _plan_matches(attestation: Attestation, expected: TransitionPlan) -> bool:
    try:
        plan = plan_from_statement(attestation)
    except (TypeError, ValueError):
        return False
    return plan.digest == expected.digest


def _assertion_digest(attestation: Attestation) -> str:
    statement = attestation.statement
    return canonical_json_digest(
        {
            "claim": statement.get("claim"),
            "repository": statement.get("repository"),
            "scope": statement.get("scope"),
            "plane": statement.get("plane"),
            "context": statement.get("context"),
            "boundary": statement.get("boundary"),
            "required_gaps": statement.get("required_gaps"),
            "verifier": attestation.verifier,
        }
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


def plan_for_attestation(root: Path, attestation: Attestation, *, store: Path):
    """Return the exact transient plan for any member of the current proof set."""
    plan = plan_from_statement(attestation)
    admitted, gaps = _admitted_proofs(
        root,
        attestation.subject.removeprefix("git:commit:"),
        store=store,
        expected_plan=plan,
    )
    if gaps or attestation.id not in {item.id for item in admitted}:
        raise ValueError(gaps[0] if gaps else "proof_attestation_not_current")
    return plan


def evidence_digest(
    root: Path,
    head: str,
    *,
    store: Path,
    expected_plan: TransitionPlan | None = None,
) -> str:
    """Return the stable semantic identity of one admitted proof set."""
    admitted, gaps = _admitted_proofs(root, head, store=store, expected_plan=expected_plan)
    if gaps or not admitted:
        return ""
    return canonical_json_digest(
        {"bindings": _bindings(admitted[0]), "assertion": _assertion_digest(admitted[0])}
    )
