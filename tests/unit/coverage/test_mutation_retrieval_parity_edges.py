"""Compact retrieval and parity coverage closure."""

import ast
from pathlib import Path

from ethos.adapters.store.retrieval import common
from ethos.adapters.store.retrieval import indexing
from ethos.adapters.store.retrieval import query
from ethos.adapters.store.retrieval import schema
from ethos.adapters.store.retrieval import sources
from ethos.repository.evidence.parity import core as parity
from ethos.repository.evidence.parity import validation
from ethos.repository.evidence.shadow import payload
from tests.unit.product.parity.snapshots import complete_parity_evidence


def test_retrieval_rejected_inputs(tmp_path):
    eval_report = query.context_eval_report
    assert indexing.python_symbols("def broken(:") == []
    assert indexing.signature_for(ast.parse("class C: pass").body[0]) == "class C"
    assert indexing.kind_for("openspec/specs/x.md", Path("x.md")) == "openspec"
    assert sources.unsafe_source_reason(tmp_path, tmp_path / "missing") == "missing_path"
    assert eval_report(tmp_path, suite="smoke")["required_gaps"] == ["context_index_missing"]
    schema.initialize_context_index(common.default_retrieval_db_path(tmp_path))
    assert eval_report(tmp_path, suite="deep")["required_gaps"] == ["context_eval_suite_missing"]


def test_parity_validation_and_payload_reject_invalid_values(tmp_path):
    evidence_path = tmp_path / "evidence/parity/demo-shadow.json"
    evidence_path.parent.mkdir(parents=True)
    evidence_path.write_text("{", encoding="utf-8")
    report = validation.parity_evidence(tmp_path, "demo")
    assert report["required_gaps"] == ["parity_evidence_invalid_json:JSONDecodeError"]
    evidence = complete_parity_evidence("demo")
    evidence["shadow"] = {**evidence["shadow"], "ok": False, "required_gaps": ["gap"]}
    gaps = validation.validate_parity_evidence(evidence, "demo")
    assert "parity_evidence_invalid:demo:shadow_ok" in gaps
    assert "parity_evidence_invalid:demo:shadow_required_gaps" in gaps
    assert payload.int_value(object()) == 0
    assert payload.identity_evidence_inputs(None) == []
    assert payload.identity_evidence_inputs(
        ["skip", {"path": "p", "kind": "k", "sha256": "s"}, {"path": "", "kind": "k"}]
    ) == [{"path": "p", "kind": "k", "sha256": "s"}]


def test_shadow_report_rejects_mismatched_tracked_target(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    assert (
        parity.shadow_parity_report(target=tmp_path, root=tmp_path, adopter="absent")["state"]
        == "planned"
    )
    evidence = payload.build_tracked_parity_evidence(
        adopter="demo",
        target=other,
        shadow={"ok": True, "required_gaps": [], "identity": {"target_root": str(other)}},
        current_product_head="p1",
        current_target_head="t1",
        timeout_seconds=30,
    )
    parity.write_tracked_parity_evidence(root=tmp_path, adopter="demo", evidence=evidence)
    report = parity.shadow_parity_report(target=tmp_path, root=tmp_path, adopter="demo")
    assert "shadow_parity_evidence_target_mismatch:demo" in report["required_gaps"]
