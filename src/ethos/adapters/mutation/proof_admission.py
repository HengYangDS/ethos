"""Admit proof Attestations for one exact local repository query."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.openspec.commitment import admissible_openspec_commitments
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.lifecycle.archive_transition import attested_archive_transition
from ethos.adapters.openspec.observation import active_change_names_in_ref
from ethos.adapters.openspec.selection import requested_change
from ethos.adapters.process import run_command
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.dependency_acceptance import dependency_acceptance_gaps
from ethos.adapters.repo.gate_policy import resolve_proof_policies
from ethos.adapters.repo.git import current_branch
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.proof.plan import archive_scope_gaps
from ethos.contracts.proof.plan import proof_acceptance_purpose
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.value import mutable_json
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from collections.abc import Callable

    from ethos.contracts.proof.plan import AcceptancePurpose
    from ethos.contracts.semantic import Attestation
    from ethos.repository.policy.gates import ResolvedGatePolicy


_BINDINGS = (
    "commitment_digest",
    "facts_digest",
    "plan_digest",
    "policy_digest",
    "effect_digest",
)


def predecessor_policy_gaps(root: Path, head: str, proof: Attestation) -> list[str]:
    """Compare the exact proof policy with the installed hook's read-only plan."""
    try:
        selected = current_runtime(Path(git_common_dir(root)))
    except (OSError, ValueError) as error:
        return [str(error) or "predecessor_runtime_unavailable"]
    if selected.build == invoking_build_identity():
        return []
    candidate = plan_from_statement(proof)
    command = [
        selected.python.as_posix(),
        "-B",
        "-I",
        "-m",
        "ethos.cli",
        "prove",
        "--full",
        "--expect-head",
        head,
        "--root",
        root.as_posix(),
        "--json",
    ]
    purpose = proof_acceptance_purpose(candidate.policy)
    if purpose != "repository":
        command.extend(("--acceptance-purpose", purpose))
    change = (
        str(candidate.commitment.get("id") or "").removeprefix("change:")
        if isinstance(candidate.commitment, Mapping)
        else ""
    )
    if change:
        command.extend(("--change", change))
    try:
        completed = run_command(root, tuple(command), timeout=60, remove_env_prefixes=("GIT_",))
    except subprocess.TimeoutExpired:
        return ["predecessor_policy_probe_timeout"]
    except (OSError, ValueError):
        return ["predecessor_policy_probe_unavailable"]
    predecessor, gaps = _predecessor_plan(completed.stdout, head)
    if predecessor is None or gaps:
        return gaps or ["predecessor_policy_probe_invalid"]
    return (
        []
        if (
            candidate.inputs.policy == predecessor.inputs.policy
            and candidate.nodes == predecessor.nodes
            and candidate.policy == predecessor.policy
        )
        else ["proof_attestation_repository_policy_mismatch"]
    )


def _predecessor_plan(stdout: str, head: str) -> tuple[TransitionPlan | None, list[str]]:
    """Extract the installed reader's exact policy without treating dry-run as proof."""
    try:
        report = json.loads(stdout)
    except (TypeError, ValueError):
        return None, ["predecessor_policy_probe_invalid"]
    data = report.get("data") if isinstance(report, dict) else None
    binding = data.get("expected_head") if isinstance(data, dict) else None
    raw_gaps = report.get("required_gaps") if isinstance(report, dict) else None
    if not (
        isinstance(report, dict)
        and report.get("command") == "prove"
        and isinstance(data, dict)
        and isinstance(binding, dict)
        and binding.get("expected") == head
        and binding.get("current") == head
        and binding.get("matches") is True
        and isinstance(raw_gaps, list)
        and all(isinstance(gap, str) for gap in raw_gaps)
    ):
        return None, ["predecessor_policy_probe_invalid"]
    gaps = [gap for gap in raw_gaps if gap != "full_proof_requires_execute"]
    if gaps:
        return None, gaps
    try:
        predecessor = TransitionPlan.model_validate(data.get("transition_plan"))
    except (TypeError, ValueError):
        return None, ["predecessor_policy_probe_invalid"]
    return predecessor, list(predecessor.required_gaps)


