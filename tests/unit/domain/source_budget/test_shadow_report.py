from __future__ import annotations

import json
from typing import Any
from typing import cast

from ethos.domain.source_budget.core import SourceBudgetShadowObservation
from ethos.domain.source_budget.core import source_budget_shadow_report


def _v1() -> dict[str, object]:
    return {"ok": True, "state": "clean", "required_gaps": [], "metrics": {"global_total": 1}}


def _observation() -> dict[str, object]:
    return {
        "observer": {
            "profile_id": "v1-live-at-task4-start",
            "commit_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "taxonomy_path": ".config/checks/format/selection.toml",
            "taxonomy_blob": "c" * 40,
            "taxonomy_content_sha256": "d" * 64,
            "taxonomy_semantic_sha256": "e" * 64,
        },
        "subject": {
            "commit_sha": "f" * 40,
            "tree_sha": "1" * 40,
            "snapshot_digest": "2" * 64,
        },
        "v1": {
            "declaration_commit": "3" * 40,
            "declared_total": 105342,
            "replay_total": 104389,
            "drift": -953,
            "metrics": {"global_total": 104389},
            "category_deltas": {"jinja": -671},
            "inventory": {
                "file_count": 888,
                "digest": "4" * 64,
                "category_counts": {"python_product": 877, "yaml": 11},
            },
        },
        "v2": None,
        "disagreements": ["taxonomy_profile_drift:jinja"],
        "required_gaps": ["source_budget_taxonomy_profile_unresolved"],
        "comparison_state": "unresolved",
    }


def _v2() -> dict[str, object]:
    return {
        "manifest_digest": "5" * 64,
        "inventory_digest": "6" * 64,
        "contract_set_digest": "7" * 64,
        "provider_coverage": {"python-source-v2": 1},
        "coordinates": [
            {
                "scope_id": "test.python",
                "metric_id": "lexical_tokens",
                "unit": "lexical_token",
                "value": 1,
            }
        ],
        "vector_digest": "8" * 64,
        "snapshot_digest": "9" * 64,
    }


def _assert_canonical_invalid(observation: dict[str, object]) -> None:
    assert source_budget_shadow_report(_v1(), observation)["v2_shadow"] == {
        "mode": "v1_authoritative_v2_shadow",
        "authoritative": "v1",
        "observer": None,
        "subject": None,
        "v1": None,
        "v2": None,
        "disagreements": [],
        "required_gaps": ["source_budget_v2_shadow_observation_invalid"],
        "comparison_state": "blocked",
    }


def test_shadow_preserves_v1_authority_and_projects_supplied_observation() -> None:
    v1 = _v1()
    observation = _observation()

    report = source_budget_shadow_report(v1, observation)

    assert {key: report[key] for key in v1} == v1
    shadow = report["v2_shadow"]
    assert shadow["mode"] == "v1_authoritative_v2_shadow"
    assert shadow["authoritative"] == "v1"
    assert shadow["observer"] == observation["observer"]
    assert shadow["comparison_state"] == "unresolved"
    assert shadow["required_gaps"] == ["source_budget_taxonomy_profile_unresolved"]


def test_shadow_accepts_json_round_trip_regardless_of_key_order() -> None:
    observation = json.loads(json.dumps(_observation(), sort_keys=True))

    shadow = source_budget_shadow_report(_v1(), observation)["v2_shadow"]

    assert shadow["comparison_state"] == "unresolved"
    assert shadow["required_gaps"] == ["source_budget_taxonomy_profile_unresolved"]


def test_shadow_rejects_malformed_nested_shapes_and_incoherent_states() -> None:
    for field in ("observer", "subject", "v1"):
        observation = _observation()
        observation[field] = {}
        shadow = source_budget_shadow_report(_v1(), observation)["v2_shadow"]
        assert shadow["comparison_state"] == "blocked"
        assert "source_budget_v2_shadow_observation_invalid" in shadow["required_gaps"]

    reviewed = _observation()
    reviewed["comparison_state"] = "reviewed_observation"
    shadow = source_budget_shadow_report(_v1(), reviewed)["v2_shadow"]
    assert shadow["comparison_state"] == "blocked"
    assert "source_budget_v2_shadow_observation_invalid" in shadow["required_gaps"]

    unresolved = _observation()
    unresolved["required_gaps"] = []
    unresolved["disagreements"] = []
    shadow = source_budget_shadow_report(_v1(), unresolved)["v2_shadow"]
    assert shadow["comparison_state"] == "blocked"
    assert "source_budget_v2_shadow_observation_invalid" in shadow["required_gaps"]


