from __future__ import annotations

from pathlib import Path

import pytest
import tomli_w

import ethos.domain.campaign.closeout as campaign_closeout
import ethos.repository.adoption.evolution as evolution
from ethos.domain.campaign.closeout import campaign_publication_report
from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_candidates
from ethos.repository.adoption.evolution import evolution_ledger
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.adoption.practice.selection import selection_ref_gaps

_CAMPAIGN_MANIFEST = Path("tests/fixtures/campaign/minimal.toml").read_text(encoding="utf-8")
_LEDGER_SCHEMA = "system/schemas/kernel/evolution-ledger.schema.json"


def _write_campaign(root: Path, manifest: str = _CAMPAIGN_MANIFEST) -> None:
    (root / "openspec/changes/compression-foundation").mkdir(parents=True)
    path = root / "evolution/campaigns/compression/campaign.toml"
    path.parent.mkdir(parents=True)
    path.write_text(manifest, encoding="utf-8")


def _write_ledger(root: Path, **sections: object) -> None:
    path = root / "evolution/ledger.toml"
    path.parent.mkdir(parents=True)
    path.write_text(tomli_w.dumps({"schema": _LEDGER_SCHEMA, **sections}), encoding="utf-8")


def _write_refs(root: Path, *refs: str) -> None:
    for ref in refs:
        path = root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# reference\n", encoding="utf-8")


def _hypothesis(identifier: str, **overrides: object) -> dict[str, object]:
    return {
        "id": identifier,
        "campaign": "sample-campaign",
        "state": "active",
        "owner": "ethos-maintainers",
        "claim": "Structural evolution must bind real proof.",
        "challenge": "Unresolved refs make evolution unreviewable.",
        "transition": "shape -> canonize",
        "proof_refs": ["ethos status --json"],
        "review_refs": ["docs/research.md"],
        "decision_refs": ["docs/decision.md"],
        "retirement_conditions": ["all refs resolve"],
    } | overrides


def _practice_change(identifier: str, **overrides: object) -> dict[str, object]:
    return {
        "id": identifier,
        "state": "active",
        "change_kind": "introduce",
        "commitment_effect": "create_commitment",
        "practice": "new bounded practice",
        "carrier_kind": "workflow",
        "summary": "Introduces one bounded practice.",
        "boundary": "No prior practice owns this boundary.",
        "evidence_refs": ["docs/research.md"],
        "decision_refs": ["docs/decision.md"],
    } | overrides


def _assert_evolution_gaps(root: Path, expected: list[str]) -> None:
    report = evolution_report(root)
    assert report["ok"] is False
    assert report["required_gaps"] == expected


def _mock_source_budget(monkeypatch: pytest.MonkeyPatch, **report: object) -> None:
    monkeypatch.setattr(campaign_closeout, "source_budget_report", lambda _root: report)


def _campaign_gaps(
    root: Path,
    *,
    step_state: str,
    closeout_state: str = "planned",
    carrier: str = "active",
) -> list[str]:
    terminal = closeout_state in {"closed", "retired"}
    manifest = (
        _CAMPAIGN_MANIFEST.replace(
            'title = "Foundation"\nstate = "active"',
            f'title = "Foundation"\nstate = "{step_state}"',
            1,
        )
        .replace('state = "planned"', f'state = "{closeout_state}"', 1)
        .replace(
            'accepted_head = ""',
            f'accepted_head = "{"a" * 40 if terminal else ""}"',
        )
        .replace(
            'candidate_head = ""',
            f'candidate_head = "{"b" * 40 if terminal else ""}"',
        )
        .replace(
            "evidence = []",
            'evidence = ["evidence/chronicle/campaign/2026-07-19.md"]'
            if terminal
            else "evidence = []",
        )
    )
    carrier_path = (
        root / "openspec/changes/compression-foundation"
        if carrier == "active"
        else root / "openspec/changes/archive/2026-07-19-compression-foundation"
    )
    carrier_path.mkdir(parents=True)
    path = root / "evolution/campaigns/compression/campaign.toml"
    path.parent.mkdir(parents=True)
    path.write_text(manifest, encoding="utf-8")
    return campaign_report(root)["required_gaps"]


