from __future__ import annotations

import pytest

import ethos.adapters.shadow.execution as shadow_execution
import ethos.adapters.shadow.semantics as shadow_semantics
from ethos.adapters.shadow.semantics import accepted_semantic_differences
from ethos.adapters.shadow.semantics import semantic_diff
from ethos.repository.policy.schema import validate_schema_instance


def test_shadow_semantic_diff_compares_plan_gate_dimension() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "summary": {"required_gate_count": 1},
        "data": {"required_gates": [{"id": "unit"}]},
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "summary": {"required_gate_count": 0},
        "data": {"required_gates": []},
    }

    diff = shadow_semantics.semantic_diff(("plan", "--changed"), external, embedded)

    assert diff == {"required_gate_ids": {"external": ["unit"], "embedded": []}}


def test_shadow_plan_projection_deduplicates_required_gate_ids() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
        "data": {
            "required_gates": [
                {"id": "proof"},
                {"id": "proof"},
                {"id": "markdown"},
            ]
        },
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
        "data": {"required_gates": [{"id": "markdown"}, {"id": "proof"}]},
    }

    assert semantic_diff(("plan", "--changed"), external, embedded) == {}


def test_shadow_status_projection_accepts_embedded_top_level_fields() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "data": {"role": "accepted_root", "dirty": False, "changed_paths": []},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "required_gaps": [],
        "role": "accepted_root",
        "dirty": False,
        "changed_paths": [],
    }

    assert shadow_semantics.semantic_diff(("status",), external, embedded) == {}


@pytest.mark.parametrize(
    ("external_role", "embedded_role"),
    [
        ("candidate", "integration_candidate"),
        ("work_lane", "isolated_lane"),
    ],
)
def test_shadow_status_projection_normalizes_legacy_role_aliases(
    external_role: str,
    embedded_role: str,
) -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "summary": {"role": external_role, "dirty": False},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "required_gaps": [],
        "summary": {"role": embedded_role, "dirty": False},
    }

    assert shadow_semantics.semantic_diff(("status",), external, embedded) == {}


def test_shadow_report_projection_normalizes_missing_blocking_gap_count() -> None:
    external = {"ok": True, "command": "report", "state": "ready", "required_gaps": []}
    embedded = {
        "ok": True,
        "command": "report",
        "summary": {"blocking_gap_count": 0},
        "required_gaps": [],
        "scorecards": [{"id": "governance", "ok": True, "required_gaps": []}],
    }

    assert shadow_semantics.semantic_diff(("report",), external, embedded) == {}


def test_shadow_playbooks_projection_ignores_schema_specific_route_details() -> None:
    external = {
        "ok": True,
        "command": "playbooks route",
        "state": "routed",
        "required_gaps": [],
        "data": {"selected": [{"id": "repo-local-skill"}]},
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "required_gaps": [],
        "route_hints": [],
    }

    assert (
        shadow_semantics.semantic_diff(("playbooks", "route", "--changed"), external, embedded)
        == {}
    )


def test_shadow_parse_failure_is_process_failure() -> None:
    result = {
        "exit_code": 0,
        "stdout": "not json",
        "stderr": "",
        "json": {},
    }

    assert shadow_execution.process_failed(result) is True


def test_shadow_timeout_is_process_failure() -> None:
    result = {
        "exit_code": 124,
        "stdout": "",
        "stderr": "timeout",
        "json": {},
    }

    assert shadow_execution.process_failed(result) is True


def test_shadow_semantic_diff_derives_state_for_minimal_status_payload() -> None:
    external = {
        "ok": True,
        "command": "status",
        "state": "ready",
        "required_gaps": [],
        "data": {"role": "accepted_root"},
    }
    embedded = {
        "ok": True,
        "command": "status",
        "summary": {"dirty": False},
        "required_gaps": [],
        "role": "accepted_root",
    }

    assert semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_derives_state_for_legacy_plan_payload() -> None:
    external = {
        "ok": True,
        "command": "plan",
        "state": "planned",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "plan",
        "summary": {"changed_path_count": 0},
        "required_gaps": [],
    }

    assert semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_derives_state_for_legacy_assistants_doctor_payload() -> None:
    external = {
        "ok": True,
        "command": "assistants doctor",
        "state": "ready",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "assistants doctor",
        "summary": {"surface_count": 4},
        "required_gaps": [],
    }

    assert semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_normalizes_ready_prove_against_minimal_payload() -> None:
    external = {
        "ok": True,
        "command": "prove",
        "state": "ready",
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "prove",
        "state": {},
        "required_gaps": [],
    }

    assert semantic_diff(("prove",), external, embedded) == {}


