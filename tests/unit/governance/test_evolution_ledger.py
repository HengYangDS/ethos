# ruff: noqa: E702, I001, UP034 - compact coverage edges preserve unique assertions.
# fmt: off

from __future__ import annotations
from pathlib import Path
import pytest
import ethos.domain.campaign.closeout as campaign_closeout
from ethos.repository.adoption import evolution as evolution_module
from ethos.domain.campaign.closeout import campaign_publication_report
from ethos.repository.adoption.evolution import campaign_report
from ethos.repository.adoption.evolution import evolution_candidates
from ethos.repository.adoption.evolution import evolution_ledger
from ethos.repository.adoption.evolution import evolution_report
from ethos.repository.adoption.practice.selection import selection_ref_gaps

_CAMPAIGN_MANIFEST = Path('tests/fixtures/campaign/minimal.toml').read_text(encoding='utf-8')

def _write_campaign(root: Path, manifest: str = _CAMPAIGN_MANIFEST) -> None:
    (root / 'openspec/changes/compression-foundation').mkdir(parents=True)
    path = root / 'evolution/campaigns/compression/campaign.toml'; path.parent.mkdir(parents=True); path.write_text(manifest, encoding='utf-8')

def _campaign_gaps(root: Path, *, step_state: str, closeout_state: str = 'planned', carrier: str = 'active') -> list[str]:
    terminal = closeout_state in {'closed', 'retired'}
    manifest = _CAMPAIGN_MANIFEST.replace('title = "Foundation"\nstate = "active"', f'title = "Foundation"\nstate = "{step_state}"', 1).replace('state = "planned"', f'state = "{closeout_state}"', 1).replace('accepted_head = ""', f'accepted_head = "{"a" * 40 if terminal else ""}"').replace('candidate_head = ""', f'candidate_head = "{"b" * 40 if terminal else ""}"').replace('evidence = []', 'evidence = ["evidence/chronicle/campaign/2026-07-19.md"]' if terminal else 'evidence = []')
    carrier_path = root / 'openspec/changes/compression-foundation' if carrier == 'active' else root / 'openspec/changes/archive/2026-07-19-compression-foundation'
    carrier_path.mkdir(parents=True)
    path = root / 'evolution/campaigns/compression/campaign.toml'; path.parent.mkdir(parents=True); path.write_text(manifest, encoding='utf-8')
    return campaign_report(root)['required_gaps']

def test_campaign_helpers_fail_closed_for_missing_declarations(monkeypatch, tmp_path: Path) -> None:
    assert evolution_module._openspec_carrier_state(tmp_path, '') == 'missing'
    assert evolution_module._list_items('not-a-list') == []
    monkeypatch.setattr(evolution_module, 'load_workflow_contract_declaration', lambda _root: type('D', (), {'campaign': None})())
    with pytest.raises(ValueError, match='campaign workflow policy missing'):
        evolution_module.campaign_policy(tmp_path)

def test_campaign_public_policy_preserves_candidate_carrier_and_closeout_gaps(tmp_path: Path) -> None:
    assert 'campaign_step_active_openspec_archived:compression:foundation' in _campaign_gaps(tmp_path / 'active-archived', step_state='active', carrier='archived')
    assert 'campaign_step_preland_openspec_not_archived:compression:foundation' in _campaign_gaps(tmp_path / 'preland-active', step_state='archive_ready')
    terminal = _campaign_gaps(tmp_path / 'preland-terminal', step_state='archive_ready', closeout_state='retired', carrier='archived')
    assert 'campaign_step_terminal_closeout_nonterminal:compression:foundation' in terminal
    assert all('archive_ready_closeout_terminal' not in gap for gap in terminal)
    assert 'campaign_step_terminal_openspec_not_archived:compression:foundation' in _campaign_gaps(tmp_path / 'terminal-active', step_state='closed', closeout_state='retired')

