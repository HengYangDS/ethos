"""Root planning command."""

from __future__ import annotations

from ethos.adapters.openspec.core import openspec_governance_report
from ethos.adapters.repo.dirty.core import change_scope_paths_from_status
from ethos.adapters.repo.status.core import workspace_status
from ethos.domain.plan import contract_profile_matches
from ethos.domain.plan import graph_for_paths
from ethos.domain.plan import matching_rule_gates
from ethos.repository.context import context_for_root
from ethos.repository.workflow.runtime import workflow_runtime_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


def plan(
    *,
    changed: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan deterministic action graph."""
    repo = resolve_root(root)
    status_payload = workspace_status(repo, include_foreign_path_scope=False)
    governance = context_for_root(repo)
    paths = change_scope_paths_from_status(repo, status_payload) if changed else ()
    graph = graph_for_paths(paths)
    matched_rules, required_gates, rule_validation_gaps = matching_rule_gates(repo, paths)
    domain_contracts = contract_profile_matches(repo, paths)
    workflow_runtime = workflow_runtime_report(repo, changed_paths=paths)
    openspec_lifecycle = openspec_governance_report(repo, lifecycle=True, changed_paths=paths)
    lifecycle_gaps = tuple(str(gap) for gap in openspec_lifecycle.get("required_gaps", []))
    required_gaps = tuple(dict.fromkeys((*lifecycle_gaps, *rule_validation_gaps)))
    ok = bool(openspec_lifecycle.get("ok")) and not rule_validation_gaps
    result = EthosResult(
        command="plan",
        ok=ok,
        state="planned" if ok else "gapped",
        summary={
            "changed": changed,
            "action_count": len(graph.nodes),
            "matched_rule_count": len(matched_rules),
            "required_gate_count": len(required_gates),
        },
        required_gaps=required_gaps,
        next_actions=("ethos prove --json",)
        if ok
        else (
            "repair .ethos/rules.toml and rerun ethos plan --json"
            if rule_validation_gaps
            else "ethos openspec --lifecycle --json",
        ),
        governance_context=governance,
        data={
            "changed_paths": list(paths),
            "matched_rules": matched_rules,
            "required_gates": required_gates,
            "rule_validation_gaps": rule_validation_gaps,
            "domain_contracts": domain_contracts,
            "action_graph": graph.to_dict(),
            "workflow_runtime": workflow_runtime,
            "openspec_lifecycle": openspec_lifecycle,
        },
    )
    emit(result, json_output=json_output, enforce=False)
