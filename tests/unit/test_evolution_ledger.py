from __future__ import annotations

from pathlib import Path

from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_candidates
from ethos.repository.adoption.evolution import evolution_ledger
from ethos.repository.adoption.evolution import evolution_report


def test_evolution_ledger_exposes_active_hypotheses() -> None:
    ledger = evolution_ledger(Path.cwd())

    assert "ethos-product-maturation" in {item["campaign"] for item in ledger["hypotheses"]}
    assert all(item["id"] for item in ledger["hypotheses"])
    assert all(item["owner"] for item in ledger["hypotheses"])
    assert all(item["transition"] for item in ledger["hypotheses"])
    assert all(item["proof_refs"] for item in ledger["hypotheses"])
    assert all(item["review_refs"] for item in ledger["hypotheses"])
    assert all(item["decision_refs"] for item in ledger["hypotheses"])
    assert all(item["retirement_conditions"] for item in ledger["hypotheses"])


def test_evolution_report_scores_hypothesis_states() -> None:
    report = evolution_report(Path.cwd())

    assert report["ok"] is True
    assert report["active_count"] >= 1
    assert report["required_gaps"] == []


def test_evolution_candidates_are_derived_from_audit_signals() -> None:
    candidates = evolution_candidates(Path.cwd())

    assert candidates["ok"] is True
    candidate_ids = {item["id"] for item in candidates["candidates"]}
    assert {
        "release-readiness-ratchet",
        "asset-quality-kernel",
    } <= candidate_ids
    assert all(item["challenge"] for item in candidates["candidates"])


def test_campaign_report_exposes_manifest_steps_and_closeout_progress() -> None:
    report = campaign_report(Path.cwd(), campaign_id="terminal-openspec-productization")

    assert report["ok"] is True
    assert report["active_count"] >= 1
    campaign = report["campaigns"][0]
    assert campaign["id"] == "terminal-openspec-productization"
    assert campaign["objective"]
    assert campaign["state"] == "active"
    assert campaign["step_summary"]["total"] >= 8
    assert {"planned", "active", "closed"} <= set(campaign["step_summary"])
    assert campaign["lane_topology"]["kind"] == "openspec_lane_sequence"
    assert campaign["lane_topology"]["mode"] == "strict_serial"
    assert campaign["lane_topology"]["active_step"] == "hooked-write-admission"
    assert campaign["lane_topology"]["edges"][0] == {
        "from": "campaign-orchestration",
        "to": "openspec-product-protocol",
        "rule": "closeout_retired_before_activation",
    }
    first_step = campaign["steps"][0]
    assert first_step["ordinal"] == 1
    assert first_step["depends_on"] == []
    assert first_step["openspec_change"]
    assert first_step["work_lane"].startswith("work/")
    assert first_step["claim_id"]
    assert first_step["closeout"]["state"] in {"planned", "landed", "closed", "retired"}
    active_step = next(item for item in campaign["steps"] if item["state"] == "active")
    assert active_step["depends_on"] == ["openspec-archive-closeout"]