def test_evolution_ledger_exposes_active_hypotheses() -> None:
    ledger = evolution_ledger(Path.cwd())
    assert 'ethos-product-maturation' in {item['campaign'] for item in ledger['hypotheses']}
    assert all((item['id'] for item in ledger['hypotheses']))
    assert all((item['owner'] for item in ledger['hypotheses']))
    assert all((item['transition'] for item in ledger['hypotheses']))
    assert all((item['proof_refs'] for item in ledger['hypotheses']))
    assert all((item['review_refs'] for item in ledger['hypotheses']))
    assert all((item['decision_refs'] for item in ledger['hypotheses']))
    assert all((item['retirement_conditions'] for item in ledger['hypotheses']))

def test_evolution_report_scores_hypothesis_states() -> None:
    report = evolution_report(Path.cwd())
    assert report['ok'] is True
    assert report['active_count'] >= 1
    assert report['required_gaps'] == []

def test_evolution_report_requires_structural_entries_to_bind_repository_evidence(tmp_path: Path) -> None:
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[entry]]\nid = "destructive-simplification"\ntype = "experiment"\nstate = "accepted"\nsummary = "Deletes a stale subsystem after proof."\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is False
    assert report['required_gaps'] == ['evolution_hypotheses_missing', 'entry_evidence_refs_missing:destructive-simplification', 'entry_decision_refs_missing:destructive-simplification']

def test_evolution_report_rejects_unresolved_hypothesis_and_entry_refs(tmp_path: Path) -> None:
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[entry]]\nid = "structural-change"\ntype = "experiment"\nstate = "accepted"\nsummary = "A structural change with unresolved refs."\nevidence_refs = ["evidence/chronicle/missing/2026-07-08.md"]\ndecision_refs = ["docs/decisions/accepted/DR-missing.md"]\n\n[[hypothesis]]\nid = "ref-bound-hypothesis"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "Structural evolution must bind real proof."\nchallenge = "Unresolved refs make the evolution ledger a second narrative store."\ntransition = "shape -> canonize"\nproof_refs = ["ethos quality missing-proof --json"]\nreview_refs = ["tests/unit/governance/test_missing.py"]\ndecision_refs = ["docs/decisions/accepted/DR-missing.md"]\nretirement_conditions = ["all refs resolve"]\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is False
    assert report['required_gaps'] == ['hypothesis_proof_ref_unresolved:ref-bound-hypothesis:ethos quality missing-proof --json', 'hypothesis_review_ref_missing:ref-bound-hypothesis:tests/unit/governance/test_missing.py', 'hypothesis_decision_ref_missing:ref-bound-hypothesis:docs/decisions/accepted/DR-missing.md', 'entry_evidence_ref_missing:structural-change:evidence/chronicle/missing/2026-07-08.md', 'entry_decision_ref_missing:structural-change:docs/decisions/accepted/DR-missing.md']

def test_evolution_report_accepts_existing_path_refs_and_known_ethos_commands(tmp_path: Path) -> None:
    (tmp_path / 'docs' / 'decisions').mkdir(parents=True)
    (tmp_path / 'docs' / 'decisions' / 'accepted.md').write_text('# Accepted\n', encoding='utf-8')
    (tmp_path / 'evidence' / 'chronicle' / 'lane').mkdir(parents=True)
    (tmp_path / 'evidence' / 'chronicle' / 'lane' / '2026-07-08.md').write_text('# Chronicle\n', encoding='utf-8')
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests' / 'proof.py').write_text('def test_ok():\n    assert True\n', encoding='utf-8')
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[entry]]\nid = "structural-change"\ntype = "experiment"\nstate = "accepted"\nsummary = "A structural change with resolved refs."\nevidence_refs = ["evidence/chronicle/lane/2026-07-08.md"]\ndecision_refs = ["docs/decisions/accepted.md"]\n\n[[hypothesis]]\nid = "ref-bound-hypothesis"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "Structural evolution must bind real proof."\nchallenge = "Resolved refs keep the evolution ledger bound."\ntransition = "shape -> canonize"\nproof_refs = ["ethos status --json", "tests/proof.py"]\nreview_refs = ["tests/proof.py"]\ndecision_refs = ["docs/decisions/accepted.md"]\nretirement_conditions = ["all refs resolve"]\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is True
    assert report['required_gaps'] == []

