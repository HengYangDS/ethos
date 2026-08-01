"""Root planning command."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

from ethos.adapters.openspec.commitment import openspec_profile_enabled
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
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
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    paths = change_scope_paths_from_status(repo, status_payload) if changed else ()
    try:
        support = status_payload.get("closeout_support")
        lease = (
            {
                "expected_head": support.get("lease_expected_head"),
                "expected_tree": support.get("lease_expected_tree"),
                "base_commitment_path": support.get("lease_base_commitment_path"),
                "base_commitment_bytes_sha256": support.get("lease_base_commitment_bytes_sha256"),
                "base_commitment_digest": support.get("base_commitment_digest"),
            }
            if isinstance(support, dict)
            else {}
        )
        commitment = (
            load_lease_bound_commitment(
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
                next_actions=("repair or select the Commitment carrier",),
            ),
            json_output=json_output,
            enforce=False,
        )
        return
    head = str(status_payload.get("head") or "")
    repository = load_repository_commitment(repo)
    facts = Facts(
        repository=repository.id,
        head=head,
        tree=current_tree(repo, head),
        observed_at=datetime.now(UTC),
        values={
            "branch": status_payload.get("branch", ""),
            "role": status_payload.get("role", ""),
            "dirty": status_payload.get("dirty", False),
            "changed_paths": paths,
        },
        source_refs=("git:HEAD", "git:HEAD^{tree}", "ethos:status"),
    )
    matched_rules, required_gates, rule_validation_gaps = matching_rule_gates(repo, paths)
    profile_adapter: dict[str, object] = {}
    if openspec_profile_enabled(repo):
        profile_adapter = openspec_governance_report(
            repo,
            change=change,
            lifecycle=True,
            changed_paths=paths,
            require_workspace=False,
        )
    adapter_gaps = tuple(string_sequence(profile_adapter.get("required_gaps")))
    gate_ids = tuple(str(gate.get("id") or "") for gate in required_gates)
    policy = resolve_gate_policy(repo, gate_ids=gate_ids)
    nodes = policy.nodes
    plan = compile_plan(
        commitment,
        facts,
        nodes,
        policy=policy.projection,
        required_gaps=tuple(dict.fromkeys((*rule_validation_gaps, *policy.gaps))),
    )
    required_gaps = tuple(
        dict.fromkeys((*plan.required_gaps, *adapter_gaps, *rule_validation_gaps))
    )
    ok = plan.verdict == "pass" and not adapter_gaps and not rule_validation_gaps
    result = EthosResult(
        command="plan",
        verdict="pass" if ok else "block" if required_gaps else "unknown",
        state="planned" if ok else "gapped",
        summary={
            "changed": changed,
            "plan_node_count": len(plan.nodes),
            "matched_rule_count": len(matched_rules),
            "required_gate_count": len(required_gates),
        },
        required_gaps=required_gaps,
        next_actions=("ethos prove --json",)
        if ok
        else (
            "repair .ethos/rules.toml and rerun ethos plan --json"
            if rule_validation_gaps
            else "repair the selected Commitment carrier",
        ),
        data={
            "changed_paths": list(paths),
            "matched_rules": matched_rules,
            "required_gates": required_gates,
            "rule_validation_gaps": rule_validation_gaps,
            "commitment": commitment.model_dump(mode="json"),
            "facts_digest": facts.digest(),
            "transition_plan": plan.model_dump(mode="json"),
            **({"profile_adapter": profile_adapter} if profile_adapter else {}),
        },
    )
    emit(result, json_output=json_output, enforce=False, artifact_root=repo)
