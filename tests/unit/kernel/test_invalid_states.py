"""The invalid-state taxonomy is load-bearing, not decorative: every gap ETHOS emits
must reduce to exactly one node-derived category, and the classifier + contract must
stay MECE. A gap that classifies nowhere is itself an ungoverned invalid state."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import jsonschema

import ethos.state.invalid as invalid_states_module
from ethos.state.invalid import NODE_ORDER
from ethos.state.invalid import UNCLASSIFIED
from ethos.state.invalid import classify
from ethos.state.invalid import classify_all
from ethos.state.invalid import invalid_state_categories
from ethos.state.invalid import invalid_state_projection

ROOT = Path(__file__).resolve().parents[3]

# Field/aggregate names carry gaps; composed suffixes and diagnostic reasons are not
# emitted gap strings. Retired category ids are also excluded from the scanner.
_NON_GAP_TOKENS = {
    *(
        "required_gaps required_gap_count enforcement_gaps advisory_gaps observation_gaps "
        "observation_gap_count waived_gaps coordination_gaps validation_gaps "
        "branch_coverage_required blocking_gap_count advisory_missing_count args_missing "
        "args_extra governance_gap_count advisory_gap_count adopter_gap_count adopter_gaps "
        "generic_gap_count hard_quality_gap_count parity_gap_count required_gap_closure "
        "required_gap_kinds can_close_required_gaps baseline_gap baseline_gap_count "
        "baseline_gap_limit unclassified_invalid_state required_gap required_gap_prefix "
        "not_required review_gaps review_gap_count campaign_required_gaps instability_gap "
        "branch_ref_present decision_ref_missing decision_refs_invalid declaration_not_table "
        "evidence_digest_mismatch holder_not_quiesced inventory_git_output_invalid "
        "inventory_object_mismatch inventory_path_invalid linked_worktree_present "
        "native_linux_smoke_required persistent_asset_restore_required process_missing "
        "profile_missing proof_filename_invalid proof_json_invalid proof_record_invalid "
        "proof_refs_invalid recorded_path_present review_ref_missing review_refs_invalid "
        "untrusted_output_schema_invalid missing_required_path_count "
        "missing_required_state_count missing_required_state_paths role_root_mismatch_count "
        "role_root_mismatches physical_target_homes_present projection_drift adapter_bypass "
        "extra_gaps effect_complete_receipt_missing"
    )
    .strip()
    .split(),
    *NODE_ORDER,  # the category ids themselves are not gaps
}

_GAP_RE = re.compile(
    r'"([a-z_]+(?:_gap|_missing|_stale|_mismatch|_invalid|_drift|_unbounded|'
    r"_overreach|_required|_present|_not_[a-z_]+|_bypass|_unarmed|_not_armed|"
    r"_ambiguous)"
    r'[a-z_]*)"'
)


def _emitted_gap_stems() -> set[str]:
    stems: set[str] = set()
    for src in (ROOT / "src/ethos",):
        for path in src.rglob("*.py"):
            for match in _GAP_RE.findall(path.read_text(encoding="utf-8")):
                stem = match.split(":", 1)[0]
                if stem not in _NON_GAP_TOKENS:
                    stems.add(stem)
    return stems


def test_taxonomy_contract_validates_against_schema() -> None:
    payload = tomllib.loads((ROOT / "system/invalid_states.toml").read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "system/schemas/contracts/invalid_states.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(schema).validate(payload)


def test_docs_topology_report_fields_do_not_pollute_taxonomy() -> None:
    payload = tomllib.loads((ROOT / "system/invalid_states.toml").read_text(encoding="utf-8"))
    prefixes = {
        prefix for category in payload["category"] for prefix in category.get("match_prefixes", [])
    }

    assert "missing_required_state_count" in _NON_GAP_TOKENS
    assert "missing_required_state_paths" in _NON_GAP_TOKENS
    assert "missing_required_state" not in prefixes


def test_taxonomy_loads_from_packaged_resource_outside_checkout(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        invalid_states_module,
        "__file__",
        str(tmp_path / "site-packages" / "ethos" / "state" / "invalid.py"),
    )
    invalid_states_module.invalid_state_categories.cache_clear()

    try:
        categories = invalid_states_module.invalid_state_categories()
    finally:
        invalid_states_module.invalid_state_categories.cache_clear()

    assert tuple(category.id for category in categories) == NODE_ORDER


def test_taxonomy_is_mece_over_the_chain() -> None:
    categories = invalid_state_categories()
    # exactly the nine node-derived categories, in chain order.
    assert tuple(c.id for c in categories) == NODE_ORDER
    # every category names a chain node or an explicit boundary.
    for category in categories:
        assert category.node, category.id


def test_every_emitted_gap_classifies_to_exactly_one_node() -> None:
    unclassified = sorted(stem for stem in _emitted_gap_stems() if classify(stem) == UNCLASSIFIED)
    assert unclassified == [], (
        "gap strings that reduce to no kernel node (ungoverned invalid states) — "
        f"add a match_prefix to system/invalid_states.toml: {unclassified}"
    )


def test_classify_all_groups_in_chain_order() -> None:
    grouped = classify_all(
        ("authority_graph_missing", "openspec_config_missing", "evidence_stale:x")
    )
    assert list(grouped) == [
        "authority_gap",
        "carrier_invalid",
        "evidence_missing_or_stale",
    ]


def test_archive_preflight_raw_failure_families_reduce_to_carrier_invalid() -> None:
    assert classify("workspace_missing") == "carrier_invalid"
    assert classify("official_archive_result_invalid") == "carrier_invalid"


def test_longest_prefix_wins_on_overlap() -> None:
    # a specific prefix beats a generic one sharing a stem
    assert classify("write_admission_not_armed:core.hooksPath") == "substrate_untrusted"
    assert classify("push_to_protected_role_not_proven") == "evidence_missing_or_stale"


def test_coordination_advisories_reduce_to_change_unbounded() -> None:
    assert classify("foreign_work_lane_present") == "change_unbounded"
    assert classify("unbound_work_lane_ref_present") == "change_unbounded"
    assert classify("work_lane_missing_lease:work/raw") == "change_unbounded"


def test_head_unbound_evidence_advisories_reduce_to_evidence() -> None:
    assert classify("sample:evidence.head_unbound") == "evidence_missing_or_stale"
    assert classify("evidence.head_unbound") == "evidence_missing_or_stale"


def test_claim_freshness_gaps_reduce_to_evidence() -> None:
    freshness_gaps = (
        "freshness_missing",
        "freshness_mode_invalid",
        "historical_freshness_overbound",
        "head_missing",
        "head_bound_semantic_digest_forbidden",
        "head_stale:old!=new",
        "semantic_sha256_missing",
        "semantic_scope_empty",
        "semantic_scope_unavailable",
        "semantic_scope_stale",
    )

    assert all(
        classify(f"sample:evidence.{gap}") == "evidence_missing_or_stale" for gap in freshness_gaps
    )


def test_coverage_artifact_gaps_reduce_to_evidence() -> None:
    assert classify("coverage_artifact_missing") == "evidence_missing_or_stale"
    assert (
        classify("coverage_artifact_missing:build/evidence/quality/tests/coverage/coverage.xml")
        == "evidence_missing_or_stale"
    )


def test_git_snapshot_transport_gaps_reduce_to_evidence() -> None:
    gaps = (
        "git_snapshot_request_invalid",
        "git_snapshot_root_invalid",
        "git_snapshot_identity_mismatch",
        "git_snapshot_ls_tree_invalid",
        "git_snapshot_path_selection_invalid",
        "git_snapshot_blob_batch_invalid",
    )

    assert all(classify(gap) == "evidence_missing_or_stale" for gap in gaps)


def test_runtime_and_projection_failures_reduce_to_substrate() -> None:
    assert classify("python_entrypoint_invalid:.venv/bin/python") == "substrate_untrusted"
    assert classify("uv_interpreter_probe_stuck") == "substrate_untrusted"
    assert classify("projection_drift:skills") == "substrate_untrusted"
    assert (
        classify("design_integrity_forbidden_projection_path:.ethos/decomp-recipes")
        == "substrate_untrusted"
    )


def test_current_live_gaps_reduce_to_terminal_taxonomy() -> None:
    gaps = (
        "openspec_archive_delta_specs_missing:2026-07-05-ethos-two-package-collapse",
        "openspec_archive_metadata_missing:2026-07-05-ethos-two-package-collapse",
        "parity_pending:work-lane-lifecycle",
        "parity_evidence_invalid:generic:product_head",
        "protected_root_mutation",
        "proof_not_proven",
    )
    grouped = classify_all(gaps)
    assert grouped == {
        "change_unbounded": ["protected_root_mutation"],
        "carrier_invalid": [
            "openspec_archive_delta_specs_missing:2026-07-05-ethos-two-package-collapse",
            "openspec_archive_metadata_missing:2026-07-05-ethos-two-package-collapse",
        ],
        "evidence_missing_or_stale": [
            "parity_pending:work-lane-lifecycle",
            "parity_evidence_invalid:generic:product_head",
            "proof_not_proven",
        ],
    }


def test_projection_counts_grouped_gaps() -> None:
    projection = invalid_state_projection(["openspec_config_missing", "proof_not_proven"])

    assert projection == {
        "categories": {
            "carrier_invalid": ["openspec_config_missing"],
            "evidence_missing_or_stale": ["proof_not_proven"],
        },
        "category_count": 2,
        "gap_count": 2,
    }


def test_whitespace_path_admission_reduces_to_subject_ambiguous() -> None:
    assert classify("prewrite_path_invalid_whitespace") == "subject_ambiguous"
