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


def test_evolution_report_requires_structural_entries_to_bind_repository_evidence(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[entry]]
id = "destructive-simplification"
type = "experiment"
state = "accepted"
summary = "Deletes a stale subsystem after proof."
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "evolution_hypotheses_missing",
        "entry_evidence_refs_missing:destructive-simplification",
        "entry_decision_refs_missing:destructive-simplification",
    ]


def test_evolution_report_rejects_unresolved_hypothesis_and_entry_refs(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[entry]]
id = "structural-change"
type = "experiment"
state = "accepted"
summary = "A structural change with unresolved refs."
evidence_refs = ["evidence/chronicle/missing/2026-07-08.md"]
decision_refs = ["docs/decisions/accepted/DR-missing.md"]

[[hypothesis]]
id = "ref-bound-hypothesis"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Structural evolution must bind real proof."
challenge = "Unresolved refs make the evolution ledger a second narrative store."
transition = "shape -> canonize"
proof_refs = ["ethos quality missing-proof --json"]
review_refs = ["tests/unit/governance/test_missing.py"]
decision_refs = ["docs/decisions/accepted/DR-missing.md"]
retirement_conditions = ["all refs resolve"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "hypothesis_proof_ref_unresolved:ref-bound-hypothesis:ethos quality missing-proof --json",
        "hypothesis_review_ref_missing:ref-bound-hypothesis:tests/unit/governance/test_missing.py",
        "hypothesis_decision_ref_missing:ref-bound-hypothesis:docs/decisions/accepted/DR-missing.md",
        "entry_evidence_ref_missing:structural-change:evidence/chronicle/missing/2026-07-08.md",
        "entry_decision_ref_missing:structural-change:docs/decisions/accepted/DR-missing.md",
    ]


def test_evolution_report_accepts_existing_path_refs_and_known_ethos_commands(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "decisions" / "accepted.md").write_text(
        "# Accepted\n",
        encoding="utf-8",
    )
    (tmp_path / "evidence" / "chronicle" / "lane").mkdir(parents=True)
    (tmp_path / "evidence" / "chronicle" / "lane" / "2026-07-08.md").write_text(
        "# Chronicle\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "proof.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[entry]]
id = "structural-change"
type = "experiment"
state = "accepted"
summary = "A structural change with resolved refs."
evidence_refs = ["evidence/chronicle/lane/2026-07-08.md"]
decision_refs = ["docs/decisions/accepted.md"]

[[hypothesis]]
id = "ref-bound-hypothesis"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Structural evolution must bind real proof."
challenge = "Resolved refs keep the evolution ledger bound."
transition = "shape -> canonize"
proof_refs = ["ethos status --json", "tests/proof.py"]
review_refs = ["tests/proof.py"]
decision_refs = ["docs/decisions/accepted.md"]
retirement_conditions = ["all refs resolve"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_evolution_report_rejects_path_like_and_plain_unknown_proof_refs(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "decision.md").write_text("# Decision\n", encoding="utf-8")
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "bad-proof-refs"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Proof refs must resolve."
challenge = "Unresolved refs make evolution unreviewable."
transition = "shape -> canonize"
proof_refs = ["/tmp/proof.md", "https://example.test/proof.json", "pytest"]
review_refs = ["docs/decision.md"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["all refs resolve"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "hypothesis_proof_ref_unresolved:bad-proof-refs:/tmp/proof.md",
        "hypothesis_proof_ref_unresolved:bad-proof-refs:https://example.test/proof.json",
        "hypothesis_proof_ref_unresolved:bad-proof-refs:pytest",
    ]


def test_evolution_report_treats_non_list_entry_refs_as_unresolved(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "valid-hypothesis"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Evolution needs one active hypothesis."
challenge = "Without one, entries cannot be judged."
transition = "shape -> canonize"
proof_refs = ["ethos status --json"]
review_refs = ["docs/decision.md"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["all refs resolve"]

[[entry]]
id = "bad-entry-ref-shape"
type = "experiment"
state = "accepted"
summary = "A structural change with scalar refs."
evidence_refs = "evidence/chronicle/lane/2026-07-08.md"
decision_refs = "docs/decisions/accepted.md"
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "hypothesis_review_ref_missing:valid-hypothesis:docs/decision.md",
        "hypothesis_decision_ref_missing:valid-hypothesis:docs/decision.md",
        "entry_evidence_refs_invalid:bad-entry-ref-shape",
        "entry_decision_refs_invalid:bad-entry-ref-shape",
    ]


def test_evolution_report_rejects_non_list_hypothesis_refs(tmp_path: Path) -> None:
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "bad-hypothesis-ref-shape"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Hypothesis refs must be arrays."
challenge = "Scalar refs hide review and proof boundaries."
transition = "shape -> canonize"
proof_refs = "ethos status --json"
review_refs = "docs/decision.md"
decision_refs = "docs/decision.md"
retirement_conditions = ["all refs resolve"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "hypothesis_proof_refs_invalid:bad-hypothesis-ref-shape",
        "hypothesis_review_refs_invalid:bad-hypothesis-ref-shape",
        "hypothesis_decision_refs_invalid:bad-hypothesis-ref-shape",
    ]


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