def test_evolution_report_rejects_path_like_and_plain_unknown_proof_refs(tmp_path: Path) -> None:
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'decision.md').write_text('# Decision\n', encoding='utf-8')
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[hypothesis]]\nid = "bad-proof-refs"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "Proof refs must resolve."\nchallenge = "Unresolved refs make evolution unreviewable."\ntransition = "shape -> canonize"\nproof_refs = ["/workspace/proof.md", "https://example.test/proof.json", "pytest"]\nreview_refs = ["docs/decision.md"]\ndecision_refs = ["docs/decision.md"]\nretirement_conditions = ["all refs resolve"]\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is False
    assert report['required_gaps'] == ['hypothesis_proof_ref_unresolved:bad-proof-refs:/workspace/proof.md', 'hypothesis_proof_ref_unresolved:bad-proof-refs:https://example.test/proof.json', 'hypothesis_proof_ref_unresolved:bad-proof-refs:pytest']

def test_evolution_report_treats_non_list_entry_refs_as_unresolved(tmp_path: Path) -> None:
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[hypothesis]]\nid = "valid-hypothesis"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "Evolution needs one active hypothesis."\nchallenge = "Without one, entries cannot be judged."\ntransition = "shape -> canonize"\nproof_refs = ["ethos status --json"]\nreview_refs = ["docs/decision.md"]\ndecision_refs = ["docs/decision.md"]\nretirement_conditions = ["all refs resolve"]\n\n[[entry]]\nid = "bad-entry-ref-shape"\ntype = "experiment"\nstate = "accepted"\nsummary = "A structural change with scalar refs."\nevidence_refs = "evidence/chronicle/lane/2026-07-08.md"\ndecision_refs = "docs/decisions/accepted.md"\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is False
    assert report['required_gaps'] == ['hypothesis_review_ref_missing:valid-hypothesis:docs/decision.md', 'hypothesis_decision_ref_missing:valid-hypothesis:docs/decision.md', 'entry_evidence_refs_invalid:bad-entry-ref-shape', 'entry_decision_refs_invalid:bad-entry-ref-shape']

def test_evolution_report_rejects_non_list_hypothesis_refs(tmp_path: Path) -> None:
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[hypothesis]]\nid = "bad-hypothesis-ref-shape"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "Hypothesis refs must be arrays."\nchallenge = "Scalar refs hide review and proof boundaries."\ntransition = "shape -> canonize"\nproof_refs = "ethos status --json"\nreview_refs = "docs/decision.md"\ndecision_refs = "docs/decision.md"\nretirement_conditions = ["all refs resolve"]\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is False
    assert report['required_gaps'] == ['hypothesis_proof_refs_invalid:bad-hypothesis-ref-shape', 'hypothesis_review_refs_invalid:bad-hypothesis-ref-shape', 'hypothesis_decision_refs_invalid:bad-hypothesis-ref-shape']

def test_evolution_candidates_are_derived_from_audit_signals() -> None:
    candidates = evolution_candidates(Path.cwd())
    assert candidates['ok'] is True
    candidate_ids = {item['id'] for item in candidates['candidates']}
    assert {'release-readiness-ratchet', 'asset-quality-kernel'} <= candidate_ids
    assert all((item['challenge'] for item in candidates['candidates']))

def test_campaign_report_exposes_manifest_steps_and_closeout_progress() -> None:
    report = campaign_report(Path.cwd(), campaign_id='terminal-openspec-productization')
    assert report['ok'] is True
    assert report['active_count'] >= 1
    campaign = report['campaigns'][0]
    assert campaign['id'] == 'terminal-openspec-productization'
    assert campaign['objective']
    assert campaign['state'] == 'active'
    assert campaign['step_summary']['total'] >= 8
    assert campaign['step_summary']['planned'] >= 5
    assert campaign['step_summary']['active'] == 0
    assert campaign['step_summary']['closed'] >= 4
    assert campaign['lane_topology']['kind'] == 'openspec_lane_sequence'
    assert campaign['lane_topology']['mode'] == 'strict_serial'
    assert campaign['lane_topology']['active_step'] == ''
    assert campaign['lane_topology']['active_steps'] == []
    assert campaign['lane_topology']['next_planned_step'] == 'adopter-openspec-scaffold'
    assert campaign['lane_topology']['edges'][0] == {'from': 'campaign-orchestration', 'to': 'openspec-product-protocol', 'rule': 'closeout_retired_before_activation'}
    first_step = campaign['steps'][0]
    assert first_step['ordinal'] == 1
    assert first_step['depends_on'] == []
    assert first_step['openspec_change']
    assert first_step['work_lane'].startswith('work/')
    assert first_step['claim_id']
    assert first_step['closeout']['state'] in {'planned', 'landed', 'closed', 'retired'}
    hooked_step = next((item for item in campaign['steps'] if item['id'] == 'hooked-write-admission'))
    assert hooked_step['state'] == 'closed'
    assert hooked_step['closeout'] == {'state': 'retired', 'accepted_head': 'c17b8939f8d55082d226b3090c03a1c37cd48b37', 'candidate_head': 'd735b62add0a0d5dc7ebdf8cb0e7e1d8deadec30', 'evidence': ['evidence/chronicle/hooked-write-admission/2026-07-02.md']}

