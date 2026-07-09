from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

import ethos.domain.report as report_domain
import ethos.domain.reporting.parity.core as reporting_parity
import ethos.domain.reporting.scoring as reporting_scoring
from ethos_core.contracts.context.projection import ASSISTANT_TRUTH_BOUNDARY


def _patch_report_scorecard_dependencies(monkeypatch, *, profile: str) -> None:
    audit_payload: dict[str, object] = {
        "ok": True,
        "required_gaps": [],
        "governance_context": {"profile": profile},
        "schemas": {"ok": True},
        "openspec": {"ok": True, "advisory_gaps": []},
    }
    if profile == "product":
        audit_payload["package_ontology"] = {"ok": True, "adapter_missing": []}
    else:
        audit_payload["adopter"] = {
            "adopter": {"governance": {"claims": True, "evidence": True, "docs": True}}
        }
        monkeypatch.setattr(reporting_parity, "profile_identity", lambda _repo: "domain-adopter")

    monkeypatch.setattr(
        report_domain,
        "workspace_status",
        lambda _repo: {
            "coordination": {
                "required_gaps": ["coordination_gap:current_scope_unknown"],
                "advisory_gaps": ["coordination_gap:foreign_scope_unknown:work/other"],
            },
        },
    )
    monkeypatch.setattr(
        report_domain.status_domain,
        "audit_for_root",
        lambda _repo, **_kwargs: audit_payload,
    )
    monkeypatch.setattr(report_domain, "docs_health_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "claims_report",
        lambda _repo, **_kwargs: {"ok": True, "required_gaps": [], "advisory_gaps": []},
    )
    monkeypatch.setattr(report_domain, "command_registry_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "projection_contract",
        lambda: {"truth": ASSISTANT_TRUTH_BOUNDARY},
    )
    monkeypatch.setattr(report_domain, "schema_validation_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "evolution_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "signature_policy_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "playbooks_report",
        lambda _repo, mode="v2-strict": {
            "ok": True,
            "mode": mode,
            "required_gaps": [],
            "advisory_gaps": [],
            "v2_compliance": {"score": 1, "max_score": 1},
        },
    )
    monkeypatch.setattr(report_domain, "adoption_scaffold_report", lambda: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "parity_ledger_report",
        lambda: {"ok": True, "summary": {"unclassified_count": 0}},
    )
    monkeypatch.setattr(report_domain.git_adapter, "current_tracked_head", lambda _repo: "head")
    monkeypatch.setattr(
        report_domain,
        "parity_gaps_report",
        lambda **_kwargs: {"ok": True, "required_gaps": [], "pending_packages": []},
    )
    monkeypatch.setattr(
        report_domain,
        "context_projection_contract",
        lambda: {
            "authority": "projection",
            "can_close_required_gaps": False,
            "can_satisfy_proof": False,
        },
    )
    monkeypatch.setattr(report_domain, "available_profiles", lambda: ())
    monkeypatch.setattr(
        reporting_scoring,
        "standard_adapter_registry",
        lambda: {"std": {"boundary": "b", "fallback": "f", "exit_strategy": "e"}},
    )
    if profile == "product":
        monkeypatch.setattr(
            reporting_scoring,
            "hard_quality_floor_report",
            lambda _repo: {"ok": True, "required_gaps": []},
        )


def _assert_coordination_required_report(payload: dict[str, Any], *, profile: str) -> None:
    assert payload["ok"] is False
    assert payload["required_gaps"] == ("coordination_gap:current_scope_unknown",)
    assert payload["summary"]["profile"] == profile
    assert payload["summary"]["coordination_risk_count"] == 2
    assert payload["data"]["score_model"]["coordination_risk_penalty"] == 1
    assert payload["next_actions"] == ("ethos orient --json", "ethos lane status --json")
    coordination = payload["data"]["gap_layers"]["coordination_risk"]
    assert coordination["blocking"] is True
    assert coordination["required_gaps"] == ["coordination_gap:current_scope_unknown"]
    assert coordination["advisory_gaps"] == ["coordination_gap:foreign_scope_unknown:work/other"]


def test_scorecard_surfaces_status_coordination_required_gaps(monkeypatch, tmp_path: Path) -> None:
    """Only status-required coordination gaps should block the report scorecard."""

    _patch_report_scorecard_dependencies(monkeypatch, profile="product")

    payload: dict[str, Any] = report_domain.scorecard_report(tmp_path)

    _assert_coordination_required_report(payload, profile="product")


def test_adopter_scorecard_surfaces_status_coordination_required_gaps(
    monkeypatch, tmp_path: Path
) -> None:
    """Coordination blockers are shared governed-repository semantics across profiles."""

    _patch_report_scorecard_dependencies(monkeypatch, profile="gitlab")

    payload: dict[str, Any] = report_domain.scorecard_report(tmp_path)

    _assert_coordination_required_report(payload, profile="gitlab")