@pytest.mark.parametrize(
    ("command", "external_state"),
    [
        ("prove", "gapped"),
        ("report", "gapped"),
        ("land", "dry_run"),
        ("publish", "dry_run"),
    ],
)
def test_shadow_semantic_diff_classifies_external_repository_audit_gaps_for_minimal_payload(
    command: str,
    external_state: str,
) -> None:
    external = {
        "ok": False,
        "command": command,
        "state": external_state,
        "required_gaps": [
            "docs/architecture/product-ontology.md",
            "claims_missing",
        ],
        "data": {
            "repository_audit": {
                "required_gaps": [
                    "docs/architecture/product-ontology.md",
                    "claims_missing",
                ],
            },
        },
    }
    embedded = {
        "ok": True,
        "command": command,
        "summary": {"command": command, "role": "accepted_root"},
        "required_gaps": [],
    }

    assert semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_preserves_external_non_repository_audit_gaps() -> None:
    external = {
        "ok": False,
        "command": "prove",
        "state": "gapped",
        "required_gaps": [
            "docs/architecture/product-ontology.md",
            "action_graph_invalid",
        ],
        "data": {
            "repository_audit": {
                "required_gaps": ["docs/architecture/product-ontology.md"],
            },
        },
    }
    embedded = {
        "ok": True,
        "command": "prove",
        "summary": {"command": "prove"},
        "required_gaps": [],
    }

    diff = semantic_diff(external, embedded)

    assert diff["ok"] == {"external": False, "embedded": True}
    assert diff["required_gaps"] == {"external": ["action_graph_invalid"], "embedded": []}


def test_shadow_semantic_diff_classifies_changed_route_noop() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": [
            "skill_missing_id",
            "skill_missing_id",
            "playbook_route_missing:changed-scope",
        ],
        "data": {
            "subject": "changed-scope",
            "required_gaps": [
                "skill_missing_id",
                "skill_missing_id",
                "playbook_route_missing:changed-scope",
            ],
        },
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 0,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    assert semantic_diff(external, embedded) == {}


def test_shadow_semantic_diff_classifies_changed_route_noop_with_strict_activation_gap() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": [
            "skill_missing_id",
            "playbook_activation_unsupported_version:1",
        ],
        "data": {
            "subject": "changed-scope",
            "required_gaps": [
                "skill_missing_id",
                "playbook_activation_unsupported_version:1",
            ],
        },
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 0,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    assert semantic_diff(external, embedded) == {}
    assert accepted_semantic_differences(external, embedded) == [
        {
            "kind": "changed_route_noop",
            "classification": "accepted",
            "scope": "changed_scope_route",
            "commands": ["ethos playbooks route"],
            "gaps": [
                "playbook_activation_unsupported_version:1",
                "skill_missing_id",
            ],
            "reason": "changed-scope route has no changed paths to route",
        }
    ]