def test_campaign_report_surfaces_terminal_budget_progress_as_advisory(monkeypatch, tmp_path: Path) -> None:
    _write_campaign(tmp_path)
    monkeypatch.setattr(campaign_closeout, 'source_budget_report', lambda _root: {'campaign_id': 'compression', 'terminal_target_met': False, 'active_debt': {'ids': ['temporary-compiler']}})
    report = campaign_publication_report(tmp_path)
    assert report['required_gaps'] == []
    assert report['advisory_gaps'] == ['campaign_publication_campaign_active:compression', 'campaign_publication_step_not_retired:compression', 'campaign_publication_terminal_budget_unmet:compression', 'campaign_publication_active_debt:compression:temporary-compiler']
    assert report['remote_publication_admission'] == 'admitted'
    assert report['terminal_ready'] is False

def test_invalid_campaign_manifest_blocks_repository_publication(monkeypatch, tmp_path: Path) -> None:
    _write_campaign(tmp_path, _CAMPAIGN_MANIFEST.replace('campaign_terminal', 'unknown'))
    monkeypatch.setattr(campaign_closeout, 'source_budget_report', lambda _root: {'campaign_id': '', 'required_gaps': [], 'active_debt': {'ids': []}})
    publication = campaign_publication_report(tmp_path)
    assert publication['mode'] == 'invalid'
    assert publication['remote_publication_admission'] == 'blocked'
    assert publication['advisory_gaps'] == []

