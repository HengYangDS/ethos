"""ETHOS workflow runtime read model.

This module projects declared workflow contracts plus repository/evolution facts.
It does not persist lifecycle state or execute an orchestration engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.contracts.workflow import load_workflow_contract_declaration
from ethos.contracts.workflow import planned_transition_projection
from ethos.contracts.workflow import workflow_contract_report
from ethos.normalization.core import string_list
from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_report

if TYPE_CHECKING:
    from pathlib import Path


def workflow_runtime_report(root: Path, *, changed_paths: tuple[str, ...] = ()) -> dict[str, Any]:
    """Return the derived workflow runtime read model for a repository root."""
    try:
        contract = load_workflow_contract_declaration(root)
    except (FileNotFoundError, ValueError) as exc:
        return _missing_workflow_contract(root, changed_paths=changed_paths, exc=exc)
    contract_report = workflow_contract_report(contract)
    evolution = evolution_report(root)
    campaigns = campaign_report(root)
    ledger = _dict(evolution.get("ledger"))
    selection = _dict(evolution.get("selection"))
    contract_evolution = _dict(contract_report.get("evolution"))
    active_hypotheses = [
        {
            "id": str(item.get("id", "")),
            "campaign": str(item.get("campaign", "")),
            "state": str(item.get("state", "")),
            "claim": str(item.get("claim", "")),
            "transition": str(item.get("transition", "")),
        }
        for item in _dict_items(ledger.get("hypotheses"))
        if item.get("state") in {"active", "experimenting"}
    ]
    required_gaps = list(contract_report["required_gaps"])
    return {
        "ok": not required_gaps,
        "kind": "workflow_runtime_read_model",
        "truth_boundary": "derived_repository_projection",
        "contract": contract_report,
        "plan": planned_transition_projection(contract, changed_paths=changed_paths),
        "evolution_bridge": {
            "truth_boundary": "evolution_ledger_claim_evidence_chronicle",
            "active_hypothesis_count": len(active_hypotheses),
            "active_hypotheses": active_hypotheses,
            "campaign_count": campaigns.get("campaign_count", 0),
            "campaign_required_gaps": string_list(campaigns.get("required_gaps")),
            "practice_claim_count": selection.get("practice_claim_count", 0),
            "practice_claims": selection.get("practice_claims", []),
            "selection_policy": contract_evolution.get("selection_policy", ""),
            "commitment_effect_policy": contract_evolution.get("commitment_effect_policy", ""),
            "practice_claim_policy": contract_evolution.get("practice_claim_policy", ""),
            "practice_change_policy": contract_evolution.get("practice_change_policy", ""),
            "practice_evolution": selection,
            "runtime_owns_evolution": False,
        },
        "required_gaps": required_gaps,
    }


def _missing_workflow_contract(
    root: Path,
    *,
    changed_paths: tuple[str, ...],
    exc: BaseException,
) -> dict[str, Any]:
    gap = f"workflow_contract_unavailable:{type(exc).__name__}"
    return {
        "ok": False,
        "kind": "workflow_runtime_read_model",
        "truth_boundary": "derived_repository_projection",
        "contract": {"ok": False, "required_gaps": [gap]},
        "plan": {
            "kind": "workflow_runtime_plan",
            "truth_boundary": "derived_repository_projection",
            "changed_path_count": len(changed_paths),
            "changed_paths": list(changed_paths),
            "transitions": [],
            "nodes": [],
        },
        "evolution_bridge": {
            "truth_boundary": "evolution_ledger_claim_evidence_chronicle",
            "active_hypothesis_count": 0,
            "active_hypotheses": [],
            "campaign_count": 0,
            "campaign_required_gaps": [],
            "selection_policy": "",
            "commitment_effect_policy": "",
            "practice_claim_policy": "",
            "practice_change_policy": "",
            "practice_evolution": {},
            "runtime_owns_evolution": False,
        },
        "required_gaps": [gap],
    }


def _dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return cast("dict[str, Any]", value)


def _dict_items(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [cast("dict[str, Any]", item) for item in value if isinstance(item, dict)]