def test_campaign_helpers_fail_closed_for_missing_declarations(monkeypatch, tmp_path: Path) -> None:
    carrier_state = getattr(evolution, "_openspec" + "_carrier_state")
    list_items = getattr(evolution, "_list" + "_items")
    assert carrier_state(tmp_path, "") == "missing"
    assert list_items("not-a-list") == []
    monkeypatch.setattr(
        evolution,
        "load_workflow_contract_declaration",
        lambda _root: type("D", (), {"campaign": None})(),
    )

    with pytest.raises(ValueError, match="campaign workflow policy missing"):
        evolution.campaign_policy(tmp_path)


def test_campaign_public_policy_preserves_candidate_carrier_and_closeout_gaps(
    tmp_path: Path,
) -> None:
    assert "campaign_step_active_openspec_archived:compression:foundation" in _campaign_gaps(
        tmp_path / "active-archived", step_state="active", carrier="archived"
    )
    assert "campaign_step_preland_openspec_not_archived:compression:foundation" in (
        _campaign_gaps(tmp_path / "preland-active", step_state="archive_ready")
    )
    terminal = _campaign_gaps(
        tmp_path / "preland-terminal",
        step_state="archive_ready",
        closeout_state="retired",
        carrier="archived",
    )
    assert "campaign_step_terminal_closeout_nonterminal:compression:foundation" in terminal
    assert all("archive_ready_closeout_terminal" not in gap for gap in terminal)
    assert "campaign_step_terminal_openspec_not_archived:compression:foundation" in (
        _campaign_gaps(
            tmp_path / "terminal-active",
            step_state="closed",
            closeout_state="retired",
        )
    )


def test_evolution_ledger_exposes_active_hypotheses() -> None:
    ledger = evolution_ledger(Path.cwd())

    assert "ethos-product-maturation" in {item["campaign"] for item in ledger["hypotheses"]}
    required = "id\nowner\ntransition\nproof_refs".splitlines()
    required += "review_refs\ndecision_refs\nretirement_conditions".splitlines()
    assert all(all(item[key] for key in required) for item in ledger["hypotheses"])


def test_evolution_report_scores_hypothesis_states() -> None:
    report = evolution_report(Path.cwd())

    assert report["ok"] is True
    assert report["active_count"] >= 1
    assert report["required_gaps"] == []


def test_evolution_report_requires_structural_entries_to_bind_repository_evidence(
    tmp_path: Path,
) -> None:
    _write_ledger(
        tmp_path,
        entry=[
            {
                "id": "destructive-simplification",
                "type": "experiment",
                "state": "accepted",
                "summary": "Deletes a stale subsystem after proof.",
            }
        ],
    )

    expected = [
        "evolution_hypotheses_missing",
        "entry_evidence_refs_missing:destructive-simplification",
        "entry_decision_refs_missing:destructive-simplification",
    ]
    _assert_evolution_gaps(tmp_path, expected)


def test_evolution_report_rejects_unresolved_hypothesis_and_entry_refs(
    tmp_path: Path,
) -> None:
    _write_ledger(
        tmp_path,
        entry=[
            {
                "id": "structural-change",
                "type": "experiment",
                "state": "accepted",
                "summary": "A structural change with unresolved refs.",
                "evidence_refs": ["evidence/chronicle/missing/2026-07-08.md"],
                "decision_refs": ["docs/decisions/accepted/DR-missing.md"],
            }
        ],
        hypothesis=[
            _hypothesis(
                "ref-bound-hypothesis",
                proof_refs=["ethos quality missing-proof --json"],
                review_refs=["tests/unit/governance/test_missing.py"],
                decision_refs=["docs/decisions/accepted/DR-missing.md"],
            )
        ],
    )

    expected = [
        "hypothesis_proof_ref_unresolved:ref-bound-hypothesis:ethos quality missing-proof --json",
        "hypothesis_review_ref_missing:ref-bound-hypothesis:tests/unit/governance/test_missing.py",
        "hypothesis_decision_ref_missing:ref-bound-hypothesis:docs/decisions/accepted/DR-missing.md",
        "entry_evidence_ref_missing:structural-change:evidence/chronicle/missing/2026-07-08.md",
        "entry_decision_ref_missing:structural-change:docs/decisions/accepted/DR-missing.md",
    ]
    _assert_evolution_gaps(tmp_path, expected)


