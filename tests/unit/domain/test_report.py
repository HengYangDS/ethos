from __future__ import annotations

from typing import Any

from ethos.domain import report as report_domain
from ethos_core.contracts.context_projection import ASSISTANT_TRUTH_BOUNDARY


def test_scorecard_blocks_product_hard_quality_floor(monkeypatch, tmp_path):
    """Report must not claim ready when standalone hard quality gates are blocked."""

    monkeypatch.setattr(
        report_domain._status,
        "audit_for_root",
        lambda _repo, **_kwargs: {
            "ok": True,
            "required_gaps": [],
            "governance_context": {"profile": "product"},
            "package_ontology": {"ok": True, "adapter_missing": []},
            "schemas": {"ok": True},
            "openspec": {"ok": True, "advisory_gaps": []},
        },
    )
    monkeypatch.setattr(report_domain, "docs_health_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "claims_report",
        lambda _repo: {"ok": True, "required_gaps": [], "advisory_gaps": []},
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
    monkeypatch.setattr(report_domain._gitio, "current_tracked_head", lambda _repo: "head")
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
        report_domain,
        "code_size_report",
        lambda _repo: {
            "ok": False,
            "required_gaps": ["code_size_exceeded:tests/unit/product/test_flat.py:999>800"],
        },
    )
    monkeypatch.setattr(
        report_domain,
        "module_layout_report",
        lambda _repo: {"ok": True, "state": "clean", "required_gaps": []},
    )
    monkeypatch.setattr(
        report_domain,
        "standard_adapter_registry",
        lambda: {"std": {"boundary": "b", "fallback": "f", "exit_strategy": "e"}},
    )

    payload: dict[str, Any] = report_domain.scorecard_report(tmp_path)

    assert payload["ok"] is False
    assert payload["required_gaps"] == (
        "code_size_exceeded:tests/unit/product/test_flat.py:999>800",
    )
    assert payload["summary"]["governance_gap_count"] == 1
    assert payload["next_actions"] == ("ethos quality code-size --json",)
    quality_floor = payload["data"]["gap_layers"]["hard_quality_floor"]
    assert quality_floor["blocking"] is True
    assert quality_floor["ok"] is False
    assert quality_floor["required_gaps"] == [
        "code_size_exceeded:tests/unit/product/test_flat.py:999>800"
    ]
