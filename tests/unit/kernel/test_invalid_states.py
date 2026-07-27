"""Terminal invalid-state taxonomy behavior."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import jsonschema

import ethos.state.invalid as invalid_states_module
from ethos.state.invalid import CATEGORY_ORDER
from ethos.state.invalid import UNCLASSIFIED
from ethos.state.invalid import classify
from ethos.state.invalid import classify_all
from ethos.state.invalid import invalid_state_categories
from ethos.state.invalid import invalid_state_projection

ROOT = Path(__file__).resolve().parents[3]


def test_taxonomy_contract_validates_against_schema() -> None:
    payload = tomllib.loads((ROOT / "system/invalid_states.toml").read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "system/schemas/contracts/invalid_states.schema.json").read_text(encoding="utf-8")
    )

    jsonschema.Draft202012Validator(schema).validate(payload)


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

    assert tuple(category.id for category in categories) == CATEGORY_ORDER


def test_taxonomy_has_only_terminal_kernel_concepts() -> None:
    categories = invalid_state_categories()

    assert tuple(category.id for category in categories) == CATEGORY_ORDER
    assert {category.concept for category in categories} == {
        "ChangeContract",
        "RepositoryFacts",
        "PlanIR",
        "Attestation",
        "execution substrate",
    }


def test_unclassified_signals_are_preserved_without_aliasing_retired_ontology() -> None:
    assert classify("new_semantic_residual") == UNCLASSIFIED
    assert classify("claim_overreach") == UNCLASSIFIED
    assert classify("chronicle_missing") == UNCLASSIFIED
    assert classify("rule_attestation_mismatch:head") == UNCLASSIFIED


def test_terminal_categories_classify_current_verifier_boundaries() -> None:
    assert classify("authority_graph_missing") == "change_contract_invalid"
    assert classify("openspec_config_missing") == "change_contract_invalid"
    assert classify("git_snapshot_root_invalid") == "repository_facts_invalid"
    assert classify("protected_root_mutation") == "plan_invalid"
    assert classify("proof_not_proven") == "attestation_invalid"
    assert classify("projection_drift:skills") == "execution_substrate_invalid"


def test_classify_all_preserves_terminal_category_order() -> None:
    grouped = classify_all(
        (
            "authority_graph_missing",
            "git_snapshot_root_invalid",
            "protected_root_mutation",
            "proof_not_proven",
            "projection_drift:skills",
        )
    )

    assert list(grouped) == list(CATEGORY_ORDER)


def test_projection_counts_grouped_gaps() -> None:
    projection = invalid_state_projection(["openspec_config_missing", "proof_not_proven"])

    assert projection == {
        "categories": {
            "change_contract_invalid": ["openspec_config_missing"],
            "attestation_invalid": ["proof_not_proven"],
        },
        "category_count": 2,
        "gap_count": 2,
    }