def test_evolution_report_accepts_existing_path_refs_and_known_ethos_commands(
    tmp_path: Path,
) -> None:
    _write_refs(
        tmp_path,
        "docs/decisions/accepted.md",
        "evidence/chronicle/lane/2026-07-08.md",
        "tests/proof.py",
    )
    _write_ledger(
        tmp_path,
        entry=[
            {
                "id": "structural-change",
                "type": "experiment",
                "state": "accepted",
                "summary": "A structural change with resolved refs.",
                "evidence_refs": ["evidence/chronicle/lane/2026-07-08.md"],
                "decision_refs": ["docs/decisions/accepted.md"],
            }
        ],
        hypothesis=[
            _hypothesis(
                "ref-bound-hypothesis",
                proof_refs=["ethos status --json", "tests/proof.py"],
                review_refs=["tests/proof.py"],
                decision_refs=["docs/decisions/accepted.md"],
            )
        ],
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_evolution_report_rejects_path_like_and_plain_unknown_proof_refs(
    tmp_path: Path,
) -> None:
    _write_refs(tmp_path, "docs/decision.md")
    _write_ledger(
        tmp_path,
        hypothesis=[
            _hypothesis(
                "bad-proof-refs",
                proof_refs=["/workspace/proof.md", "https://example.test/proof.json", "pytest"],
                review_refs=["docs/decision.md"],
            )
        ],
    )

    expected = [
        "hypothesis_proof_ref_unresolved:bad-proof-refs:/workspace/proof.md",
        "hypothesis_proof_ref_unresolved:bad-proof-refs:https://example.test/proof.json",
        "hypothesis_proof_ref_unresolved:bad-proof-refs:pytest",
    ]
    _assert_evolution_gaps(tmp_path, expected)


def test_evolution_report_treats_non_list_entry_refs_as_unresolved(
    tmp_path: Path,
) -> None:
    _write_ledger(
        tmp_path,
        hypothesis=[
            _hypothesis(
                "valid-hypothesis",
                review_refs=["docs/decision.md"],
                decision_refs=["docs/decision.md"],
            )
        ],
        entry=[
            {
                "id": "bad-entry-ref-shape",
                "type": "experiment",
                "state": "accepted",
                "summary": "A structural change with scalar refs.",
                "evidence_refs": "evidence/chronicle/lane/2026-07-08.md",
                "decision_refs": "docs/decisions/accepted.md",
            }
        ],
    )

    expected = [
        "hypothesis_review_ref_missing:valid-hypothesis:docs/decision.md",
        "hypothesis_decision_ref_missing:valid-hypothesis:docs/decision.md",
        "entry_evidence_refs_invalid:bad-entry-ref-shape",
        "entry_decision_refs_invalid:bad-entry-ref-shape",
    ]
    _assert_evolution_gaps(tmp_path, expected)


def test_evolution_report_rejects_non_list_hypothesis_refs(tmp_path: Path) -> None:
    _write_ledger(
        tmp_path,
        hypothesis=[
            _hypothesis(
                "bad-hypothesis-ref-shape",
                proof_refs="ethos status --json",
                review_refs="docs/decision.md",
                decision_refs="docs/decision.md",
            )
        ],
    )

    expected = [
        "hypothesis_proof_refs_invalid:bad-hypothesis-ref-shape",
        "hypothesis_review_refs_invalid:bad-hypothesis-ref-shape",
        "hypothesis_decision_refs_invalid:bad-hypothesis-ref-shape",
    ]
    _assert_evolution_gaps(tmp_path, expected)


def test_campaign_report_exposes_manifest_steps_and_closeout_progress() -> None:
    report = campaign_report(Path.cwd(), campaign_id="terminal-openspec-productization")

    assert (report["ok"], report["active_count"] >= 1) == (True, True)
    campaign = report["campaigns"][0]
    identity = campaign["id"], campaign["state"], bool(campaign["objective"])
    assert identity == ("terminal-openspec-productization", "active", True)
    summary = campaign["step_summary"]
    assert (summary["total"] >= 8, summary["planned"] >= 4) == (True, True)
    assert (summary["active"], summary["closed"] >= 4) == (0, True)
    topology = campaign["lane_topology"]
    assert (topology["kind"], topology["mode"]) == ("openspec_lane_sequence", "strict_serial")
    assert (topology["active_step"], topology["active_steps"]) == ("", [])
    assert topology["next_planned_step"] == "projection-digest-governance"
    assert topology["edges"][0] == {
        "from": "campaign-orchestration",
        "to": "openspec-product-protocol",
        "rule": "closeout_retired_before_activation",
    }
    first_step = campaign["steps"][0]
    assert (first_step["ordinal"], first_step["depends_on"]) == (1, [])
    assert all(first_step[key] for key in ("openspec_change", "claim_id"))
    assert first_step["work_lane"].startswith("work/")
    assert first_step["closeout"]["state"] in {"planned", "landed", "closed", "retired"}
    hooked_step = next(item for item in campaign["steps"] if item["id"] == "hooked-write-admission")
    assert hooked_step["state"] == "closed"
    assert hooked_step["closeout"] == {
        "state": "retired",
        "accepted_head": "c17b8939f8d55082d226b3090c03a1c37cd48b37",
        "candidate_head": "d735b62add0a0d5dc7ebdf8cb0e7e1d8deadec30",
        "evidence": ["evidence/chronicle/hooked-write-admission/2026-07-02.md"],
    }


def test_campaign_report_surfaces_terminal_budget_progress_as_advisory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _write_campaign(tmp_path)
    _mock_source_budget(
        monkeypatch,
        campaign_id="compression",
        terminal_target_met=False,
        active_debt={"ids": ["temporary-compiler"]},
    )

    report = campaign_publication_report(tmp_path)

    assert report["required_gaps"] == []
    assert report["advisory_gaps"] == [
        "campaign_publication_campaign_active:compression",
        "campaign_publication_step_not_retired:compression",
        "campaign_publication_terminal_budget_unmet:compression",
        "campaign_publication_active_debt:compression:temporary-compiler",
    ]
    assert report["remote_publication_admission"] == "admitted"
    assert report["terminal_ready"] is False


def test_invalid_campaign_manifest_blocks_repository_publication(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _write_campaign(tmp_path, _CAMPAIGN_MANIFEST.replace("campaign_terminal", "unknown"))
    _mock_source_budget(
        monkeypatch,
        campaign_id="",
        required_gaps=[],
        active_debt={"ids": []},
    )

    publication = campaign_publication_report(tmp_path)

    assert publication["mode"] == "invalid"
    assert publication["remote_publication_admission"] == "blocked"
    assert publication["advisory_gaps"] == []


def test_campaign_publication_requires_the_budget_bound_campaign(
    monkeypatch, tmp_path: Path
) -> None:
    _mock_source_budget(
        monkeypatch,
        campaign_id="declared-compression",
        terminal_target_met=False,
        active_debt={"ids": []},
        required_gaps=[],
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
    _mock_source_budget(
        monkeypatch,
        campaign_id="compression",
        terminal_target_met=False,
        active_debt={"ids": []},
        required_gaps=[],
    )

    filtered = campaign_report(tmp_path, campaign_id="compression")
    publication = campaign_publication_report(tmp_path)

    assert [item["id"] for item in filtered["campaigns"]] == ["compression"]
    assert publication["scope"] == "repository"
    assert publication["remote_publication_admission"] == "admitted"
    assert publication["advisory_gaps"] == [
        "campaign_publication_campaign_active:compression",
        "campaign_publication_step_not_retired:compression",
        "campaign_publication_terminal_budget_unmet:compression",
    ]


def test_evolution_report_exposes_practice_selection_and_fate() -> None:
    report = evolution_report(Path.cwd())

    assert report["ok"] is True
    selection = report["selection"]
    counts = "practice_claim_count\ncandidate_set_count"
    counts += "\nexperiment_protocol_count\nevaluation_record_count"
    assert all(selection[key] >= 1 for key in counts.splitlines())
    claims = selection["practice_claims"]
    assert "workflow-runtime-trustworthy-practice-claim" in {item["id"] for item in claims}
    assert selection["supports_multi_candidate_selection"] is True
    assert selection["supports_practice_lifecycle"] is True
    assert "introduce" in selection["practice_change_kinds"]
    ledger = report["ledger"]
    assert {item["subject"] for item in ledger["practice_claims"]} >= {
        "ethos:workflow-runtime-practice-evolution"
    }
    assert "create_commitment" in {item["commitment_effect"] for item in claims}
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
    expected = "openspec-alone\ncomet-direct\nspec-kit-grammar\ntask-master-graph".splitlines()
    expected += (
        "fspec-scenario-coverage\nmethod-pack-composition\nethos-native-runtime".splitlines()
    )
    assert set(expected) <= candidate_ids


def test_evolution_report_distinguishes_introduction_from_supersession(
    tmp_path: Path,
) -> None:
    _write_refs(tmp_path, "docs/research.md", "docs/decision.md")
    _write_ledger(
        tmp_path,
        hypothesis=[_hypothesis("intro-hypothesis")],
        practice_change=[_practice_change("new-practice")],
    )

    report = evolution_report(tmp_path)

    assert report["ok"] is True
    assert report["selection"]["practice_change_kinds"] == ["introduce"]


def test_evolution_report_requires_practice_claim_links(tmp_path: Path) -> None:
    _write_refs(tmp_path, "docs/research.md", "docs/decision.md")
    _write_ledger(
        tmp_path,
        hypothesis=[_hypothesis("claim-hypothesis")],
        practice_claim=[
            {
                "id": "root-practice",
                "state": "evaluated",
                "owner": "ethos-maintainers",
                "subject": "ethos:sample-practice",
                "question": "Which practice deserves trust?",
                "claim": "A practice is trustworthy only through bounded evidence.",
                "boundary": "The commitment is the root object.",
                "incumbent_relation": "No incumbent exists for this sample boundary.",
                "falsifiers": ["the selected candidate cannot bind evidence"],
                "candidate_set": "missing-candidate-set",
                "experiment_protocol": "missing-experiment",
                "evaluation_record": "missing-evaluation",
                "commitment_effect": "invalid_effect",
                "practice_changes": ["missing-practice-change"],
                "commitment_targets": ["docs/missing-contract.md"],
                "evidence_refs": ["docs/research.md"],
                "decision_refs": ["docs/decision.md"],
            }
        ],
    )

    expected = [
        "practice_claim_commitment_effect_invalid:root-practice:invalid_effect",
        "practice_claim_candidate_set_missing:root-practice:missing-candidate-set",
        "practice_claim_experiment_protocol_missing:root-practice:missing-experiment",
        "practice_claim_evaluation_record_missing:root-practice:missing-evaluation",
        "practice_claim_practice_change_missing:root-practice:missing-practice-change",
        "practice_claim_commitment_ref_missing:root-practice:docs/missing-contract.md",
    ]
    _assert_evolution_gaps(tmp_path, expected)


def test_evolution_report_rejects_introduction_with_incumbents(tmp_path: Path) -> None:
    _write_refs(tmp_path, "docs/research.md", "docs/decision.md")
    _write_ledger(
        tmp_path,
        hypothesis=[_hypothesis("bad-intro-hypothesis")],
        practice_change=[
            _practice_change(
                "bad-introduction",
                boundary="Prior practice exists.",
                incumbents=["old-practice"],
            )
        ],
    )

    _assert_evolution_gaps(tmp_path, ["practice_change_introduce_has_incumbents:bad-introduction"])


def test_evolution_report_rejects_practice_change_commitment_effect_mismatch(
    tmp_path: Path,
) -> None:
    _write_refs(tmp_path, "docs/research.md", "docs/decision.md")
    _write_ledger(
        tmp_path,
        hypothesis=[_hypothesis("effect-hypothesis")],
        practice_change=[
            _practice_change(
                "bad-effect",
                change_kind="supersede",
                boundary="Prior practice exists.",
                incumbents=["old-practice"],
                retirement_conditions=["old practice is migrated"],
            )
        ],
    )

    expected = [
        "practice_change_commitment_effect_mismatch:bad-effect:supersede:"
        "create_commitment:replace_commitment"
    ]
    _assert_evolution_gaps(tmp_path, expected)


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


def test_evolution_candidates_are_derived_from_audit_signals() -> None:
    candidates = evolution_candidates(Path.cwd())

    assert candidates["ok"] is True
    candidate_ids = {item["id"] for item in candidates["candidates"]}
    assert {"release-readiness-ratchet", "asset-quality-kernel"} <= candidate_ids
    assert all(item["challenge"] for item in candidates["candidates"])


def test_evolution_candidates_ignore_non_list_candidate_sets(tmp_path: Path) -> None:
    (tmp_path / "evolution").mkdir()
    (tmp_path / "evolution/ledger.toml").write_text(
        'schema = "system/schemas/kernel/evolution-ledger.schema.json"\n'
        'candidate_set = "not-a-list"\n',
        encoding="utf-8",
    )

    candidates = evolution_candidates(tmp_path)

    assert candidates["ok"] is True
    assert candidates["candidate_set_count"] == 0


def test_evolution_campaign_defensive_coverage_edges(tmp_path: Path) -> None:
    assert evolution.evolution_report(tmp_path)["ledger"]["hypotheses"] == []
    (tmp_path / "evolution").mkdir()
    (tmp_path / "evolution/ledger.toml").write_text("[", encoding="utf-8")
    assert "evolution_ledger_invalid_toml" in evolution.evolution_report(tmp_path)["required_gaps"]

    empty = tmp_path / "empty"
    empty.mkdir()
    assert evolution.campaign_report(empty)["campaigns"] == []

    bad = tmp_path / "evolution/campaigns/bad"
    bad.mkdir(parents=True)
    (bad / "campaign.toml").write_text("[", encoding="utf-8")
    invalid = evolution.campaign_report(tmp_path)
    assert invalid["campaigns"] == []
    assert "campaign_manifest_invalid_toml:bad" in invalid["required_gaps"]

    missing_root = tmp_path / "missing-root"
    (missing_root / "evolution/campaigns").mkdir(parents=True)
    assert (
        "campaign_missing:missing"
        in evolution.campaign_report(missing_root, campaign_id="missing")["required_gaps"]
    )

    carrier_state = getattr(evolution, "_openspec" + "_carrier_state")
    lane_topology = getattr(evolution, "_lane" + "_topology")
    campaign_required_gaps = getattr(evolution, "_campaign" + "_required_gaps")
    assert carrier_state(tmp_path, "") == "missing"

    def step(**values: object) -> dict[str, object]:
        item: dict[str, object] = {
            "id": "step",
            "title": "title",
            "state": "planned",
            "ordinal": 1,
            "depends_on": [],
            "openspec_change": "change",
            "work_lane": "work/x",
            "claim_id": "claim",
            "closeout": {
                "state": "planned",
                "accepted_head": "",
                "candidate_head": "",
                "evidence": [],
            },
        }
        item.update(values)
        return item

    duplicate = [
        step(id="dup", state="active"),
        step(id="dup", state="active", ordinal=2, depends_on=["dup"]),
    ]
    policy = evolution.campaign_policy(tmp_path)
    campaign = {
        "id": "campaign",
        "state": "active",
        "owner": "owner",
        "objective": "objective",
        "claim_id": "claim",
        "steps": duplicate,
        "lane_topology": lane_topology(duplicate, policy=policy),
    }
    gaps = campaign_required_gaps(tmp_path, campaign)
    assert {
        "campaign_step_id_duplicate:campaign",
        "campaign_active_step_not_serial:campaign",
        "campaign_step_dependency_not_retired:campaign:dup:dup",
    } <= set(gaps)


def test_hypothesis_ref_gaps_validate_all_shapes_before_resolving_refs(
    tmp_path: Path,
) -> None:
    hypothesis_ref_gaps = getattr(evolution, "_hypothesis" + "_ref_gaps")
    gaps = hypothesis_ref_gaps(
        tmp_path,
        [
            {
                "id": "ordered",
                "proof_refs": ["docs/missing.md"],
                "review_refs": "docs/review.md",
                "decision_refs": "docs/decision.md",
            }
        ],
    )

    assert gaps == [
        "hypothesis_review_refs_invalid:ordered",
        "hypothesis_decision_refs_invalid:ordered",
        "hypothesis_proof_ref_unresolved:ordered:docs/missing.md",
    ]
