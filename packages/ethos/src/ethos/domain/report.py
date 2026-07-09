"""Report-stage reducer — compose the ETHOS scorecard payload."""

from __future__ import annotations

from pathlib import Path
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
from ethos.repository.profile import load_repository_profile
from ethos.repository.registry.commands import command_registry_report
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.standards import standard_adapter_registry
from ethos_core.contracts.context.projection import ASSISTANT_TRUTH_BOUNDARY
from ethos_core.contracts.context.projection import context_projection_contract
from ethos_core.invalid_states import invalid_state_projection


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
        _hard_quality_floor_report(repo) if product_profile else _adopter_quality_floor_report()
    )
    adopter_id = profile_identity(repo) if not product_profile else ""
    parity_root = (
        repo if product_profile else adopter_product_root(repo, status_payload, product_root)
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
    hard_quality_penalty = int(hard_quality_gap_count > 0)
    effective_score = max(0, nominal_score - hard_quality_penalty)
    coordination_gaps = tuple(_strings(audit.get("coordination_gaps")))
    advisory_gaps = _advisory_gaps(audit, claim_report, playbooks, status_payload)
    advisory_next_actions = _advisory_next_actions(advisory_gaps)
    gap_layers = _gap_layers(
        result_required_gaps,
        parity_gaps,
        playbooks,
        (advisory_gaps, advisory_next_actions),
        hard_quality_floor,
        coordination_gaps,
    )
    terminal_control = _terminal_control(
        result_required_gaps=result_required_gaps,
        hard_quality_gap_count=hard_quality_gap_count,
        stage_gates=cast("dict[str, object]", audit.get("stage_gates") or {}),
    )
    next_actions = _scorecard_next_actions(
        parity_pending_count=parity_pending_count,
        hard_quality_floor=hard_quality_floor,
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
            "terminal_control": terminal_control,
            "governance_gap_count": len(result_required_gaps),
            "hard_quality_gap_count": hard_quality_gap_count,
            "coordination_risk_count": len(coordination_gaps),
            "parity_pending_count": parity_pending_count,
            "advisory_gap_count": len(advisory_gaps),
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
                "coordination_risk_penalty": 0,
                "note": (
                    "effective_score subtracts hard local quality-floor risk "
                    "from the nominal capability score"
                ),
            },
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
                "scope": _parity_scope(
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


def profile_identity(repo: Path) -> str:
    """Return the repository profile id used for adopter-specific parity, if any."""
    profile = load_repository_profile(repo)
    return profile.identity.get("profile_id", "")


def adopter_product_root(
    repo: Path, status_payload: dict[str, object], explicit_product_root: Path | None
) -> Path:
    """Resolve the external product root used for adopter shadow parity."""
    if explicit_product_root is not None:
        return explicit_product_root.resolve()
    runtime = status_payload.get("runtime_binding")
    if isinstance(runtime, dict):
        runner_source_root = str(runtime.get("runner_source_root") or "")
        if runner_source_root:
            runner_root = Path(runner_source_root).resolve()
            if runner_root != repo.resolve():
                return runner_root
    profile = load_repository_profile(repo)
    external_backend = profile.tables.get("external_backend", {})
    configured = external_backend.get("product_root")
    if isinstance(configured, str) and configured:
        return (repo / configured).resolve()
    return repo.resolve()


def _parity_scope(
    *,
    product_profile: bool,
    adopter: str,
    generic_gap_count: int,
    adopter_gap_count: int,
) -> dict[str, object]:
    if product_profile or not adopter:
        return {
            "generic_gap_count": generic_gap_count,
            "domain_profile_parity_closed": False,
            "note": (
                "Generic command parity does not claim domain profile parity "
                "or adopter-specific retirement readiness."
            ),
        }
    return {
        "generic_gap_count": generic_gap_count,
        "adopter": adopter,
        "adopter_gap_count": adopter_gap_count,
        "domain_profile_parity_closed": adopter_gap_count == 0,
        "note": (
            "Adopter shadow parity is profile-specific evidence. Generic command parity "
            "remains a product migration signal and does not block adopter report routing."
        ),
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


def _terminal_control(
    *,
    result_required_gaps: tuple[str, ...],
    hard_quality_gap_count: int,
    stage_gates: dict[str, object],
) -> str:
    if result_required_gaps or hard_quality_gap_count:
        return "partial"
    if any(value is False for value in stage_gates.values() if isinstance(value, bool)):
        return "partial"
    return "closed_loop"


def _scorecard_next_actions(
    *,
    parity_pending_count: int,
    hard_quality_floor: dict[str, object],
    playbooks: dict[str, object] | None = None,
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
    if playbooks and playbooks.get("ok") is not True:
        return ("ethos playbooks check --mode v2-strict --json",)
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
    coordination_gaps: tuple[str, ...] = (),
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
        "coordination_risk": {
            "scope": "coordination_risk",
            "blocking": False,
            "ok": True,
            "required_gaps": [],
            "advisory_gaps": list(coordination_gaps),
            "gap_count": len(coordination_gaps),
            "invalid_states": invalid_state_projection(list(coordination_gaps)),
        },
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
