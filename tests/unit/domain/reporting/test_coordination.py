from __future__ import annotations

import ethos.domain.report as report_domain
import ethos.domain.reporting.parity.core as reporting_parity
from tests.support.reporting import patch_scorecard_dependencies

STATUS = {
    "coordination": {
        "required_gaps": ["coordination_gap:current_scope_unknown"],
        "advisory_gaps": ["coordination_gap:foreign_scope_unknown:work/other"],
    }
}


def test_scorecard_surfaces_status_coordination_required_gaps(monkeypatch, tmp_path) -> None:
    """Coordination blockers are shared governed-repository semantics across profiles."""
    for profile in ("product", "gitlab"):
        patch_scorecard_dependencies(monkeypatch, profile=profile, status=STATUS)
        if profile != "product":
            monkeypatch.setattr(
                reporting_parity, "profile_identity", lambda _repo: "domain-adopter"
            )
        payload = report_domain.scorecard_report(tmp_path)
        assert payload["ok"] is False
        assert payload["required_gaps"] == ("coordination_gap:current_scope_unknown",)
        assert payload["summary"]["profile"] == profile
        assert payload["summary"]["coordination_risk_count"] == 2
        assert payload["data"]["score_model"]["coordination_risk_penalty"] == 1
        assert payload["next_actions"] == (
            "ethos orient --json",
            "ethos lane status --json",
        )
        coordination = payload["data"]["gap_layers"]["coordination_risk"]
        assert coordination["blocking"] is True
        assert coordination["required_gaps"] == ["coordination_gap:current_scope_unknown"]
        assert coordination["advisory_gaps"] == [
            "coordination_gap:foreign_scope_unknown:work/other"
        ]
