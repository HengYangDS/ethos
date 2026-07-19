from __future__ import annotations

from pathlib import Path

import ethos.domain.campaign.closeout as campaign_closeout
from ethos.domain.campaign.closeout import campaign_publication_report
from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_ledger
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.adoption.practice.selection import selection_ref_gaps

_CAMPAIGN_MANIFEST = Path("tests/fixtures/campaign/minimal.toml").read_text(encoding="utf-8")


def _write_campaign(root: Path, manifest: str = _CAMPAIGN_MANIFEST) -> None:
    (root / "openspec/changes/compression-foundation").mkdir(parents=True)
    path = root / "evolution/campaigns/compression/campaign.toml"
    path.parent.mkdir(parents=True)
    path.write_text(manifest, encoding="utf-8")


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
proof_refs = ["/workspace/proof.md", "https://example.test/proof.json", "pytest"]
review_refs = ["docs/decision.md"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["all refs resolve"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "hypothesis_proof_ref_unresolved:bad-proof-refs:/workspace/proof.md",
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


def test_campaign_report_exposes_manifest_steps_and_closeout_progress() -> None:
    report = campaign_report(Path.cwd(), campaign_id="terminal-openspec-productization")

    assert report["ok"] is True
    assert report["active_count"] >= 1
    campaign = report["campaigns"][0]
    assert campaign["id"] == "terminal-openspec-productization"
    assert campaign["objective"]
    assert campaign["state"] == "active"
    assert campaign["step_summary"]["total"] >= 8
    assert campaign["step_summary"]["planned"] >= 5
    assert campaign["step_summary"]["active"] == 0
    assert campaign["step_summary"]["closed"] >= 4
    assert campaign["lane_topology"]["kind"] == "openspec_lane_sequence"
    assert campaign["lane_topology"]["mode"] == "strict_serial"
    assert campaign["lane_topology"]["active_step"] == ""
    assert campaign["lane_topology"]["active_steps"] == []
    assert campaign["lane_topology"]["next_planned_step"] == "adopter-openspec-scaffold"
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
    hooked_step = next(item for item in campaign["steps"] if item["id"] == "hooked-write-admission")
    assert hooked_step["state"] == "closed"
    assert hooked_step["closeout"] == {
        "state": "retired",
        "accepted_head": "c17b8939f8d55082d226b3090c03a1c37cd48b37",
        "candidate_head": "d735b62add0a0d5dc7ebdf8cb0e7e1d8deadec30",
        "evidence": ["evidence/chronicle/hooked-write-admission/2026-07-02.md"],
    }


def test_campaign_report_defers_remote_publication_until_terminal_budget_settlement(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _write_campaign(tmp_path)
    monkeypatch.setattr(
        campaign_closeout,
        "source_budget_report",
        lambda _root: {
            "campaign_id": "compression",
            "terminal_target_met": False,
            "active_debt": {"ids": ["temporary-compiler"]},
        },
    )

    report = campaign_publication_report(tmp_path)

    assert report["required_gaps"] == [
        "campaign_publication_campaign_active:compression",
        "campaign_publication_step_not_retired:compression",
        "campaign_publication_terminal_budget_unmet:compression",
        "campaign_publication_active_debt:compression:temporary-compiler",
    ]


def test_invalid_campaign_manifest_blocks_repository_publication(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _write_campaign(tmp_path, _CAMPAIGN_MANIFEST.replace("campaign_terminal", "unknown"))
    monkeypatch.setattr(
        campaign_closeout,
        "source_budget_report",
        lambda _root: {
            "campaign_id": "",
            "required_gaps": [],
            "active_debt": {"ids": []},
        },
    )

    publication = campaign_publication_report(tmp_path)

    assert publication["mode"] == "invalid"
    assert publication["remote_publication_admission"] == "blocked"


def test_campaign_publication_requires_the_budget_bound_campaign(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        campaign_closeout,
        "source_budget_report",
        lambda _root: {
            "campaign_id": "declared-compression",
            "terminal_target_met": False,
            "active_debt": {"ids": []},
            "required_gaps": [],
        },
    )

    report = campaign_publication_report(
        tmp_path,
        campaigns={"campaigns": [], "required_gaps": [], "ok": True},
    )

    assert report["remote_publication_admission"] == "blocked"
    assert report["required_gaps"] == [
        "campaign_publication_bound_campaign_missing:declared-compression"
    ]


def test_campaign_publication_payload_is_declared_in_workflow_policy() -> None:
    source = Path("system/workflows.toml").read_text(encoding="utf-8")

    assert "publication_projection = '''" in source
    assert "def publication(" not in Path(
        "packages/ethos-core/src/ethos_core/contracts/workflow.py"
    ).read_text(encoding="utf-8")


def test_filtered_campaign_status_keeps_repository_publication_scope(
    monkeypatch, tmp_path: Path
) -> None:
    _write_campaign(tmp_path)
    monkeypatch.setattr(
        campaign_closeout,
        "source_budget_report",
        lambda _root: {
            "campaign_id": "compression",
            "terminal_target_met": False,
            "active_debt": {"ids": []},
            "required_gaps": [],
        },
    )

    filtered = campaign_report(tmp_path, campaign_id="compression")
    publication = campaign_publication_report(tmp_path)

    assert [item["id"] for item in filtered["campaigns"]] == ["compression"]
    assert publication["scope"] == "repository"
    assert publication["remote_publication_admission"] == "blocked"


def test_evolution_report_exposes_practice_selection_and_fate() -> None:
    report = evolution_report(Path.cwd())

    assert report["ok"] is True
    selection = report["selection"]
    assert selection["practice_claim_count"] >= 1
    assert {item["id"] for item in selection["practice_claims"]} >= {
        "workflow-runtime-trustworthy-practice-claim"
    }
    assert selection["candidate_set_count"] >= 1
    assert selection["experiment_protocol_count"] >= 1
    assert selection["evaluation_record_count"] >= 1
    assert selection["supports_multi_candidate_selection"] is True
    assert selection["supports_practice_lifecycle"] is True
    assert "introduce" in selection["practice_change_kinds"]
    ledger = report["ledger"]
    assert {item["subject"] for item in ledger["practice_claims"]} >= {
        "ethos:workflow-runtime-practice-evolution"
    }
    assert {item["commitment_effect"] for item in selection["practice_claims"]} >= {
        "create_commitment"
    }
    selected = {
        item["selected_candidate"]
        for item in ledger["evaluation_records"]
        if item.get("state") == "selected"
    }
    assert "ethos-native-runtime" in selected
    candidate_ids = {
        candidate["id"]
        for candidate_set in ledger["candidate_sets"]
        for candidate in candidate_set["candidates"]
    }
    assert {
        "openspec-alone",
        "comet-direct",
        "spec-kit-grammar",
        "task-master-graph",
        "fspec-scenario-coverage",
        "method-pack-composition",
        "ethos-native-runtime",
    } <= candidate_ids


def test_evolution_report_distinguishes_introduction_from_supersession(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "research.md").write_text("# Research\n", encoding="utf-8")
    (tmp_path / "docs" / "decision.md").write_text("# Decision\n", encoding="utf-8")
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "intro-hypothesis"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "A new practice may be introduced without an incumbent."
challenge = "Calling every introduction supersession hides the boundary model."
transition = "shape -> canonize"
proof_refs = ["ethos status --json"]
review_refs = ["docs/research.md"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["practice fate is explicit"]

[[practice_change]]
id = "new-practice"
state = "active"
change_kind = "introduce"
commitment_effect = "create_commitment"
practice = "new bounded practice"
carrier_kind = "workflow"
summary = "Introduces a new practice without replacing an incumbent."
boundary = "No prior practice owns this boundary."
evidence_refs = ["docs/research.md"]
decision_refs = ["docs/decision.md"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is True
    assert report["selection"]["practice_change_kinds"] == ["introduce"]


def test_evolution_report_requires_practice_claim_links(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "research.md").write_text("# Research\n", encoding="utf-8")
    (tmp_path / "docs" / "decision.md").write_text("# Decision\n", encoding="utf-8")
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "claim-hypothesis"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "A practice claim must bind its proof path."
challenge = "Unlinked mechanism records are not repository truth."
transition = "shape -> canonize"
proof_refs = ["ethos status --json"]
review_refs = ["docs/research.md"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["practice claim links resolve"]

[[practice_claim]]
id = "root-practice"
state = "evaluated"
owner = "ethos-maintainers"
subject = "ethos:sample-practice"
question = "Which practice deserves trust?"
claim = "A practice is trustworthy only through bounded evidence."
boundary = "The commitment is the root object; mechanism records are subordinate."
incumbent_relation = "No incumbent exists for this sample boundary."
falsifiers = ["the selected candidate cannot bind evidence"]
candidate_set = "missing-candidate-set"
experiment_protocol = "missing-experiment"
evaluation_record = "missing-evaluation"
commitment_effect = "invalid_effect"
practice_changes = ["missing-practice-change"]
commitment_targets = ["docs/missing-contract.md"]
evidence_refs = ["docs/research.md"]
decision_refs = ["docs/decision.md"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "practice_claim_commitment_effect_invalid:root-practice:invalid_effect",
        "practice_claim_candidate_set_missing:root-practice:missing-candidate-set",
        "practice_claim_experiment_protocol_missing:root-practice:missing-experiment",
        "practice_claim_evaluation_record_missing:root-practice:missing-evaluation",
        "practice_claim_practice_change_missing:root-practice:missing-practice-change",
        "practice_claim_commitment_ref_missing:root-practice:docs/missing-contract.md",
    ]


def test_evolution_report_rejects_introduction_with_incumbents(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "research.md").write_text("# Research\n", encoding="utf-8")
    (tmp_path / "docs" / "decision.md").write_text("# Decision\n", encoding="utf-8")
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "bad-intro-hypothesis"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Introductions must not pretend to replace incumbents."
challenge = "Incumbents imply refine, supersede, or retire analysis."
transition = "shape -> canonize"
proof_refs = ["ethos status --json"]
review_refs = ["docs/research.md"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["practice fate is explicit"]

[[practice_change]]
id = "bad-introduction"
state = "active"
change_kind = "introduce"
commitment_effect = "create_commitment"
practice = "new bounded practice"
carrier_kind = "workflow"
summary = "Claims introduction while naming an incumbent."
boundary = "Prior practice exists."
incumbents = ["old-practice"]
evidence_refs = ["docs/research.md"]
decision_refs = ["docs/decision.md"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["practice_change_introduce_has_incumbents:bad-introduction"]


def test_evolution_report_rejects_practice_change_commitment_effect_mismatch(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "research.md").write_text("# Research\n", encoding="utf-8")
    (tmp_path / "docs" / "decision.md").write_text("# Decision\n", encoding="utf-8")
    ledger = tmp_path / "evolution" / "ledger.toml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        """
schema = "system/schemas/kernel/evolution-ledger.schema.json"

[[hypothesis]]
id = "effect-hypothesis"
campaign = "sample-campaign"
state = "active"
owner = "ethos-maintainers"
claim = "Practice fate must match commitment effect."
challenge = "Supersession that creates instead of replaces hides commitment semantics."
transition = "shape -> canonize"
proof_refs = ["ethos status --json"]
review_refs = ["docs/research.md"]
decision_refs = ["docs/decision.md"]
retirement_conditions = ["practice fate is explicit"]

[[practice_change]]
id = "bad-effect"
state = "active"
change_kind = "supersede"
commitment_effect = "create_commitment"
practice = "new bounded practice"
carrier_kind = "workflow"
summary = "Claims supersession while creating instead of replacing."
boundary = "Prior practice exists."
incumbents = ["old-practice"]
retirement_conditions = ["old practice is migrated"]
evidence_refs = ["docs/research.md"]
decision_refs = ["docs/decision.md"]
""".strip(),
        encoding="utf-8",
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "practice_change_commitment_effect_mismatch:bad-effect:supersede:"
        "create_commitment:replace_commitment"
    ]


def test_selection_ref_gaps_cover_missing_practice_claim_and_candidate_set_fields(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "research.md").write_text("# Research\n", encoding="utf-8")
    gaps = selection_ref_gaps(
        tmp_path,
        {
            "practice_claims": [
                {
                    "id": "fieldless-claim",
                    "commitment_targets": [],
                    "evidence_refs": "docs/research.md",
                    "decision_refs": ["docs/missing-decision.md"],
                }
            ],
            "candidate_sets": [
                {
                    "id": "thin-candidates",
                    "selection_policy": "manual",
                    "decision_refs": "docs/research.md",
                    "candidates": [
                        {
                            "id": "candidate-a",
                            "hypothesis_ref": "missing-hypothesis",
                            "evidence_refs": ["docs/missing-evidence.md"],
                        }
                    ],
                }
            ],
            "hypotheses": [],
            "experiment_protocols": [],
            "evaluation_records": [],
            "practice_changes": [],
        },
    )

    assert {
        "practice_claim_owner_missing:fieldless-claim",
        "practice_claim_commitment_effect_missing:fieldless-claim",
        "practice_claim_practice_changes_missing:fieldless-claim",
        "practice_claim_commitment_refs_missing:fieldless-claim",
        "practice_claim_evidence_refs_invalid:fieldless-claim",
        "practice_claim_decision_ref_missing:fieldless-claim:docs/missing-decision.md",
        "candidate_set_too_small:thin-candidates",
        "candidate_set_selection_policy_invalid:thin-candidates",
        "candidate_set_decision_refs_invalid:thin-candidates",
        "candidate_hypothesis_ref_missing:thin-candidates:candidate-a:missing-hypothesis",
        "candidate_evidence_ref_missing:thin-candidates:candidate-a:docs/missing-evidence.md",
    } <= set(gaps)


def test_selection_ref_gaps_cover_experiment_evaluation_and_practice_change_edges(
    tmp_path: Path,
) -> None:
    gaps = selection_ref_gaps(
        tmp_path,
        {
            "hypotheses": [{"id": "known-hypothesis"}],
            "candidate_sets": [{"id": "known-candidates", "candidates": [{}, {}]}],
            "experiment_protocols": [
                {
                    "id": "bad-experiment",
                    "candidate_set": "missing-candidates",
                    "hypothesis_refs": ["missing-hypothesis"],
                    "evidence_refs": [],
                }
            ],
            "evaluation_records": [
                {
                    "id": "bad-evaluation",
                    "candidate_set": "missing-candidates",
                    "experiment_protocol": "missing-experiment",
                    "selected_candidate": "same",
                    "rejected_candidates": ["same"],
                    "evidence_refs": [],
                    "decision_refs": [],
                },
                {
                    "id": "unselected-evaluation",
                    "candidate_set": "known-candidates",
                    "experiment_protocol": "bad-experiment",
                    "metric_results": [],
                    "evidence_refs": [],
                    "decision_refs": [],
                },
            ],
            "practice_changes": [
                {
                    "id": "bad-retirement",
                    "change_kind": "retire",
                    "commitment_effect": "unknown_effect",
                    "evidence_refs": [],
                    "decision_refs": [],
                },
                {
                    "id": "missing-effect",
                    "change_kind": "refine",
                    "practice": "practice",
                    "carrier_kind": "workflow",
                    "summary": "summary",
                    "boundary": "boundary",
                    "evidence_refs": [],
                    "decision_refs": [],
                },
                {
                    "id": "unknown-effect",
                    "change_kind": "unknown",
                    "commitment_effect": "unknown_effect",
                    "practice": "practice",
                    "carrier_kind": "workflow",
                    "summary": "summary",
                    "boundary": "boundary",
                    "evidence_refs": [],
                    "decision_refs": [],
                },
            ],
            "practice_claims": [],
        },
    )

    assert {
        "experiment_candidate_set_missing:bad-experiment:missing-candidates",
        "experiment_hypothesis_ref_missing:bad-experiment:missing-hypothesis",
        "experiment_variables_missing:bad-experiment",
        "experiment_evidence_refs_missing:bad-experiment",
        "evaluation_candidate_set_missing:bad-evaluation:missing-candidates",
        "evaluation_experiment_protocol_missing:bad-evaluation:missing-experiment",
        "evaluation_selected_candidate_missing:unselected-evaluation",
        "evaluation_rejected_candidates_missing:unselected-evaluation",
        "evaluation_selected_candidate_also_rejected:bad-evaluation:same",
        "evaluation_metric_results_missing:bad-evaluation",
        "evaluation_evidence_refs_missing:bad-evaluation",
        "practice_change_practice_missing:bad-retirement",
        "practice_change_commitment_effect_mismatch:bad-retirement:retire:unknown_effect:"
        "remove_commitment",
        "practice_change_incumbents_missing:bad-retirement",
        "practice_change_retirement_conditions_missing:bad-retirement",
        "practice_change_evidence_refs_missing:bad-retirement",
        "practice_change_commitment_effect_missing:missing-effect",
        "practice_change_commitment_effect_invalid:unknown-effect:unknown_effect",
    } <= set(gaps)


def test_selection_ref_gaps_reject_absolute_and_url_path_refs(tmp_path: Path) -> None:
    gaps = selection_ref_gaps(
        tmp_path,
        {
            "hypotheses": [],
            "practice_claims": [
                {
                    "id": "external-refs",
                    "owner": "owner",
                    "subject": "subject",
                    "question": "question",
                    "claim": "claim",
                    "boundary": "boundary",
                    "incumbent_relation": "none",
                    "falsifiers": ["falsifier"],
                    "commitment_effect": "create_commitment",
                    "practice_changes": ["known-change"],
                    "commitment_targets": ["/workspace/contract.md"],
                    "evidence_refs": ["https://example.test/evidence.md"],
                    "decision_refs": [""],
                }
            ],
            "practice_changes": [{"id": "known-change"}],
            "candidate_sets": [],
            "experiment_protocols": [],
            "evaluation_records": [],
        },
    )

    assert {
        "practice_claim_commitment_ref_missing:external-refs:/workspace/contract.md",
        "practice_claim_evidence_ref_missing:external-refs:https://example.test/evidence.md",
        "practice_claim_decision_ref_missing:external-refs:",
    } <= set(gaps)
