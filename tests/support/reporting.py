from __future__ import annotations

import ethos.domain.report as report_domain
import ethos.domain.reporting.scoring as reporting_scoring
from ethos_core.contracts.context.projection import ASSISTANT_TRUTH_BOUNDARY

OK = {"ok": True}
CLEAN = {"ok": True, "required_gaps": []}


def _clean(**values: object) -> dict[str, object]:
    return {**CLEAN, **values}


def _value(value: object):
    return lambda *_args, **_kwargs: value


def patch_scorecard_dependencies(
    monkeypatch, *, profile: str = "product", status: dict[str, object] | None = None
) -> None:
    audit = _clean(
        governance_context={"profile": profile},
        schemas=OK,
        openspec=_clean(advisory_gaps=[]),
    )
    audit["package_ontology" if profile == "product" else "adopter"] = (
        {"ok": True, "adapter_missing": []}
        if profile == "product"
        else {"adopter": {"governance": {"claims": True, "evidence": True, "docs": True}}}
    )
    reports = {
        "workspace_status": status or {},
        "claims_report": _clean(advisory_gaps=[]),
        "projection_contract": {"truth": ASSISTANT_TRUTH_BOUNDARY},
        "workflow_runtime_report": CLEAN,
        "playbooks_report": _clean(
            mode="v2-strict",
            advisory_gaps=[],
            v2_compliance={"score": 1, "max_score": 1},
        ),
        "adoption_scaffold_report": OK,
        "parity_ledger_report": _clean(summary={"unclassified_count": 0}),
        "proof_readiness_report": _clean(
            blocking=False, state="proven", evidence_class="local_readiness"
        ),
        "hosted_observation_report": _clean(state="observed", provider_states={}, advisory_gaps=[]),
        "parity_gaps_report": _clean(pending_packages=[]),
        "context_projection_contract": {
            "authority": "projection",
            "can_close_required_gaps": False,
            "can_satisfy_proof": False,
        },
        "available_profiles": (),
    }
    monkeypatch.setattr(report_domain.status_domain, "audit_for_root", _value(audit))
    monkeypatch.setattr(report_domain.git_adapter, "current_tracked_head", _value("head"))
    for name in "docs_health_report command_registry_report schema_validation_report evolution_report signature_policy_report".split():  # noqa: SIM905
        monkeypatch.setattr(report_domain, name, _value(OK))
    for name, value in reports.items():
        monkeypatch.setattr(report_domain, name, _value(value))
    monkeypatch.setattr(
        reporting_scoring,
        "standard_adapter_registry",
        _value({"std": {"boundary": "b", "fallback": "f", "exit_strategy": "e"}}),
    )
    monkeypatch.setattr(reporting_scoring, "hard_quality_floor_report", _value(CLEAN))
    monkeypatch.setattr(reporting_scoring, "global_compression_report", _value(CLEAN))