def test_campaign_publication_requires_the_budget_bound_campaign(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(campaign_closeout, 'source_budget_report', lambda _root: {'campaign_id': 'declared-compression', 'terminal_target_met': False, 'active_debt': {'ids': []}, 'required_gaps': []})
    report = campaign_publication_report(tmp_path, campaigns={'campaigns': [], 'required_gaps': [], 'ok': True})
    assert report['remote_publication_admission'] == 'blocked'
    assert report['required_gaps'] == ['campaign_publication_bound_campaign_missing:declared-compression']

def test_campaign_publication_payload_is_declared_in_workflow_policy() -> None:
    source = Path('system/workflows.toml').read_text(encoding='utf-8')
    assert "publication_projection = '''" in source
    assert 'def publication(' not in Path('packages/ethos-core/src/ethos_core/contracts/workflow.py').read_text(encoding='utf-8')

def test_filtered_campaign_status_keeps_repository_publication_scope(monkeypatch, tmp_path: Path) -> None:
    _write_campaign(tmp_path)
    monkeypatch.setattr(campaign_closeout, 'source_budget_report', lambda _root: {'campaign_id': 'compression', 'terminal_target_met': False, 'active_debt': {'ids': []}, 'required_gaps': []})
    filtered = campaign_report(tmp_path, campaign_id='compression')
    publication = campaign_publication_report(tmp_path)
    assert [item['id'] for item in filtered['campaigns']] == ['compression']
    assert publication['scope'] == 'repository'
    assert publication['remote_publication_admission'] == 'admitted'
    assert publication['advisory_gaps'] == ['campaign_publication_campaign_active:compression', 'campaign_publication_step_not_retired:compression', 'campaign_publication_terminal_budget_unmet:compression']

def test_evolution_report_exposes_practice_selection_and_fate() -> None:
    report = evolution_report(Path.cwd())
    assert report['ok'] is True
    selection = report['selection']
    assert selection['practice_claim_count'] >= 1
    assert {item['id'] for item in selection['practice_claims']} >= {'workflow-runtime-trustworthy-practice-claim'}
    assert selection['candidate_set_count'] >= 1
    assert selection['experiment_protocol_count'] >= 1
    assert selection['evaluation_record_count'] >= 1
    assert selection['supports_multi_candidate_selection'] is True
    assert selection['supports_practice_lifecycle'] is True
    assert 'introduce' in selection['practice_change_kinds']
    ledger = report['ledger']
    assert {item['subject'] for item in ledger['practice_claims']} >= {'ethos:workflow-runtime-practice-evolution'}
    assert {item['commitment_effect'] for item in selection['practice_claims']} >= {'create_commitment'}
    selected = {item['selected_candidate'] for item in ledger['evaluation_records'] if item.get('state') == 'selected'}
    assert 'ethos-native-runtime' in selected
    candidate_ids = {candidate['id'] for candidate_set in ledger['candidate_sets'] for candidate in candidate_set['candidates']}
    assert {'openspec-alone', 'comet-direct', 'spec-kit-grammar', 'task-master-graph', 'fspec-scenario-coverage', 'method-pack-composition', 'ethos-native-runtime'} <= candidate_ids

def test_evolution_report_distinguishes_introduction_from_supersession(tmp_path: Path) -> None:
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'research.md').write_text('# Research\n', encoding='utf-8')
    (tmp_path / 'docs' / 'decision.md').write_text('# Decision\n', encoding='utf-8')
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[hypothesis]]\nid = "intro-hypothesis"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "A new practice may be introduced without an incumbent."\nchallenge = "Calling every introduction supersession hides the boundary model."\ntransition = "shape -> canonize"\nproof_refs = ["ethos status --json"]\nreview_refs = ["docs/research.md"]\ndecision_refs = ["docs/decision.md"]\nretirement_conditions = ["practice fate is explicit"]\n\n[[practice_change]]\nid = "new-practice"\nstate = "active"\nchange_kind = "introduce"\ncommitment_effect = "create_commitment"\npractice = "new bounded practice"\ncarrier_kind = "workflow"\nsummary = "Introduces a new practice without replacing an incumbent."\nboundary = "No prior practice owns this boundary."\nevidence_refs = ["docs/research.md"]\ndecision_refs = ["docs/decision.md"]\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is True
    assert report['selection']['practice_change_kinds'] == ['introduce']

def test_evolution_report_requires_practice_claim_links(tmp_path: Path) -> None:
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'research.md').write_text('# Research\n', encoding='utf-8')
    (tmp_path / 'docs' / 'decision.md').write_text('# Decision\n', encoding='utf-8')
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[hypothesis]]\nid = "claim-hypothesis"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "A practice claim must bind its proof path."\nchallenge = "Unlinked mechanism records are not repository truth."\ntransition = "shape -> canonize"\nproof_refs = ["ethos status --json"]\nreview_refs = ["docs/research.md"]\ndecision_refs = ["docs/decision.md"]\nretirement_conditions = ["practice claim links resolve"]\n\n[[practice_claim]]\nid = "root-practice"\nstate = "evaluated"\nowner = "ethos-maintainers"\nsubject = "ethos:sample-practice"\nquestion = "Which practice deserves trust?"\nclaim = "A practice is trustworthy only through bounded evidence."\nboundary = "The commitment is the root object; mechanism records are subordinate."\nincumbent_relation = "No incumbent exists for this sample boundary."\nfalsifiers = ["the selected candidate cannot bind evidence"]\ncandidate_set = "missing-candidate-set"\nexperiment_protocol = "missing-experiment"\nevaluation_record = "missing-evaluation"\ncommitment_effect = "invalid_effect"\npractice_changes = ["missing-practice-change"]\ncommitment_targets = ["docs/missing-contract.md"]\nevidence_refs = ["docs/research.md"]\ndecision_refs = ["docs/decision.md"]\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is False
    assert report['required_gaps'] == ['practice_claim_commitment_effect_invalid:root-practice:invalid_effect', 'practice_claim_candidate_set_missing:root-practice:missing-candidate-set', 'practice_claim_experiment_protocol_missing:root-practice:missing-experiment', 'practice_claim_evaluation_record_missing:root-practice:missing-evaluation', 'practice_claim_practice_change_missing:root-practice:missing-practice-change', 'practice_claim_commitment_ref_missing:root-practice:docs/missing-contract.md']