def unavailable_proof_admission() -> dict[str, object]:
    """Project a proof admission that cannot be selected for an inadmissible target."""
    return {
        "verdict": "block",
        "state": "unavailable",
        "selection": "",
        "attestation": {},
        "required_gaps": [],
        "next_action": "",
    }


def proof_attestation(
    root: Path,
    head: str,
    *,
    repository_transition: bool = False,
    store: Path,
    attestation_id: str = "",
    change_id: str | None = None,
    acceptance_purpose: AcceptancePurpose = "repository",
) -> tuple[Attestation | None, list[str]]:
    """Return one deterministic member of the current exact proof set."""
    admitted, gaps = _admitted_proofs(
        root,
        head,
        repository_transition=repository_transition,
        store=store,
        attestation_id=attestation_id,
        change_id=change_id,
        acceptance_purpose=acceptance_purpose,
    )
    if not admitted:
        return None, gaps
    if attestation_id:
        selected = next((item for item in admitted if item.id == attestation_id), None)
        return selected, [] if selected else ["proof_attestation_selection_missing"]
    return min(admitted, key=lambda item: item.id), []


def _purpose_candidates(
    matching: tuple[Attestation, ...],
    purpose: AcceptancePurpose,
    attestation_id: str,
) -> tuple[tuple[Attestation, ...], list[str]]:
    """Select one proof purpose without obscuring a genuinely missing explicit ID."""
    try:
        selected = tuple(
            item
            for item in matching
            if proof_acceptance_purpose(plan_from_statement(item).policy) == purpose
        )
    except (TypeError, ValueError) as error:
        return (), [str(error)]
    wrong_id = (
        attestation_id
        and any(item.id == attestation_id for item in matching)
        and all(item.id != attestation_id for item in selected)
    )
    return (
        ((), ["proof_acceptance_purpose_mismatch"]) if not selected or wrong_id else (selected, [])
    )


def _floor_candidates(
    evaluated: tuple[tuple[Attestation, str, list[str]], ...], *, full_required: bool
) -> tuple[tuple[Attestation, ...], list[str]]:
    """Select the required canonical proof floor and explain its absence."""
    valid_by_floor = {
        floor: tuple(
            item
            for item, item_floor, item_gaps in evaluated
            if item_floor == floor and not item_gaps
        )
        for floor in ("full", "default")
    }
    valid = (
        valid_by_floor["full"]
        if full_required
        else next((items for items in valid_by_floor.values() if items), ())
    )
    if valid:
        return valid, []
    gaps = (
        ["full_proof_required"]
        if full_required and valid_by_floor["default"]
        else list(dict.fromkeys(gap for _item, _floor, item_gaps in evaluated for gap in item_gaps))
    )
    return (), gaps


def _admitted_proofs(
    root: Path,
    head: str,
    *,
    repository_transition: bool,
    store: Path,
    attestation_id: str,
    change_id: str | None,
    acceptance_purpose: AcceptancePurpose,
) -> tuple[tuple[Attestation, ...], list[str]]:
    try:
        _selected_root, attestations = read_attestation_set(root)
    except ValueError as error:
        return (), [str(error)]
    matching, gaps = _selected_candidates(head, attestations)
    if gaps:
        return (), gaps
    matching, gaps = _purpose_candidates(matching, acceptance_purpose, attestation_id)
    if gaps:
        return (), gaps
    canonical_policies = resolve_proof_policies(
        root, tree_ref=head, acceptance_purpose=acceptance_purpose
    )

    @cache
    def source_intent(change: str) -> tuple[Commitment, ...]:
        """Share exact-source interpretation only inside this fresh proof query."""
        return admissible_openspec_commitments(
            root, tree_ref=head, change_id=change, attestations=attestations
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
                source_intent=source_intent,
            ),
        )
        for item in matching
    )
    integrity = _integrity_gaps(evaluated)
    if integrity:
        return (), integrity
    evaluated, gaps = _intent_candidates(
        root, head, evaluated, attestation_id, change_id=change_id, source_intent=source_intent
    )
    if gaps:
        return (), gaps
    valid, set_gaps = _floor_candidates(
        evaluated, full_required=canonical_policies[0][1].digest != canonical_policies[1][1].digest
    )
    if len({_bindings(item, repository_transition=repository_transition) for item in valid}) > 1:
        set_gaps = ["stale_binding"]
    elif len({_assertion_digest(item) for item in valid}) > 1:
        set_gaps = ["contradiction"]
    if not set_gaps and attestation_id:
        selected_gaps = next(
            (item_gaps for item, _floor, item_gaps in evaluated if item.id == attestation_id),
            [],
        )
        set_gaps = list(selected_gaps)
    return ((), set_gaps) if set_gaps else (valid, [])


