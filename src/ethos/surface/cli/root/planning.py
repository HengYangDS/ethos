"""Root planning command."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.repo.change_contract import load_change_contract
from ethos.adapters.repo.change_contract import load_lease_bound_change_contract
from ethos.adapters.repo.change_contract import load_repository_contract
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.lifecycle.declaration import load_lifecycle_declaration
from ethos.contracts.semantic import RepositoryFacts
from ethos.domain.plan import matching_rule_gates
from ethos.repository.context import context_for_root
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
    """Compile deterministic PlanIR."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    governance = context_for_root(repo)
    paths = change_scope_paths_from_status(repo, status_payload) if changed else ()
    try:
        support = status_payload.get("closeout_support")
        lease = support if isinstance(support, dict) else {}
        change_contract = (
            load_lease_bound_change_contract(
                repo,
                change_id=change,
                expected_head=str(lease.get("lease_expected_head") or ""),
                base_change_contract_digest=str(lease.get("base_change_contract_digest") or ""),
            )
            if status_payload.get("role") == ROLE_WORK_LANE
            else load_change_contract(repo, change_id=change)
            if change is not None
            else load_repository_contract(repo)
        )
    except ValueError as exc:
        gap = str(exc)
        emit(
            EthosResult(
                command="plan",
                ok=False,
                state="gapped",
                required_gaps=(gap,),
                next_actions=("create or select an OpenSpec change contract",),
                governance_context=governance,
            ),
            json_output=json_output,
            enforce=False,
        )
        return
    head = str(status_payload.get("head") or "")
    contract = change_contract
    repository = load_repository_contract(repo)
    facts = RepositoryFacts(
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
    openspec_lifecycle = openspec_governance_report(
        repo,
        change=change,
        lifecycle=True,
        changed_paths=paths,
        require_workspace=False,
    )
    lifecycle_gaps = tuple(str(gap) for gap in openspec_lifecycle.get("required_gaps", []))
    facts = facts.model_copy(
        update={
            "values": {
                **facts.values,
                "openspec_carrier": bool(openspec_lifecycle.get("ok")),
            }
        }
    )
    plan = load_lifecycle_declaration(repo).plan(
        contract=contract,
        facts=facts,
        node_ids=("status", "plan", "prove"),
    )
    plan_gaps = tuple(
        gap
        for gap in plan.gaps()
        if not (lifecycle_gaps and gap == "lifecycle_external_fact_missing:plan:openspec_carrier")
    )
    required_gaps = tuple(dict.fromkeys((*plan_gaps, *lifecycle_gaps, *rule_validation_gaps)))
    ok = plan.ok and bool(openspec_lifecycle.get("ok")) and not rule_validation_gaps
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
            else "openspec validate --all --strict --json",
        ),
        governance_context=governance,
        data={
            "changed_paths": list(paths),
            "matched_rules": matched_rules,
            "required_gates": required_gates,
            "rule_validation_gaps": rule_validation_gaps,
            "change_contract": contract.model_dump(mode="json"),
            "repository_facts_digest": facts.digest(),
            "plan_ir": plan.to_dict(),
            "openspec_lifecycle": openspec_lifecycle,
        },
    )
    emit(result, json_output=json_output, enforce=False, artifact_root=repo)
