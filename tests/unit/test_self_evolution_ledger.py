from __future__ import annotations

from pathlib import Path

from ethos_governance.evolution import evolution_candidates, evolution_ledger, evolution_report


def test_evolution_ledger_exposes_active_hypotheses() -> None:
    ledger = evolution_ledger(Path.cwd())

    assert "ethos-product-maturation" in {item["campaign"] for item in ledger["hypotheses"]}
    assert all(item["id"] for item in ledger["hypotheses"])


def test_evolution_report_scores_hypothesis_states() -> None:
    report = evolution_report(Path.cwd())

    assert report["ok"] is True
    assert report["active_count"] >= 1
    assert report["required_gaps"] == []


def test_evolution_candidates_are_derived_from_audit_signals() -> None:
    candidates = evolution_candidates(Path.cwd())

    assert candidates["ok"] is True
    candidate_ids = {item["id"] for item in candidates["candidates"]}
    assert "history-identity-normalization" not in candidate_ids
    assert "release-readiness-ratchet" in candidate_ids
