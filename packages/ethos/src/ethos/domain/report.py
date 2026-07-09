"""Report-stage reducer — compose the ETHOS scorecard payload."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git_adapter
import ethos.domain.land as land_domain
import ethos.domain.reporting.gaps as reporting_gaps
import ethos.domain.reporting.parity.core as reporting_parity
import ethos.domain.reporting.scoring as reporting_scoring
import ethos.domain.status as status_domain
from ethos.adapters.gates.signature import signature_policy_report
from ethos.adapters.repo.status.core import workspace_status
from ethos.assistants.playbooks import playbooks_report
from ethos.assistants.projections import projection_contract
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.adoption.planner import adoption_scaffold_report
from ethos.repository.adoption.planner import available_profiles
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity import parity_gaps_report
from ethos.repository.evidence.parity import parity_ledger_report
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.registry.commands import command_registry_report
from ethos.repository.registry.docs.health import docs_health_report
from ethos_core.contracts.context.projection import context_projection_contract

if TYPE_CHECKING:
    from pathlib import Path


def scorecard_report(repo: Path, *, product_root: Path | None = None) -> dict[str, object]:
    """Build the read-only report payload without emitting CLI output."""
    status_payload = workspace_status(repo)
    audit = status_domain.audit_for_root(repo, openspec_mode="shape")
    docs_report = docs_health_report(repo)
    current_head = git_adapter.current_tracked_head(repo)
    claim_report = claims_report(repo, current_head=current_head)
    command_report = command_registry_report(repo)
    projection = projection_contract()
    schemas_report = schema_validation_report(repo)
    evolution = evolution_report(repo)
    signature = signature_policy_report(repo)
    audit_profile = str(cast("dict[str, object]", audit["governance_context"])["profile"])
    product_profile = audit_profile == "product"
    playbooks = playbooks_report(repo, mode="v2-strict")
    adoption_scaffold = adoption_scaffold_report()
    parity_ledger = parity_ledger_report()
    hard_quality_floor = (
        reporting_scoring.hard_quality_floor_report(repo)
        if product_profile
        else reporting_scoring.adopter_quality_floor_report()
    )
    adopter_id = reporting_parity.profile_identity(repo) if not product_profile else ""
    parity_root = (
        repo
        if product_profile
        else reporting_parity.adopter_product_root(repo, status_payload, product_root)
    )
    current_product_head = (
        current_head if product_profile else git_adapter.current_tracked_head(parity_root)
    )
    parity_gaps = parity_gaps_report(
        root=repo,
        target=repo,
        current_product_head=current_head,
        current_target_head=current_head,
        acceptable_product_heads=land_domain.acceptable_parity_product_heads(repo, None),
        acceptable_target_heads=land_domain.acceptable_parity_target_heads(repo, repo, None),
    )
    adopter_parity_gaps = (
        parity_gaps_report(
            adopter=adopter_id,
            root=parity_root,
            target=repo,
            current_product_head=current_product_head,
            current_target_head=current_head,
            acceptable_product_heads=land_domain.acceptable_parity_product_heads(
                parity_root, adopter_id
            ),
            acceptable_target_heads=land_domain.acceptable_parity_target_heads(
                parity_root, repo, adopter_id
            ),
        )
        if adopter_id
        else {}
    )
    context_projection = context_projection_contract()
    context_projection_score = int(
        context_projection["authority"] == "projection"
        and not context_projection["can_close_required_gaps"]
        and not context_projection["can_satisfy_proof"]
    )
    scores = (
        reporting_scoring.adopter_scores(audit, projection, context_projection_score, playbooks)
        if not product_profile
        else reporting_scoring.product_scores(
            audit,
            docs_report,
            claim_report,
            command_report,
            projection,
            schemas_report,
            evolution,
            signature,
            playbooks,
            adoption_scaffold,
            parity_ledger,
            context_projection_score,
        )
    )
    nominal_score = sum(scores.values())
    max_score = len(scores)
    result_required_gaps = tuple(cast("list[str]", audit["required_gaps"]))
    if product_profile:
        result_required_gaps = (
            result_required_gaps
            + tuple(cast("list[str]", claim_report["required_gaps"]))
            + tuple(cast("list[str]", hard_quality_floor["required_gaps"]))
        )
    generic_parity_pending_count = len(cast("list[str]", parity_gaps["required_gaps"]))
    adopter_parity_pending_count = len(
        cast("list[str]", adopter_parity_gaps.get("required_gaps", []))
    )
    parity_pending_count = (
        generic_parity_pending_count if product_profile else adopter_parity_pending_count
    )
    hard_quality_gap_count = len(cast("list[str]", hard_quality_floor["required_gaps"]))
    coordination_required_gaps, coordination_advisory_gaps = reporting_gaps.coordination_risk_gaps(
        audit, status_payload
    )
    result_required_gaps = tuple(
        dict.fromkeys((*result_required_gaps, *coordination_required_gaps))
    )
    hard_quality_penalty = int(hard_quality_gap_count > 0)
    coordination_risk_penalty = int(bool(coordination_required_gaps))
    effective_score = max(0, nominal_score - hard_quality_penalty - coordination_risk_penalty)
    coordination_risk_count = len(coordination_required_gaps) + len(coordination_advisory_gaps)
    advisory_gap_items = reporting_gaps.advisory_gaps(
        audit, claim_report, playbooks, status_payload
    )
    advisory_action_items = reporting_gaps.advisory_next_actions(advisory_gap_items)
    report_gap_layers = reporting_gaps.gap_layers(
        result_required_gaps,
        parity_gaps,
        playbooks,
        (advisory_gap_items, advisory_action_items),
        hard_quality_floor,
        coordination_required_gaps,
        coordination_advisory_gaps,
    )
    terminal_control_state = reporting_scoring.terminal_control(
        result_required_gaps=result_required_gaps,
        hard_quality_gap_count=hard_quality_gap_count,
        stage_gates=cast("dict[str, object]", audit.get("stage_gates") or {}),
    )
    next_actions = reporting_scoring.scorecard_next_actions(
        parity_pending_count=parity_pending_count,
        hard_quality_floor=hard_quality_floor,
        coordination_required_gaps=coordination_required_gaps,
        playbooks=playbooks,
    )
    return {
        "ok": all(value == 1 for value in scores.values()) and not result_required_gaps,
        "summary": {
            "profile": audit_profile,
            "read_model": "governed_repository_scorecard_v2",
            "score": nominal_score,
            "max_score": max_score,
            "effective_score": effective_score,
            "effective_max_score": max_score,
            "terminal_control": terminal_control_state,
            "governance_gap_count": len(result_required_gaps),
            "hard_quality_gap_count": hard_quality_gap_count,
            "coordination_risk_count": coordination_risk_count,
            "parity_pending_count": parity_pending_count,
            "advisory_gap_count": len(advisory_gap_items),
        },
        "required_gaps": result_required_gaps,
        "next_actions": next_actions,
        "data": {
            "governance_context": audit["governance_context"],
            "scores": scores,
            "score_model": {
                "nominal_score": nominal_score,
                "nominal_max_score": max_score,
                "effective_score": effective_score,
                "effective_max_score": max_score,
                "hard_quality_floor_penalty": hard_quality_penalty,
                "coordination_risk_penalty": coordination_risk_penalty,
                "note": (
                    "effective_score subtracts hard local quality-floor and "
                    "required coordination risk from the nominal capability score"
                ),
            },
            "first_hour": reporting_scoring.first_hour(
                product_profile=product_profile, required_gaps=result_required_gaps
            ),
            "scorecards": [reporting_gaps.skills_scorecard(playbooks)],
            "repository_audit": audit,
            "docs": docs_report,
            "claims": claim_report,
            "assistant_projection": projection,
            "context_projection": context_projection,
            "schema_validation": schemas_report,
            "evolution": evolution,
            "signature_policy": signature,
            "playbooks": playbooks,
            "adoption_scaffold": adoption_scaffold,
            "hard_quality_floor": hard_quality_floor,
            "gap_layers": report_gap_layers,
            "invalid_states": reporting_gaps.all_invalid_states(
                result_required_gaps, parity_gaps, playbooks
            ),
            "advisory_signals": {
                "blocking": False,
                "advisory_gaps": list(advisory_gap_items),
                "gap_count": len(advisory_gap_items),
                "next_actions": list(advisory_action_items),
            },
            "parity": {
                "scope": reporting_parity.parity_scope(
                    product_profile=product_profile,
                    adopter=adopter_id,
                    generic_gap_count=generic_parity_pending_count,
                    adopter_gap_count=adopter_parity_pending_count,
                ),
                "ledger": parity_ledger,
                "gaps": parity_gaps,
                "adopter_gaps": adopter_parity_gaps,
            },
            "profiles": list(available_profiles()),
        },
    }
