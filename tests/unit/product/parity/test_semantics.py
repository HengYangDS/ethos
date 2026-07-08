from __future__ import annotations

import ethos.adapters.shadow.semantics as shadow_semantics


def test_shadow_semantic_diff_accepts_external_required_gap_superset() -> None:
    external = {
        "ok": False,
        "command": "status",
        "state": "blocked",
        "required_gaps": ["embedded_gap", "external_stricter_gap"],
    }
    embedded = {
        "ok": False,
        "command": "status",
        "state": "blocked",
        "required_gaps": ["embedded_gap"],
    }

    assert shadow_semantics.semantic_diff(("status",), external, embedded) == {}
    accepted = shadow_semantics.accepted_semantic_differences(("status",), external, embedded)

    assert accepted == [
        {
            "kind": "external_required_gap_superset",
            "classification": "accepted",
            "scope": "external_required_gap_superset",
            "commands": ["ethos status"],
            "gaps": ["external_stricter_gap"],
            "reason": "external product reports the embedded blocking gaps plus stricter required gaps",
        }
    ]


def test_shadow_semantic_diff_accepts_external_stricter_land_gap() -> None:
    external = {
        "ok": False,
        "command": "land",
        "state": "blocked",
        "required_gaps": ["candidate_base_stale"],
    }
    embedded = {
        "ok": True,
        "command": "land",
        "state": "ready_to_land",
        "required_gaps": [],
    }

    assert shadow_semantics.semantic_diff(("land",), external, embedded) == {}
    accepted = shadow_semantics.accepted_semantic_differences(("land",), external, embedded)

    assert accepted == [
        {
            "kind": "external_stricter_required_gap",
            "classification": "accepted",
            "scope": "external_stricter_required_gap",
            "commands": ["ethos land"],
            "gaps": ["candidate_base_stale"],
            "reason": "external product reports a stricter blocking gap allowed by shadow parity",
        }
    ]


def test_shadow_semantic_diff_accepts_external_protected_root_mutation_for_land_publish() -> None:
    for command, ready_state in (
        (("land",), "ready_to_land"),
        (("publish",), "ready_to_publish"),
    ):
        external = {
            "ok": False,
            "command": command[0],
            "state": "blocked",
            "required_gaps": ["protected_root_mutation"],
        }
        embedded = {
            "ok": True,
            "command": command[0],
            "state": ready_state,
            "required_gaps": [],
        }

        assert shadow_semantics.semantic_diff(command, external, embedded) == {}
        accepted = shadow_semantics.accepted_semantic_differences(command, external, embedded)

        assert accepted == [
            {
                "kind": "external_stricter_required_gap",
                "classification": "accepted",
                "scope": "external_stricter_required_gap",
                "commands": [f"ethos {command[0]}"],
                "gaps": ["protected_root_mutation"],
                "reason": "external product reports a stricter blocking gap allowed by shadow parity",
            }
        ]


def test_shadow_semantic_diff_rejects_external_false_negative() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
    }
    embedded = {
        "ok": False,
        "command": "status",
        "state": "blocked",
        "required_gaps": ["embedded_gap"],
    }

    diff = shadow_semantics.semantic_diff(("status",), external, embedded)

    assert diff["required_gaps"] == {"external": [], "embedded": ["embedded_gap"]}
    assert shadow_semantics.false_negative_gaps(("status",), external, embedded) == ["embedded_gap"]