def test_shadow_semantic_diff_classifies_report_parity_evidence_refresh_bootstrap() -> None:
    external = {
        "ok": False,
        "command": "report",
        "state": "gapped",
        "summary": {
            "score": 6,
            "max_score": 7,
            "governance_gap_count": 0,
            "parity_pending_count": 6,
        },
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "report",
        "state": "ready",
        "summary": {"blocking_gap_count": 0},
        "required_gaps": [],
    }

    assert semantic_diff(external, embedded) == {}
    accepted = accepted_semantic_differences(external, embedded)
    assert accepted == [
        {
            "kind": "report_parity_evidence_refresh_bootstrap",
            "classification": "accepted",
            "scope": "parity_evidence_refresh",
            "commands": ["ethos report"],
            "gaps": ["parity_pending_count:6"],
            "reason": "report parity freshness is being refreshed by the current shadow run",
        }
    ]

    payload = {
        "ok": True,
        "state": "matched",
        "target": "/repo",
        "identity": {
            "target_root": "/repo",
            "target_head": "a" * 40,
            "product_head": "b" * 40,
            "changed_paths": [],
            "commands": ["ethos report --json"],
            "external_commands": ["python -m ethos.cli report --root /repo --json"],
            "embedded_commands": ["pixi run ethos report --json"],
            "evidence_inputs": [
                {"path": ".ethos/profile.toml", "kind": "file", "sha256": "c" * 64}
            ],
        },
        "required_gaps": [],
        "accepted_summary": {
            "total_count": 1,
            "command_count": 1,
            "kind_counts": {"report_parity_evidence_refresh_bootstrap": 1},
        },
        "false_negative_count": 0,
        "comparisons": [
            {
                "command": "ethos report",
                "external": {"exit_code": 0, "stdout": "", "stderr": "", "json": external},
                "embedded": {"exit_code": 0, "stdout": "", "stderr": "", "json": embedded},
                "semantic_diff": {},
                "false_negative_gaps": [],
                "accepted_summary": {
                    "total_count": 1,
                    "kind_counts": {"report_parity_evidence_refresh_bootstrap": 1},
                },
                "accepted_differences": accepted,
            }
        ],
        "execution_packages": [],
    }

    validation = validate_schema_instance("shadow-parity.schema.json", payload)
    assert validation["ok"] is True


def test_shadow_semantic_diff_preserves_changed_route_gap_when_paths_changed() -> None:
    external = {
        "ok": False,
        "command": "playbooks route",
        "state": "gapped",
        "required_gaps": ["playbook_route_missing:changed-scope"],
        "data": {"subject": "changed-scope"},
    }
    embedded = {
        "ok": True,
        "command": "playbooks route",
        "summary": {
            "changed_requested": True,
            "changed_path_count": 1,
            "command": "playbooks route",
        },
        "required_gaps": [],
    }

    diff = semantic_diff(external, embedded)

    assert diff["required_gaps"] == {
        "external": ["playbook_route_missing:changed-scope"],
        "embedded": [],
    }


def test_shadow_projection_marks_accepted_ready_states() -> None:
    cases = [
        ("prove", "proof_ready", "proven"),
        ("assistants doctor", "assistant_ready", "ready"),
        ("playbooks route", "route_ready", "routed"),
        ("land", "readiness", "ready_to_land"),
        ("publish", "readiness", "local_publish_ready"),
    ]
    for command_name, ready_key, ready_state in cases:
        external = {
            "ok": False,
            "command": command_name,
            "state": "gapped",
            "summary": {"governance_gap_count": 0, "parity_pending_count": 1},
            "required_gaps": [],
        }
        embedded = {"ok": True, "command": "report", "state": "ready", "required_gaps": []}
        projection, _embedded, _accepted = shadow_semantics._normalized_semantic_projections(
            tuple(command_name.split()), external, embedded
        )
        shadow_semantics._mark_projection_ready(projection)
        assert projection[ready_key] is True
        assert shadow_semantics._ready_state_for_command(command_name) == ready_state


def test_shadow_report_refresh_bootstrap_rejects_non_matching_shapes() -> None:
    base_external = {
        "ok": False,
        "command": "report",
        "state": "gapped",
        "summary": {"governance_gap_count": 0, "parity_pending_count": 1},
        "required_gaps": [],
    }
    base_embedded = {"ok": True, "command": "report", "state": "ready", "required_gaps": []}
    cases = [
        ({"summary": {"governance_gap_count": 1, "parity_pending_count": 1}}, {}),
        ({"summary": {"governance_gap_count": 0, "parity_pending_count": 0}}, {}),
        ({"command": "status"}, {}),
        ({}, {"command": "status"}),
        ({"required_gaps": ["gap"]}, {}),
        ({"ok": True}, {}),
        ({"state": "ready"}, {}),
        ({}, {"state": "gapped"}),
    ]
    for external_patch, embedded_patch in cases:
        external = {**base_external, **external_patch}
        embedded = {**base_embedded, **embedded_patch}
        projection, embedded_projection, _accepted = (
            shadow_semantics._normalized_semantic_projections(("report",), external, embedded)
        )
        assert (
            shadow_semantics._report_parity_evidence_refresh_bootstrap_gaps(
                external, embedded, projection, embedded_projection
            )
            == []
        )
