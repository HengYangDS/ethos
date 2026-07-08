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


def test_shadow_semantic_diff_accepts_external_stricter_command_surface_retired_mentions() -> None:
    external = {
        "ok": False,
        "command": "quality command-surface",
        "state": "blocked",
        "required_gaps": [
            "retired_public_root_mention:docs/current/development/workflow/proof-workflow.md:214:proof",
            "retired_public_command_prefix_mention:docs/current/development/workflow/local-ci-contract.md:66:wt",
        ],
        "data": {
            "retired_public_root_mentions": [
                {"path": "docs/current/development/workflow/proof-workflow.md"},
            ],
        },
    }
    embedded = {
        "ok": True,
        "command": "quality command-surface",
        "state": "clean",
        "required_gaps": [],
        "summary": {"retired_violation_count": 0},
    }

    assert shadow_semantics.semantic_diff(("quality", "command-surface"), external, embedded) == {}
    accepted = shadow_semantics.accepted_semantic_differences(
        ("quality", "command-surface"),
        external,
        embedded,
    )

    assert accepted == [
        {
            "kind": "external_stricter_required_gap",
            "classification": "accepted",
            "scope": "external_stricter_required_gap",
            "commands": ["ethos quality command-surface"],
            "gaps": [
                "retired_public_command_prefix_mention:docs/current/development/workflow/local-ci-contract.md:66:wt",
                "retired_public_root_mention:docs/current/development/workflow/proof-workflow.md:214:proof",
            ],
            "reason": "external product reports a stricter blocking gap allowed by shadow parity",
        }
    ]


def test_shadow_semantic_diff_accepts_external_work_lane_dirty_for_land() -> None:
    external = {
        "ok": False,
        "command": "land",
        "state": "blocked",
        "required_gaps": ["work_lane_dirty", "work_lane_dirty"],
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
            "gaps": ["work_lane_dirty"],
            "reason": "external product reports a stricter blocking gap allowed by shadow parity",
        }
    ]


def test_shadow_semantic_diff_accepts_external_profile_route_gap() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": ["playbook_changed_path_unmatched:.ethos/profile.toml"],
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "state": "routed",
        "required_gaps": [],
    }

    assert (
        shadow_semantics.semantic_diff(("playbooks", "route", "--changed"), external, embedded)
        == {}
    )
    accepted = shadow_semantics.accepted_semantic_differences(
        ("playbooks", "route", "--changed"),
        external,
        embedded,
    )

    assert accepted == [
        {
            "kind": "external_stricter_required_gap",
            "classification": "accepted",
            "scope": "external_stricter_required_gap",
            "commands": ["ethos playbooks route"],
            "gaps": ["playbook_changed_path_unmatched:.ethos/profile.toml"],
            "reason": "external product reports a stricter blocking gap allowed by shadow parity",
        }
    ]


def test_shadow_semantic_diff_accepts_external_stricter_changed_plan() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
        "data": {
            "changed_paths": [
                ".config/interfaces/external-ethos-backend.toml",
                ".ethos/profile.toml",
                "docs/current/development/workflow/external-ethos-adoption.md",
            ],
            "matched_rules": [
                {"id": "ethos-command-plane"},
                {"id": "governance-records"},
            ],
            "required_gates": [
                {"id": "markdown"},
                {"id": "openspec"},
                {"id": "playbooks"},
                {"id": "proof"},
                {"id": "redundancy"},
            ],
        },
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
        "summary": {
            "changed_path_count": 0,
            "matched_rule_count": 0,
            "required_gate_count": 0,
        },
    }

    assert shadow_semantics.semantic_diff(("plan", "--changed"), external, embedded) == {}
    accepted = shadow_semantics.accepted_semantic_differences(
        ("plan", "--changed"),
        external,
        embedded,
    )

    assert accepted == [
        {
            "kind": "external_stricter_plan_scope",
            "classification": "accepted",
            "scope": "external_stricter_plan_scope",
            "commands": ["ethos plan"],
            "gaps": [
                "changed_paths:3",
                "matched_rules:ethos-command-plane,governance-records",
                "required_gates:markdown,openspec,playbooks,proof,redundancy",
            ],
            "reason": "external product plans a stricter changed-scope gate set allowed by shadow parity",
        }
    ]


def test_shadow_semantic_diff_accepts_external_stricter_changed_plan_without_rule_details() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
        "data": {"changed_paths": [".ethos/profile.toml"]},
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
        "summary": {"changed_path_count": 0},
    }

    assert shadow_semantics.accepted_semantic_differences(
        ("plan", "--changed"),
        external,
        embedded,
    ) == [
        {
            "kind": "external_stricter_plan_scope",
            "classification": "accepted",
            "scope": "external_stricter_plan_scope",
            "commands": ["ethos plan"],
            "gaps": ["changed_paths:1"],
            "reason": "external product plans a stricter changed-scope gate set allowed by shadow parity",
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
