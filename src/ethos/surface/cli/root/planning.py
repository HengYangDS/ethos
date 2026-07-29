"""Root planning command."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from ethos.domain.plan import matching_rule_gates
from ethos.repository.context import is_product_root
from ethos.repository.policy.gates import gate_nodes
from ethos.repository.policy.gates import gate_policy_digest
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
        lease = support if isinstance(support, dict) else {}
        product = is_product_root(repo)
        if product:
            from ethos.adapters.openspec.commitment import load_openspec_commitment
            from ethos.adapters.openspec.profile import load_profile_lease_bound_commitment

            commitment = (
                load_profile_lease_bound_commitment(
                    repo,
                    change_id=change,
                    expected_head=str(lease.get("lease_expected_head") or ""),
                    base_commitment_digest=str(lease.get("base_commitment_digest") or ""),
                )
                if status_payload.get("role") == ROLE_WORK_LANE
                else load_openspec_commitment(repo, change_id=change)
            )
        else:
            commitment = (
                load_lease_bound_commitment(
                    repo,
                    change_id=change,
                    expected_head=str(lease.get("lease_expected_head") or ""),
                    base_commitment_digest=str(lease.get("base_commitment_digest") or ""),
                )
                if status_payload.get("role") == ROLE_WORK_LANE
                else load_commitment(repo, change_id=change)
            )
    except ValueError as exc:
        gap = str(exc)
        emit(
            EthosResult(
                command="plan",
                ok=False,
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
    if product:
        from ethos.adapters.openspec.governance import openspec_governance_report

        profile_adapter = openspec_governance_report(
            repo,
            change=change,
            lifecycle=True,
            changed_paths=paths,
            require_workspace=False,
        )
    adapter_gaps = tuple(str(gap) for gap in profile_adapter.get("required_gaps", []))
    gate_ids = tuple(str(gate.get("id") or "") for gate in required_gates)
    nodes, gate_gaps = gate_nodes(gate_ids, root=repo)
    plan = compile_plan(
        commitment,
        facts,
        nodes,
        policy_digest=gate_policy_digest(repo),
        validation_issues=tuple(dict.fromkeys((*rule_validation_gaps, *gate_gaps))),
    )
    required_gaps = tuple(dict.fromkeys((*plan.gaps(), *adapter_gaps, *rule_validation_gaps)))
    ok = plan.ok and not adapter_gaps and not rule_validation_gaps
    result = EthosResult(
        command="plan",
        ok=ok,
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
            "transition_plan": plan.to_dict(),
            **({"profile_adapter": profile_adapter} if profile_adapter else {}),
        },
    )
    emit(result, json_output=json_output, enforce=False, artifact_root=repo)
