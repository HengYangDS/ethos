"""Root planning command."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Annotated
from typing import cast

from cyclopts import Parameter

from ethos.adapters.openspec.archive_effect import archive_effect_authority
from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.openspec.profile import load_work_lane_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.coordination import collaboration_competition_projection
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import ref_progress
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.assistants.playbooks import playbooks_report
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.plan import compile_plan
from ethos.contracts.review import compile_review_plan
from ethos.contracts.review import load_review_lens_declaration
from ethos.contracts.review import load_review_results
from ethos.contracts.review import reduce_review_results
from ethos.contracts.semantic import Facts
from ethos.contracts.skill.activation import compile_skill_activation
from ethos.domain.plan import matching_rule_gates
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.gates import resolve_gate_policy
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

if TYPE_CHECKING:
    from pathlib import Path


def _non_negative(_type: type[int], value: int | None) -> None:
    if value is not None and value < 0:
        msg = "proof node capacity must be non-negative"
        raise ValueError(msg)


def _peer_proof_cost(repo: Path, lane: dict[str, object]) -> int | None:
    paths = tuple(string_sequence(lane.get("path_scope")))
    if lane.get("scope_state") != "bounded" or not paths:
        return None
    _rules, gates, gaps = matching_rule_gates(repo, paths)
    if gaps:
        return None
    gate_ids = tuple(str(gate.get("id") or "") for gate in gates)
    return len(resolve_gate_policy(repo, gate_ids=gate_ids).nodes)


def _archive_plan_authority(
    repo: Path,
    *,
    head: str,
    repository_id: str,
    commitment,
    lease: dict[str, object],
    paths: tuple[str, ...],
    work_lane: bool,
) -> dict[str, object]:
    return (
        archive_effect_authority(
            repo,
            head=head,
            repository_id=repository_id,
            commitment=commitment,
            lease=lease,
            changed_paths=paths,
        )
        if work_lane and paths
        else {}
    )


@app.command
def plan(
    *,
    changed: bool = False,
    change: str | None = None,
    proof_node_capacity: Annotated[
        int | None,
        Parameter(name="--proof-node-capacity", validator=_non_negative),
    ] = None,
    review_results: Annotated[str | None, Parameter(name="--review-results")] = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Compile deterministic TransitionPlan."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo)
    paths = change_scope_paths_from_status(repo, status_payload) if changed else ()
    try:
        lease = (
            leases_by_branch(repo).get(str(status_payload.get("branch") or ""), {})
            if status_payload.get("role") == ROLE_WORK_LANE
            else {}
        )
        commitment = (
            load_work_lane_commitment(
                repo,
                change_id=change,
                lease=lease,
            )
            if status_payload.get("role") == ROLE_WORK_LANE
            else load_profile_commitment(repo, change_id=change)
        )
    except ValueError as exc:
        gap = str(exc)
        if gap == INVALID_PROFILE_ERROR:
            raise
        emit(
            EthosResult(
                command="plan",
                verdict="block",
                state="gapped",
                required_gaps=(gap,),
                next_action="repair or select the Commitment carrier",
            ),
            json_output=json_output,
            enforce=False,
        )
        return
    head = str(status_payload.get("head") or "")
    repository = load_repository_commitment(repo)
    matched_rules, required_gates, rule_validation_gaps = matching_rule_gates(repo, paths)
    profile_adapter: dict[str, object] = {}
    intent_context: dict[str, object] = {}
    intent_gaps: tuple[str, ...] = ()
    if openspec_profile_enabled(repo):
        profile_adapter = openspec_governance_report(
            repo,
            change=change,
            lifecycle=True,
            changed_paths=paths,
            require_workspace=False,
        )
        intent_context = cast("dict[str, object]", profile_adapter.get("intent_context") or {})
        intent_gaps = tuple(
            gap
            for gap in string_sequence(profile_adapter.get("required_gaps"))
            if gap == "model_gap"
        )
    tree = current_tree(repo, head)
    review_plan = compile_review_plan(
        load_review_lens_declaration(repo / "system" / "review-lenses.toml"),
        {
            "head": head,
            "tree": tree,
            "workload": intent_context.get("schema", "spec-driven"),
            "phase": "post-implementation" if paths else "pre-implementation",
            "affected_capabilities": intent_context.get("affected_capabilities", []),
            "ambiguities": intent_context.get("ambiguities", []),
            "conflicts": intent_context.get("conflicts", []),
            "risks": list(commitment.risks),
            "changed_paths": list(paths),
            "requirements": intent_context.get("requirements", []),
            "requirement_edges": intent_context.get("requirement_edges", []),
        },
    )
    review_decision = None
    review_result_gaps: tuple[str, ...] = ()
    if review_results is not None:
        try:
            review_decision = reduce_review_results(
                review_plan,
                load_review_results(review_results),
            )
        except ValueError as error:
            review_result_gaps = (str(error),)
    facts = Facts(
        repository=repository.id,
        head=head,
        tree=tree,
        observed_at=datetime.now(UTC),
        values={
            "branch": status_payload.get("branch", ""),
            "role": status_payload.get("role", ""),
            "dirty": status_payload.get("dirty", False),
            "changed_paths": paths,
            "intent_context": intent_context,
            "review_plan": review_plan.model_dump(mode="json"),
        },
        source_refs=(
            "git:HEAD",
            "git:HEAD^{tree}",
            "ethos:status",
            "system/review-lenses.toml",
        ),
    )
    adapter_gaps = tuple(string_sequence(profile_adapter.get("required_gaps")))
    profile_projection = {key: value for key, value in profile_adapter.items() if key != "commands"}
    gate_ids = tuple(str(gate.get("id") or "") for gate in required_gates)
    policy = resolve_gate_policy(repo, gate_ids=gate_ids)
    archive_authority = _archive_plan_authority(
        repo,
        head=head,
        repository_id=repository.id,
        commitment=commitment,
        lease=lease,
        paths=paths,
        work_lane=status_payload.get("role") == ROLE_WORK_LANE,
    )
    foreign = cast("list[dict[str, object]]", status_payload.get("foreign_work_lanes") or [])
    peers = [lane | {"proof_cost": _peer_proof_cost(repo, lane)} for lane in foreign]
    candidate = cast("dict[str, object]", status_payload.get("candidate") or {})
    candidate_branch = str(candidate.get("branch") or "candidate/dev")
    strategy = collaboration_competition_projection(
        peers,
        commitment_digest=commitment.digest(),
        risks=commitment.risks,
        proof_cost=len(policy.nodes),
        proof_capacity=proof_node_capacity,
        observed_at=facts.observed_at,
        candidate=ref_progress(repo, candidate_branch, observed_at=facts.observed_at)
        | {"behind_accepted": candidate.get("behind_accepted", 0)},
    )
    plan = compile_plan(
        commitment,
        facts,
        policy.nodes,
        policy=policy.projection,
        prior_attestations=({"openspec_archive": archive_authority} if archive_authority else {}),
        required_gaps=tuple(dict.fromkeys((*rule_validation_gaps, *policy.gaps, *intent_gaps))),
    )
    playbooks = playbooks_report(repo)
    skill_activation = compile_skill_activation(
        cast("dict[str, object]", playbooks.get("registry") or {}),
        operation="plan",
        subjects=tuple(str(subject) for subject in commitment.subjects),
        changed_paths=paths,
    )
    required_gaps = tuple(
        dict.fromkeys(
            (
                *plan.required_gaps,
                *adapter_gaps,
                *rule_validation_gaps,
                *skill_activation.required_gaps,
                *review_plan.required_gaps,
                *review_result_gaps,
                *(review_decision.required_gaps if review_decision is not None else ()),
            )
        )
    )
    ok = (
        plan.verdict == "pass"
        and not adapter_gaps
        and not rule_validation_gaps
        and skill_activation.verdict == "pass"
        and review_plan.verdict == "pass"
        and not review_result_gaps
        and (review_decision is None or review_decision.verdict == "pass")
    )
    result = EthosResult(
        command="plan",
        verdict="pass" if ok else "block" if required_gaps else "unknown",
        state="planned" if ok else "gapped",
        summary={
            "changed": changed,
            "plan_node_count": len(plan.nodes),
            "matched_rule_count": len(matched_rules),
            "required_gate_count": len(required_gates),
            "required_skill_count": len(skill_activation.skills),
            "required_review_lens_count": len(review_plan.lenses),
        },
        required_gaps=required_gaps,
        next_action="ethos prove --json"
        if ok
        else (
            "repair .ethos/rules.toml and rerun ethos plan --json"
            if rule_validation_gaps
            else "repair the review result file and rerun ethos plan --json"
            if review_result_gaps
            else review_decision.next_action
            if review_decision is not None and review_decision.verdict != "pass"
            else "repair the selected Commitment carrier"
        ),
        data={
            "changed_paths": list(paths),
            "matched_rules": matched_rules,
            "required_gates": required_gates,
            "rule_validation_gaps": rule_validation_gaps,
            "commitment": commitment.model_dump(mode="json"),
            "facts_digest": facts.digest(),
            "intent_context": intent_context,
            "transition_plan": plan.model_dump(mode="json"),
            "skill_activation": skill_activation.model_dump(mode="json"),
            "review_plan": review_plan.model_dump(mode="json"),
            **(
                {"review_decision": review_decision.model_dump(mode="json")}
                if review_decision is not None
                else {}
            ),
            "coordination_strategy": strategy,
            **({"profile_adapter": profile_projection} if profile_projection else {}),
        },
    )
    emit(result, json_output=json_output, enforce=False, artifact_root=repo)