def test_evolution_report_rejects_introduction_with_incumbents(tmp_path: Path) -> None:
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'research.md').write_text('# Research\n', encoding='utf-8')
    (tmp_path / 'docs' / 'decision.md').write_text('# Decision\n', encoding='utf-8')
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[hypothesis]]\nid = "bad-intro-hypothesis"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "Introductions must not pretend to replace incumbents."\nchallenge = "Incumbents imply refine, supersede, or retire analysis."\ntransition = "shape -> canonize"\nproof_refs = ["ethos status --json"]\nreview_refs = ["docs/research.md"]\ndecision_refs = ["docs/decision.md"]\nretirement_conditions = ["practice fate is explicit"]\n\n[[practice_change]]\nid = "bad-introduction"\nstate = "active"\nchange_kind = "introduce"\ncommitment_effect = "create_commitment"\npractice = "new bounded practice"\ncarrier_kind = "workflow"\nsummary = "Claims introduction while naming an incumbent."\nboundary = "Prior practice exists."\nincumbents = ["old-practice"]\nevidence_refs = ["docs/research.md"]\ndecision_refs = ["docs/decision.md"]\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is False
    assert report['required_gaps'] == ['practice_change_introduce_has_incumbents:bad-introduction']

def test_evolution_report_rejects_practice_change_commitment_effect_mismatch(tmp_path: Path) -> None:
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'research.md').write_text('# Research\n', encoding='utf-8')
    (tmp_path / 'docs' / 'decision.md').write_text('# Decision\n', encoding='utf-8')
    ledger = tmp_path / 'evolution' / 'ledger.toml'
    ledger.parent.mkdir(parents=True)
    ledger.write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\n\n[[hypothesis]]\nid = "effect-hypothesis"\ncampaign = "sample-campaign"\nstate = "active"\nowner = "ethos-maintainers"\nclaim = "Practice fate must match commitment effect."\nchallenge = "Supersession that creates instead of replaces hides commitment semantics."\ntransition = "shape -> canonize"\nproof_refs = ["ethos status --json"]\nreview_refs = ["docs/research.md"]\ndecision_refs = ["docs/decision.md"]\nretirement_conditions = ["practice fate is explicit"]\n\n[[practice_change]]\nid = "bad-effect"\nstate = "active"\nchange_kind = "supersede"\ncommitment_effect = "create_commitment"\npractice = "new bounded practice"\ncarrier_kind = "workflow"\nsummary = "Claims supersession while creating instead of replacing."\nboundary = "Prior practice exists."\nincumbents = ["old-practice"]\nretirement_conditions = ["old practice is migrated"]\nevidence_refs = ["docs/research.md"]\ndecision_refs = ["docs/decision.md"]\n'.strip(), encoding='utf-8')
    report = evolution_report(tmp_path)
    assert report['ok'] is False
    assert report['required_gaps'] == ['practice_change_commitment_effect_mismatch:bad-effect:supersede:create_commitment:replace_commitment']