def _intent_candidates(
    root: Path,
    head: str,
    evaluated: tuple[tuple[Attestation, str, list[str]], ...],
    attestation_id: str,
    *,
    change_id: str | None,
    source_intent: Callable[[str], tuple[Commitment, ...]],
) -> tuple[tuple[tuple[Attestation, str, list[str]], ...], list[str]]:
    """Select an intent query without hiding malformed evidence or same-intent conflicts."""
    intent_digest = None
    if attestation_id:
        selected = next(
            (item for item, _floor, _gaps in evaluated if item.id == attestation_id), None
        )
        if selected is None:
            return (), ["proof_attestation_selection_missing"]
        intent_digest = selected.commitment_digest
    change = change_id if attestation_id else requested_change(change_id)
    if change is not None and openspec_profile_enabled(root, tree_ref=head):
        try:
            requested = tuple(commitment.digest() for commitment in source_intent(change))
        except (TypeError, ValueError) as error:
            return (), [f"proof_source_intent_unavailable:{error}"]
        if intent_digest is not None and intent_digest not in requested:
            return (), ["proof_attestation_intent_mismatch"]
        carried = {row[0].commitment_digest for row in evaluated}
        intent_digest = intent_digest or next(
            (digest for digest in requested if digest in carried), requested[0]
        )
    if intent_digest is None:
        return evaluated, []
    selected_rows = tuple(row for row in evaluated if row[0].commitment_digest == intent_digest)
    return (selected_rows, []) if selected_rows else ((), ["proof_not_proven"])


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
        "proof_attestation_repository_policy_mismatch",
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


def _bindings(attestation: Attestation, *, repository_transition: bool) -> tuple[str, ...]:
    """Compare accepted meaning after validating each execution's complete binding."""
    fields = ("commitment_digest", "policy_digest") if repository_transition else _BINDINGS
    return tuple(getattr(attestation, name) for name in fields)


def _source_intent_gaps(
    root: Path,
    head: str,
    plan: TransitionPlan,
    attestations: tuple[Attestation, ...],
    *,
    source_intent: Callable[[str], tuple[Commitment, ...]],
) -> list[str]:
    """Match carried acceptance to official meaning at the exact source object."""
    try:
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
        sources = source_intent(carried.id.removeprefix("change:"))
    except (TypeError, ValueError) as error:
        return [f"proof_source_intent_unavailable:{error}"]
    return [] if carried in sources else ["proof_source_intent_mismatch"]


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
    source_intent: Callable[[str], tuple[Commitment, ...]],
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
    if not gaps:
        gaps.extend(archive_scope_gaps(plan.facts, plan.prior_attestations))
    if gaps:
        return "", gaps
    checks, gaps = artifact_checks(store, attestation)
    if checks is not None and not gaps:
        gaps = proof_statement_gaps(attestation, checks)
    if not gaps and checks is not None and repository_transition:
        gaps = _source_intent_gaps(root, head, plan, attestations, source_intent=source_intent)
    if gaps or checks is None:
        return "", gaps
    gaps = dependency_acceptance_gaps(
        root,
        head,
        plan.policy,
        checks,
        acceptance_purpose=proof_acceptance_purpose(plan.policy),
    )
    if gaps:
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
