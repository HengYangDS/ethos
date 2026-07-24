from __future__ import annotations

import json

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
            "inventory": {"file_count": 888, "digest": "4" * 64},
        },
        "v2": None,
        "disagreements": ["taxonomy_profile_drift:jinja"],
        "required_gaps": ["source_budget_taxonomy_profile_unresolved"],
        "comparison_state": "unresolved",
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