def test_shadow_fails_closed_when_observation_is_missing_or_claims_clean_disagreement() -> None:
    missing = source_budget_shadow_report(_v1(), None)["v2_shadow"]
    assert missing["comparison_state"] == "blocked"
    assert missing["required_gaps"] == ["source_budget_v2_shadow_observation_missing"]

    forged = source_budget_shadow_report(
        _v1(),
        {
            "observer": {},
            "subject": {},
            "v1": {},
            "v2": None,
            "disagreements": ["still-different"],
            "required_gaps": [],
            "comparison_state": "clean",
        },
    )["v2_shadow"]
    assert forged["comparison_state"] == "blocked"
    assert "source_budget_v2_shadow_observation_invalid" in forged["required_gaps"]


def test_shadow_rejects_mixed_gaps_forged_identities_and_invalid_v2_values() -> None:
    typed = _observation()
    typed["v2"] = _v2()
    assert source_budget_shadow_report(_v1(), typed)["v2_shadow"]["v2"] == _v2()

    variants: list[dict[str, object]] = []
    for field, value in (
        ("required_gaps", ["source_budget_taxonomy_profile_unresolved", None]),
        ("required_gaps", ["invalid gap token"]),
    ):
        candidate = json.loads(json.dumps(_observation()))
        candidate[field] = value
        variants.append(candidate)
    for parent, field, value in (
        ("observer", "commit_sha", None),
        ("observer", "taxonomy_path", "taxonomy\x00.toml"),
        ("subject", "snapshot_digest", "short"),
        ("v1", "replay_total", True),
        ("v1", "metrics", {"global_total": "104389"}),
    ):
        candidate = json.loads(json.dumps(_observation()))
        candidate[parent][field] = value
        variants.append(candidate)
    for field, value in (
        (
            "coordinates",
            [{"scope_id": "x", "metric_id": "m", "unit": "lexical_token", "value": "1"}],
        ),
        ("vector_digest", None),
        ("provider_coverage", {"python-source-v2": True}),
    ):
        candidate = json.loads(json.dumps(_observation()))
        candidate["v2"] = _v2()
        candidate["v2"][field] = value
        variants.append(candidate)
    partial_v2 = json.loads(json.dumps(_observation()))
    partial_v2["v2"] = _v2()
    partial_v2["v2"]["coordinates"] = None
    partial_v2["v2"]["vector_digest"] = None
    partial_v2["v2"]["snapshot_digest"] = None
    variants.append(partial_v2)

    for candidate in variants:
        _assert_canonical_invalid(candidate)


def test_shadow_rejects_inventory_count_mismatch() -> None:
    observation = _observation()
    observation["v1"]["inventory"]["category_counts"] = {"python_product": 1}

    _assert_canonical_invalid(observation)


def test_shadow_rejects_non_mapping_duplicate_tokens_totals_and_coordinates() -> None:
    assert (
        source_budget_shadow_report(_v1(), cast("Any", []))["v2_shadow"]["comparison_state"]
        == "blocked"
    )

    duplicate_tokens = _observation()
    duplicate_tokens["required_gaps"] = [
        "source_budget_taxonomy_profile_unresolved",
        "source_budget_taxonomy_profile_unresolved",
    ]
    _assert_canonical_invalid(duplicate_tokens)

    invalid_totals = _observation()
    invalid_totals["v1"]["drift"] = 0
    _assert_canonical_invalid(invalid_totals)

    duplicate_coordinates = _observation()
    duplicate_coordinates["v2"] = _v2()
    duplicate_coordinates["v2"]["coordinates"] *= 2
    _assert_canonical_invalid(duplicate_coordinates)


def test_task4_shadow_observation_is_a_public_reusable_contract() -> None:
    typed = SourceBudgetShadowObservation.model_validate(_observation())

    assert typed.comparison_state == "unresolved"
    assert typed.model_dump(mode="json") == _observation()
