"""Root planning command."""

from __future__ import annotations

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
    status_payload = workspace_status(repo)
    governance = context_for_root(repo)
    paths = change_scope_paths_from_status(repo, status_payload) if changed else ()
    graph = graph_for_paths(paths)
    matched_rules, required_gates = matching_rule_gates(repo, paths)
    domain_contracts = contract_profile_matches(repo, paths)
    workflow_runtime = workflow_runtime_report(repo, changed_paths=paths)
    result = EthosResult(
        command="plan",
        ok=True,
        state="planned",
        summary={
            "changed": changed,
            "action_count": len(graph.nodes),
            "matched_rule_count": len(matched_rules),
            "required_gate_count": len(required_gates),
        },
        next_actions=("ethos prove --json",),
        governance_context=governance,
        data={
            "changed_paths": list(paths),
            "matched_rules": matched_rules,
            "required_gates": required_gates,
            "domain_contracts": domain_contracts,
            "action_graph": graph.to_dict(),
            "workflow_runtime": workflow_runtime,
        },
    )
    emit(result, json_output=json_output, enforce=False)
