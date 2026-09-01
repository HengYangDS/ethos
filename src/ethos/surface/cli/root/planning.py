"""Root planning command."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import cast

from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.adapters.repo.coordination import collaboration_competition_projection
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import ref_progress
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.workspace import workspace_status_observation
from ethos.assistants.playbooks import playbooks_report
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from ethos.contracts.skill.activation import compile_skill_activation
from ethos.domain.land.closeout import closeout_command_from_status
from ethos.domain.plan import matching_rule_gates
from ethos.normalization.coercion import string_sequence
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@app.command
def plan(
    *,
    changed: bool = False,
    change: str | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Compile deterministic TransitionPlan."""
    repo = resolve_root(root)
    status_payload, authority = workspace_status_observation(repo)
    closeout_action = closeout_command_from_status(repo, status_payload)
    if closeout_action:
        candidate = cast("dict[str, object]", status_payload.get("candidate") or {})
        emit(
            EthosResult(
                command="plan",
                verdict="pass",
                state="planned",
                summary={"changed": changed, "operation": "accepted_closeout"},
                next_action=closeout_action,
                data={
                    "authority": authority.projection() if authority is not None else {},
                    "accepted_head": str(status_payload.get("head") or ""),
                    "candidate_branch": str(candidate.get("branch") or ""),
                    "candidate_head": str(candidate.get("head") or ""),
                    "closeout_support": cast(
                        "dict[str, object]", status_payload.get("closeout_support") or {}
                    ),
                },
            ),
            json_output=json_output,
            enforce=False,
        )
        return
    head = str(status_payload.get("head") or "")
    try:
        repository = repository_identity(repo)
    except ValueError as exc:
        gap = str(exc)
        emit(
            EthosResult(
                command="plan",
                verdict="block",
                state="gapped",
                required_gaps=(gap,),
                next_action="repair .ethos/profile.toml",
            ),
            json_output=json_output,
            enforce=False,
        )
        return
    observed_paths = status_payload.get("changed_paths")
    authority_ready = status_payload.get("role") != "work_lane" or (
        authority is not None and authority.verdict == "pass"
    )
    if (
        changed
        and change is None
        and authority_ready
        and isinstance(observed_paths, list | tuple)
        and not observed_paths
    ):
        emit(
            EthosResult(
                command="plan",
                verdict="pass",
                state="no_changes",
                summary={
                    "changed": False,
                    "plan_node_count": 0,
                    "matched_rule_count": 0,
                    "required_gate_count": 0,
                    "required_skill_count": 0,
                },
                data={
                    "changed_paths": [],
                    "selected_carrier": "",
                    "path_attributions": [],
                    "matched_rules": [],
                    "required_gates": [],
                },
            ),
            json_output=json_output,
            enforce=False,
            artifact_root=repo,
        )
        return
    try:
        generation = resolve_current_resolution(
            repo,
            status=status_payload,
            authority=authority,
            change=change,
            changed=changed,
        )
    except ValueError as exc:
        if str(exc) == INVALID_PROFILE_ERROR:
            raise
        raise
    if generation.verdict != "pass" or generation.commitment is None:
        emit(
            EthosResult(
                command="plan",
                verdict=generation.verdict,
                state="gapped",
                required_gaps=generation.required_gaps,
                next_action=generation.next_action,
                user_decision_required=generation.user_decision_required,
            ),
            json_output=json_output,
            enforce=False,
        )
        return
    commitment, generation_scope = generation.commitment, generation.scope
    paths = generation_scope.paths
    matched_rules, required_gates, rule_validation_gaps = matching_rule_gates(repo, paths)
    profile_adapter = generation.openspec
    intent_context = cast("dict[str, object]", profile_adapter.get("intent_context") or {})
    tree = current_tree(repo, head)
    facts = Facts(
        repository=repository,
        head=head,
        tree=tree,
        observed_at=datetime.now(UTC),
        values={
            "branch": status_payload.get("branch", ""),
            "role": status_payload.get("role", ""),
            "dirty": status_payload.get("dirty", False),
            "changed_paths": paths,
            "intent_context": intent_context,
            "selected_carrier": generation_scope.selected_carrier,
            "path_attributions": generation_scope.attribution_projection(),
        },
        source_refs=(
            "git:HEAD",
            "git:HEAD^{tree}",
            "ethos:status",
        ),
    )
    adapter_gaps = tuple(string_sequence(profile_adapter.get("required_gaps")))
    profile_projection = {key: value for key, value in profile_adapter.items() if key != "commands"}
    gate_ids = tuple(str(gate.get("id") or "") for gate in required_gates)
    policy = resolve_gate_policy(repo, gate_ids=gate_ids)
    archive_authority = generation_scope.archive_authority
    prior_attestations = {"openspec_archive": archive_authority} if archive_authority else {}
    foreign = cast("list[dict[str, object]]", status_payload.get("foreign_work_lanes") or [])
    candidate = cast("dict[str, object]", status_payload.get("candidate") or {})
    candidate_branch = str(candidate.get("branch") or "candidate/dev")
    strategy = collaboration_competition_projection(
        foreign,
        observed_at=facts.observed_at,
        candidate=ref_progress(repo, candidate_branch, observed_at=facts.observed_at)
        | {"behind_accepted": candidate.get("behind_accepted", 0)},
    )
    plan = compile_plan(
        commitment,
        facts,
        policy.nodes,
        policy=policy.projection,
        prior_attestations=prior_attestations,
        required_gaps=tuple(
            dict.fromkeys((*generation_scope.gaps, *rule_validation_gaps, *policy.gaps))
        ),
    )
    playbooks = playbooks_report(repo)
    skill_activation = compile_skill_activation(
        cast("dict[str, object]", playbooks.get("registry") or {}),
        operation="plan",
        subjects=(commitment.id,),
        changed_paths=paths,
    )
    required_gaps = tuple(
        dict.fromkeys(
            (
                *plan.required_gaps,
                *adapter_gaps,
                *rule_validation_gaps,
                *skill_activation.required_gaps,
            )
        )
    )
    ok = (
        plan.verdict == "pass"
        and not adapter_gaps
        and not rule_validation_gaps
        and skill_activation.verdict == "pass"
    )
    authority_projection = authority.projection() if authority is not None else {}
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
        },
        required_gaps=required_gaps,
        next_action=closeout_action
        or (
            "ethos prove --json"
            if ok
            else (
                "repair .ethos/rules.toml and rerun ethos plan --json"
                if rule_validation_gaps
                else "repair or select the official OpenSpec Change"
            )
        ),
        data={
            "authority": authority_projection,
            "changed_paths": list(paths),
            "selected_carrier": generation_scope.selected_carrier,
            "path_attributions": list(generation_scope.attribution_projection()),
            "matched_rules": matched_rules,
            "required_gates": required_gates,
            "rule_validation_gaps": rule_validation_gaps,
            "commitment": commitment.model_dump(mode="json"),
            "facts_digest": facts.digest(),
            "intent_context": intent_context,
            "transition_plan": plan.model_dump(mode="json"),
            "skill_activation": skill_activation.model_dump(mode="json"),
            "coordination_strategy": strategy,
            **({"profile_adapter": profile_projection} if profile_projection else {}),
        },
    )
    emit(result, json_output=json_output, enforce=False, artifact_root=repo)
