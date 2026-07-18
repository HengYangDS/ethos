from __future__ import annotations

import pytest

import ethos.adapters.shadow.semantics as shadow_semantics
from tests.unit.product.parity.snapshots import accepted_difference
from tests.unit.product.parity.snapshots import parity_payload


@pytest.mark.parametrize(
    ("command", "external", "embedded", "expected"),
    [
        pytest.param(
            ("status",),
            parity_payload(
                "status", ok=False, state="blocked", gaps=("embedded_gap", "external_stricter_gap")
            ),
            parity_payload("status", ok=False, state="blocked", gaps=("embedded_gap",)),
            accepted_difference(
                "external_required_gap_superset", "status", ("external_stricter_gap",)
            ),
            id="required-gap-superset",
        ),
        pytest.param(
            ("land",),
            parity_payload("land", ok=False, state="blocked", gaps=("candidate_base_stale",)),
            parity_payload("land", ok=True, state="ready_to_land"),
            accepted_difference(
                "external_stricter_required_gap", "land", ("candidate_base_stale",)
            ),
            id="candidate-base-stale",
        ),
        pytest.param(
            ("land",),
            parity_payload("land", ok=False, state="blocked", gaps=("protected_root_mutation",)),
            parity_payload("land", ok=True, state="ready_to_land"),
            accepted_difference(
                "external_stricter_required_gap", "land", ("protected_root_mutation",)
            ),
            id="protected-root-land",
        ),
        pytest.param(
            ("publish",),
            parity_payload("publish", ok=False, state="blocked", gaps=("protected_root_mutation",)),
            parity_payload("publish", ok=True, state="local_publish_ready"),
            accepted_difference(
                "external_stricter_required_gap", "publish", ("protected_root_mutation",)
            ),
            id="protected-root-publish",
        ),
        pytest.param(
            ("quality", "command-surface"),
            parity_payload(
                "quality command-surface",
                ok=False,
                state="blocked",
                gaps=(
                    "retired_public_root_mention:docs/current/development/workflow/proof-workflow.md:214:proof",
                    "retired_public_command_prefix_mention:docs/current/development/workflow/local-ci-contract.md:66:wt",
                ),
                data={
                    "retired_public_root_mentions": [
                        {"path": "docs/current/development/workflow/proof-workflow.md"},
                    ],
                },
            ),
            parity_payload(
                "quality command-surface",
                ok=True,
                state="clean",
                summary={"retired_violation_count": 0},
            ),
            accepted_difference(
                "external_stricter_required_gap",
                "quality command-surface",
                (
                    "retired_public_command_prefix_mention:docs/current/development/workflow/local-ci-contract.md:66:wt",
                    "retired_public_root_mention:docs/current/development/workflow/proof-workflow.md:214:proof",
                ),
            ),
            id="retired-command-surface-mentions",
        ),
        pytest.param(
            ("land",),
            parity_payload(
                "land", ok=False, state="blocked", gaps=("work_lane_dirty", "work_lane_dirty")
            ),
            parity_payload("land", ok=True, state="ready_to_land"),
            accepted_difference("external_stricter_required_gap", "land", ("work_lane_dirty",)),
            id="work-lane-dirty",
        ),
        pytest.param(
            ("playbooks", "route", "--changed"),
            parity_payload(
                "playbooks route",
                ok=False,
                state="gapped",
                gaps=("playbook_changed_path_unmatched:.ethos/profile.toml",),
            ),
            parity_payload("playbooks route", ok=True, state="routed"),
            accepted_difference(
                "external_stricter_required_gap",
                "playbooks route",
                ("playbook_changed_path_unmatched:.ethos/profile.toml",),
            ),
            id="profile-route-gap",
        ),
        pytest.param(
            ("plan", "--changed"),
            parity_payload(
                "plan",
                ok=True,
                state="planned",
                data={
                    "changed_paths": [
                        ".config/interfaces/external-ethos-backend.toml",
                        ".ethos/profile.toml",
                        "docs/current/development/workflow/external-ethos-adoption.md",
                    ],
                    "matched_rules": [{"id": "ethos-command-plane"}, {"id": "governance-records"}],
                    "required_gates": [
                        {"id": "markdown"},
                        {"id": "openspec"},
                        {"id": "playbooks"},
                        {"id": "proof"},
                        {"id": "redundancy"},
                    ],
                },
            ),
            parity_payload(
                "plan",
                ok=True,
                state="planned",
                summary={
                    "changed_path_count": 0,
                    "matched_rule_count": 0,
                    "required_gate_count": 0,
                },
            ),
            accepted_difference(
                "external_stricter_plan_scope",
                "plan",
                (
                    "changed_paths:3",
                    "matched_rules:ethos-command-plane,governance-records",
                    "required_gates:markdown,openspec,playbooks,proof,redundancy",
                ),
            ),
            id="detailed-changed-plan",
        ),
        pytest.param(
            ("plan", "--changed"),
            parity_payload(
                "plan", ok=True, state="planned", data={"changed_paths": [".ethos/profile.toml"]}
            ),
            parity_payload("plan", ok=True, state="planned", summary={"changed_path_count": 0}),
            accepted_difference("external_stricter_plan_scope", "plan", ("changed_paths:1",)),
            id="minimal-changed-plan",
        ),
    ],
)
def test_shadow_semantic_diff_accepts_declared_external_differences(
    command: tuple[str, ...],
    external: dict[str, object],
    embedded: dict[str, object],
    expected: list[dict[str, object]],
) -> None:
    assert shadow_semantics.semantic_diff(command, external, embedded) == {}
    assert shadow_semantics.accepted_semantic_differences(command, external, embedded) == expected


def test_shadow_semantic_diff_rejects_external_false_negative() -> None:
    external = parity_payload("status", ok=True, state="ready")
    embedded = parity_payload("status", ok=False, state="blocked", gaps=("embedded_gap",))

    diff = shadow_semantics.semantic_diff(("status",), external, embedded)

    assert diff["required_gaps"] == {"external": [], "embedded": ["embedded_gap"]}
    assert shadow_semantics.false_negative_gaps(("status",), external, embedded) == ["embedded_gap"]