def test_selection_ref_gaps_cover_missing_practice_claim_and_candidate_set_fields(tmp_path: Path) -> None:
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs' / 'research.md').write_text('# Research\n', encoding='utf-8')
    gaps = selection_ref_gaps(tmp_path, {'practice_claims': [{'id': 'fieldless-claim', 'commitment_targets': [], 'evidence_refs': 'docs/research.md', 'decision_refs': ['docs/missing-decision.md']}], 'candidate_sets': [{'id': 'thin-candidates', 'selection_policy': 'manual', 'decision_refs': 'docs/research.md', 'candidates': [{'id': 'candidate-a', 'hypothesis_ref': 'missing-hypothesis', 'evidence_refs': ['docs/missing-evidence.md']}]}], 'hypotheses': [], 'experiment_protocols': [], 'evaluation_records': [], 'practice_changes': []})
    assert {'practice_claim_owner_missing:fieldless-claim', 'practice_claim_commitment_effect_missing:fieldless-claim', 'practice_claim_practice_changes_missing:fieldless-claim', 'practice_claim_commitment_refs_missing:fieldless-claim', 'practice_claim_evidence_refs_invalid:fieldless-claim', 'practice_claim_decision_ref_missing:fieldless-claim:docs/missing-decision.md', 'candidate_set_too_small:thin-candidates', 'candidate_set_selection_policy_invalid:thin-candidates', 'candidate_set_decision_refs_invalid:thin-candidates', 'candidate_hypothesis_ref_missing:thin-candidates:candidate-a:missing-hypothesis', 'candidate_evidence_ref_missing:thin-candidates:candidate-a:docs/missing-evidence.md'} <= set(gaps)

def test_selection_ref_gaps_cover_experiment_evaluation_and_practice_change_edges(tmp_path: Path) -> None:
    gaps = selection_ref_gaps(tmp_path, {'hypotheses': [{'id': 'known-hypothesis'}], 'candidate_sets': [{'id': 'known-candidates', 'candidates': [{}, {}]}], 'experiment_protocols': [{'id': 'bad-experiment', 'candidate_set': 'missing-candidates', 'hypothesis_refs': ['missing-hypothesis'], 'evidence_refs': []}], 'evaluation_records': [{'id': 'bad-evaluation', 'candidate_set': 'missing-candidates', 'experiment_protocol': 'missing-experiment', 'selected_candidate': 'same', 'rejected_candidates': ['same'], 'evidence_refs': [], 'decision_refs': []}, {'id': 'unselected-evaluation', 'candidate_set': 'known-candidates', 'experiment_protocol': 'bad-experiment', 'metric_results': [], 'evidence_refs': [], 'decision_refs': []}], 'practice_changes': [{'id': 'bad-retirement', 'change_kind': 'retire', 'commitment_effect': 'unknown_effect', 'evidence_refs': [], 'decision_refs': []}, {'id': 'missing-effect', 'change_kind': 'refine', 'practice': 'practice', 'carrier_kind': 'workflow', 'summary': 'summary', 'boundary': 'boundary', 'evidence_refs': [], 'decision_refs': []}, {'id': 'unknown-effect', 'change_kind': 'unknown', 'commitment_effect': 'unknown_effect', 'practice': 'practice', 'carrier_kind': 'workflow', 'summary': 'summary', 'boundary': 'boundary', 'evidence_refs': [], 'decision_refs': []}], 'practice_claims': []})
    assert {'experiment_candidate_set_missing:bad-experiment:missing-candidates', 'experiment_hypothesis_ref_missing:bad-experiment:missing-hypothesis', 'experiment_variables_missing:bad-experiment', 'experiment_evidence_refs_missing:bad-experiment', 'evaluation_candidate_set_missing:bad-evaluation:missing-candidates', 'evaluation_experiment_protocol_missing:bad-evaluation:missing-experiment', 'evaluation_selected_candidate_missing:unselected-evaluation', 'evaluation_rejected_candidates_missing:unselected-evaluation', 'evaluation_selected_candidate_also_rejected:bad-evaluation:same', 'evaluation_metric_results_missing:bad-evaluation', 'evaluation_evidence_refs_missing:bad-evaluation', 'practice_change_practice_missing:bad-retirement', 'practice_change_commitment_effect_mismatch:bad-retirement:retire:unknown_effect:remove_commitment', 'practice_change_incumbents_missing:bad-retirement', 'practice_change_retirement_conditions_missing:bad-retirement', 'practice_change_evidence_refs_missing:bad-retirement', 'practice_change_commitment_effect_missing:missing-effect', 'practice_change_commitment_effect_invalid:unknown-effect:unknown_effect'} <= set(gaps)

