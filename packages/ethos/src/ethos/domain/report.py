"""Report-stage reducer — compose the ETHOS scorecard payload."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git_adapter
import ethos.domain.land as land_domain
import ethos.domain.status as status_domain
from ethos.adapters.gates.signature import signature_policy_report
from ethos.adapters.repo.status.core import workspace_status
from ethos.assistants.playbooks import playbooks_report
from ethos.assistants.projections import projection_contract
from ethos.domain.prove import code_size_report
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.adoption.planner import adoption_scaffold_report
from ethos.repository.adoption.planner import available_profiles
from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity import parity_gaps_report
from ethos.repository.evidence.parity import parity_ledger_report
from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.layout.core import module_layout_report
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.registry.commands import command_registry_report
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.standards import standard_adapter_registry
from ethos_core.contracts.context_projection import ASSISTANT_TRUTH_BOUNDARY
from ethos_core.contracts.context_projection import context_projection_contract
from ethos_core.invalid_states import invalid_state_projection

if TYPE_CHECKING:
    from pathlib import Path


def scorecard_report(repo: Path) -> dict[str, object]:
    """Build the read-only report payload without emitting CLI output."""
    status_payload = workspace_status(repo)
    audit = status_domain.audit_for_root(repo, openspec_mode="shape")
    docs_report = docs_health_report(repo)
    claim_report = claims_report(repo)
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
        _hard_quality_floor_report(repo) if product_profile else _adopter_quality_floor_report()
    )
    current_head = git_adapter.current_tracked_head(repo)
    parity_gaps = parity_gaps_report(
        root=repo,
        target=repo,
        current_product_head=current_head,
        current_target_head=current_head,
        acceptable_product_heads=land_domain.acceptable_parity_product_heads(repo, None),
        acceptable_target_heads=land_domain.acceptable_parity_target_heads(repo, repo, None),
    )
    context_projection = context_projection_contract()
    context_projection_score = int(
        context_projection["authority"] == "projection"
        and not context_projection["can_close_required_gaps"]
        and not context_projection["can_satisfy_proof"]
    )
    scores = (
        _adopter_scores(audit, projection, context_projection_score, playbooks)
        if not product_profile
        else _product_scores(
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
    result_required_gaps = tuple(cast("list[str]", audit["required_gaps"]))
    if product_profile:
        result_required_gaps = (
            result_required_gaps
            + tuple(cast("list[str]", claim_report["required_gaps"]))
            + tuple(cast("list[str]", hard_quality_floor["required_gaps"]))
        )
    parity_pending_count = len(cast("list[str]", parity_gaps["required_gaps"]))
    advisory_gaps = _advisory_gaps(audit, claim_report, playbooks, status_payload)
    advisory_next_actions = _advisory_next_actions(advisory_gaps)
    gap_layers = _gap_layers(
        result_required_gaps,
        parity_gaps,
        playbooks,
        (advisory_gaps, advisory_next_actions),
        hard_quality_floor,
    )
    next_actions = _scorecard_next_actions(
        parity_pending_count=parity_pending_count,
        hard_quality_floor=hard_quality_floor,
    )
    return {
        "ok": all(value == 1 for value in scores.values()) and not result_required_gaps,
        "summary": {
            "score": sum(scores.values()),
            "max_score": len(scores),
            "governance_gap_count": len(result_required_gaps),
            "parity_pending_count": parity_pending_count,
            "advisory_gap_count": len(advisory_gaps),
        },
        "required_gaps": result_required_gaps,
        "next_actions": next_actions,
        "data": {
            "governance_context": audit["governance_context"],
            "scores": scores,
            "first_hour": _first_hour(
                product_profile=product_profile, required_gaps=result_required_gaps
            ),
            "scorecards": [_skills_scorecard(playbooks)],
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
            "gap_layers": gap_layers,
            "invalid_states": _all_invalid_states(result_required_gaps, parity_gaps, playbooks),
            "advisory_signals": {
                "blocking": False,
                "advisory_gaps": list(advisory_gaps),
                "gap_count": len(advisory_gaps),
                "next_actions": list(advisory_next_actions),
            },
            "parity": {
                "scope": {
                    "generic_gap_count": parity_pending_count,
                    "domain_profile_parity_closed": False,
                    "note": (
                        "Generic command parity does not claim domain profile parity "
                        "or adopter-specific retirement readiness."
                    ),
                },
                "ledger": parity_ledger,
                "gaps": parity_gaps,
            },
            "profiles": list(available_profiles()),
        },
    }


def _adopter_scores(
    audit: dict[str, object],
    projection: dict[str, object],
    context_projection_score: int,
    playbooks: dict[str, object],
) -> dict[str, int]:
    audit_adopter = cast("dict[str, object]", audit["adopter"])
    adopter = cast(
        "dict[str, object]",
        cast("dict[str, object]", audit_adopter["adopter"])["governance"],
    )
    return {
        "adopter_governance": int(bool(audit["ok"])),
        "schemas": int(bool(cast("dict[str, object]", audit["schemas"])["ok"])),
        "claims": int(bool(adopter["claims"])),
        "evidence": int(bool(adopter["evidence"])),
        "docs": int(bool(adopter["docs"])),
        "assistant_projection": int(projection["truth"] == ASSISTANT_TRUTH_BOUNDARY),
        "context_projection": context_projection_score,
        "playbooks": int(bool(playbooks["ok"])),
        "parity_ledger": int(bool(parity_ledger_report()["ok"])),
    }


def _product_scores(
    audit: dict[str, object],
    docs_report: dict[str, object],
    claim_report: dict[str, object],
    command_report: dict[str, object],
    projection: dict[str, object],
    schemas_report: dict[str, object],
    evolution: dict[str, object],
    signature: dict[str, object],
    playbooks: dict[str, object],
    adoption_scaffold: dict[str, object],
    parity_ledger: dict[str, object],
    context_projection_score: int,
) -> dict[str, int]:
    package_ontology = cast("dict[str, object]", audit["package_ontology"])
    return {
        "package_ontology": int(bool(package_ontology["ok"])),
        "distribution_adapter": int(not package_ontology["adapter_missing"]),
        "docs": int(bool(docs_report["ok"])),
        "schemas": int(bool(cast("dict[str, object]", audit["schemas"])["ok"])),
        "schema_validation": int(bool(schemas_report["ok"])),
        "claims": int(bool(claim_report["ok"])),
        "command_registry": int(bool(command_report["ok"])),
        "standards": int(
            all(
                item["boundary"] and item["fallback"] and item["exit_strategy"]
                for item in standard_adapter_registry().values()
            )
        ),
        "assistant_projection": int(projection["truth"] == ASSISTANT_TRUTH_BOUNDARY),
        "context_projection": context_projection_score,
        "evolution": int(bool(evolution["ok"])),
        "signature_policy": int(bool(signature["ok"])),
        "openspec": int(bool(cast("dict[str, object]", audit["openspec"])["ok"])),
        "playbooks": int(bool(playbooks["ok"])),
        "adoption_scaffold": int(bool(adoption_scaffold["ok"])),
        "parity_ledger": int(bool(parity_ledger["ok"])),
    }


def _hard_quality_floor_report(repo: Path) -> dict[str, object]:
    """Return product hard quality gates that the scorecard must not hide."""
    code_size = code_size_report(repo)
    module_layout = module_layout_report(repo)
    product_boundary = product_boundary_report(repo)
    contributor_policy = contributor_policy_report(repo)
    gate_reports = {
        "python-size": code_size,
        "module-layout": module_layout,
        "product-boundary": product_boundary,
        "contributor-policy": contributor_policy,
    }
    required_gaps: list[str] = []
    for report in gate_reports.values():
        required_gaps.extend(cast("list[str]", report["required_gaps"]))
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "gate_ids": list(gate_reports),
        "required_gaps": required_gaps,
        "gates": gate_reports,
    }


def _adopter_quality_floor_report() -> dict[str, object]:
    """Return the adopter report boundary; adopter gates remain profile-owned."""
    return {
        "ok": True,
        "state": "profile_deferred",
        "gate_ids": [],
        "required_gaps": [],
        "gates": {},
        "boundary": "adopter_profile_quality_floor",
    }


def _scorecard_next_actions(
    *,
    parity_pending_count: int,
    hard_quality_floor: dict[str, object],
) -> tuple[str, ...]:
    """Return bounded next actions for report without hiding hard quality gaps."""
    quality_gaps = cast("list[str]", hard_quality_floor["required_gaps"])
    if quality_gaps:
        commands: list[str] = []
        if any(gap.startswith("code_size_") for gap in quality_gaps):
            commands.append("ethos quality code-size --json")
        if any(gap.startswith("module_layout_") for gap in quality_gaps):
            commands.append("ethos quality module-layout --json")
        if any("product-boundary" in gap or "product_boundary" in gap for gap in quality_gaps):
            commands.append("ethos quality product-boundary --json")
        if any("contributor" in gap or "identity" in gap for gap in quality_gaps):
            commands.append("ethos quality contributor-policy --json")
        return tuple(commands or ["ethos quality --json"])
    if parity_pending_count:
        return ("ethos parity gaps --adopter <adopter>",)
    return ("ethos prove --full",)


def _first_hour(*, product_profile: bool, required_gaps: tuple[str, ...]) -> dict[str, object]:
    if product_profile:
        return {}
    evidence_gap_count = len(required_gaps)
    readiness = "local_readiness" if evidence_gap_count == 0 else "blocked"
    return {
        "proof_status": "ready" if evidence_gap_count == 0 else "gapped",
        "evidence_gap_count": evidence_gap_count,
        "land_readiness": readiness,
        "publish_readiness": readiness,
        "hosted_ci_truth": "external-evidence",
        "next_action": "ethos prove" if evidence_gap_count == 0 else "resolve evidence gaps",
    }


def _advisory_gaps(
    audit: dict[str, object],
    claim_report: dict[str, object],
    playbooks: dict[str, object],
    status_payload: dict[str, object] | None = None,
) -> tuple[str, ...]:
    """Collect non-blocking small signals that should stay visible in report.

    Required gaps remain the blocking transition vocabulary. Advisory gaps are
    early disorder signals: visible to humans and agents, but not proof-closing
    blockers by themselves. Keep the collection explicit so the scorecard does
    not recursively reinterpret arbitrary nested provider payloads as product
    truth.
    """
    openspec = cast("dict[str, object]", audit.get("openspec") or {})
    coordination = cast("dict[str, object]", (status_payload or {}).get("coordination") or {})
    values = [
        *_strings(coordination.get("advisory_gaps")),
        *_strings(openspec.get("advisory_gaps")),
        *_strings(claim_report.get("advisory_gaps")),
        *_strings(playbooks.get("advisory_gaps")),
    ]
    return tuple(dict.fromkeys(values))


def _advisory_next_actions(advisory_gaps: tuple[str, ...]) -> tuple[str, ...]:
    """Translate non-blocking advisory signals into bounded repair hints.

    These are not transition requirements and do not authorize mutation from the
    current checkout. They only keep small visible signals actionable for a
    human or agent who chooses to repair the owning branch or surface.
    """
    actions: list[str] = []
    for gap in advisory_gaps:
        parts = gap.split(":")
        if (
            gap
            in {
                "foreign_work_lane_present",
                "unbound_work_lane_ref_present",
            }
            or gap.startswith(
                (
                    "work_lane_missing_lease:",
                    "coordination_gap:",
                )
            )
            or gap == "work_lane_closeout_residue_present"
        ):
            actions.extend(["ethos orient --json", "ethos lane status --json"])
        if len(parts) == 4 and parts[0] == "openspec_protected_branch_active_change_unarchived":
            branch = parts[1]
            role = parts[2]
            change = parts[3]
            actions.extend(
                [
                    f"git ls-tree -r --name-only {branch} -- openspec/changes/{change}",
                    "ethos explain "
                    f"openspec_protected_branch_active_change_unarchived:{branch}:{role}:{change} "
                    "--json",
                ]
            )
    return tuple(dict.fromkeys(actions))


def _strings(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value if str(item)]


def _gap_layers(
    result_required_gaps: tuple[str, ...],
    parity_gaps: dict[str, object],
    playbooks: dict[str, object],
    advisory: tuple[tuple[str, ...], tuple[str, ...]],
    hard_quality_floor: dict[str, object] | None = None,
) -> dict[str, dict[str, object]]:
    advisory_gaps, advisory_next_actions = advisory
    hard_quality_floor = hard_quality_floor or _adopter_quality_floor_report()
    return {
        "governance_audit": _gap_layer(
            scope="governance_audit",
            blocking=True,
            ok=not result_required_gaps,
            gaps=list(result_required_gaps),
        ),
        "capability_parity": _gap_layer(
            scope="capability_parity",
            blocking=False,
            ok=bool(parity_gaps["ok"]),
            gaps=list(cast("list[str]", parity_gaps["required_gaps"])),
        ),
        "playbook_projection": {
            **_gap_layer(
                scope="skills-v2",
                blocking=True,
                ok=bool(playbooks["ok"]),
                gaps=list(cast("list[str]", playbooks["required_gaps"])),
            ),
            "advisory_gaps": list(cast("list[object]", playbooks["advisory_gaps"])),
        },
        "hard_quality_floor": _gap_layer(
            scope="hard_quality_floor",
            blocking=True,
            ok=bool(hard_quality_floor["ok"]),
            gaps=list(cast("list[str]", hard_quality_floor["required_gaps"])),
        ),
        "advisory_signals": {
            "scope": "advisory_signals",
            "blocking": False,
            "ok": True,
            "required_gaps": [],
            "advisory_gaps": list(advisory_gaps),
            "gap_count": len(advisory_gaps),
            "next_actions": list(advisory_next_actions),
            "invalid_states": invalid_state_projection(list(advisory_gaps)),
        },
    }


def _gap_layer(*, scope: str, blocking: bool, ok: bool, gaps: list[str]) -> dict[str, object]:
    return {
        "scope": scope,
        "blocking": blocking,
        "ok": ok,
        "required_gaps": gaps,
        "gap_count": len(gaps),
        "invalid_states": invalid_state_projection(gaps),
    }


def _all_invalid_states(
    result_required_gaps: tuple[str, ...],
    parity_gaps: dict[str, object],
    playbooks: dict[str, object],
) -> dict[str, object]:
    return invalid_state_projection(
        [
            *list(result_required_gaps),
            *list(cast("list[str]", parity_gaps["required_gaps"])),
            *list(cast("list[str]", playbooks["required_gaps"])),
        ]
    )


def _skills_scorecard(playbooks: dict[str, object]) -> dict[str, object]:
    v2_compliance = cast("dict[str, object]", playbooks["v2_compliance"])
    return {
        "id": "skills-v2",
        "scope": "playbook_projection",
        "mode": playbooks["mode"],
        "ok": bool(playbooks["ok"]),
        "score": v2_compliance["score"],
        "max_score": v2_compliance["max_score"],
        "blocking": True,
        "required_gaps": list(cast("list[object]", playbooks["required_gaps"])),
        "advisory_gaps": list(cast("list[object]", playbooks["advisory_gaps"])),
    }