def test_selection_ref_gaps_reject_absolute_and_url_path_refs(tmp_path: Path) -> None:
    gaps = selection_ref_gaps(tmp_path, {'hypotheses': [], 'practice_claims': [{'id': 'external-refs', 'owner': 'owner', 'subject': 'subject', 'question': 'question', 'claim': 'claim', 'boundary': 'boundary', 'incumbent_relation': 'none', 'falsifiers': ['falsifier'], 'commitment_effect': 'create_commitment', 'practice_changes': ['known-change'], 'commitment_targets': ['/workspace/contract.md'], 'evidence_refs': ['https://example.test/evidence.md'], 'decision_refs': ['']}], 'practice_changes': [{'id': 'known-change'}], 'candidate_sets': [], 'experiment_protocols': [], 'evaluation_records': []})
    assert {'practice_claim_commitment_ref_missing:external-refs:/workspace/contract.md', 'practice_claim_evidence_ref_missing:external-refs:https://example.test/evidence.md', 'practice_claim_decision_ref_missing:external-refs:'} <= set(gaps)

def test_evolution_candidates_ignore_non_list_candidate_sets(tmp_path: Path) -> None:
    (tmp_path / 'evolution').mkdir()
    (tmp_path / 'evolution' / 'ledger.toml').write_text('\nschema = "system/schemas/kernel/evolution-ledger.schema.json"\ncandidate_set = "not-a-list"\n'.strip(), encoding='utf-8')
    candidates = evolution_candidates(tmp_path)
    assert candidates['ok'] is True
    assert candidates['candidate_set_count'] == 0


def test_evolution_campaign_defensive_coverage_edges(tmp_path: Path) -> None:
    assert evolution_module.evolution_report(tmp_path)["ledger"]["hypotheses"] == []
    (tmp_path / "evolution").mkdir(); (tmp_path / "evolution/ledger.toml").write_text("[", encoding="utf-8")
    assert "evolution_ledger_invalid_toml" in evolution_module.evolution_report(tmp_path)["required_gaps"]
    empty = tmp_path / "empty"; empty.mkdir(); assert evolution_module.campaign_report(empty)["campaigns"] == []
    bad = tmp_path / "evolution/campaigns/bad"; bad.mkdir(parents=True); (bad / "campaign.toml").write_text("[", encoding="utf-8")
    invalid = evolution_module.campaign_report(tmp_path); assert invalid["campaigns"] == []; assert "campaign_manifest_invalid_toml:bad" in invalid["required_gaps"]
    missing_root = tmp_path / "missing-root"; (missing_root / "evolution/campaigns").mkdir(parents=True)
    assert "campaign_missing:missing" in evolution_module.campaign_report(missing_root, campaign_id="missing")["required_gaps"]
    assert evolution_module._openspec_carrier_state(tmp_path, "") == "missing"
    def step(**values):
        item = {"id": "step", "title": "title", "state": "planned", "ordinal": 1, "depends_on": [], "openspec_change": "change", "work_lane": "work/x", "claim_id": "claim", "closeout": {"state": "planned", "accepted_head": "", "candidate_head": "", "evidence": []}}; item.update(values); return item
    duplicate = [step(id="dup", state="active"), step(id="dup", state="active", ordinal=2, depends_on=["dup"])]
    policy = evolution_module.campaign_policy(tmp_path)
    campaign = {"id": "campaign", "state": "active", "owner": "owner", "objective": "objective", "claim_id": "claim", "steps": duplicate, "lane_topology": evolution_module._lane_topology(duplicate, policy=policy)}
    campaign_gaps = evolution_module._campaign_required_gaps(tmp_path, campaign)
    assert {"campaign_step_id_duplicate:campaign", "campaign_active_step_not_serial:campaign", "campaign_step_dependency_not_retired:campaign:dup:dup"} <= set(campaign_gaps)


def test_hypothesis_ref_gaps_validate_all_shapes_before_resolving_refs(tmp_path: Path) -> None:
    gaps = evolution_module._hypothesis_ref_gaps(tmp_path, [{"id": "ordered", "proof_refs": ["docs/missing.md"], "review_refs": "docs/review.md", "decision_refs": "docs/decision.md"}])
    assert gaps == ["hypothesis_review_refs_invalid:ordered", "hypothesis_decision_refs_invalid:ordered", "hypothesis_proof_ref_unresolved:ordered:docs/missing.md"]
