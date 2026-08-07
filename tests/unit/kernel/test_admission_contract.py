from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.admission import DecisionBasis
from ethos.contracts.admission import HookAdmissionRequest
from ethos.contracts.admission import MutationSubject
from ethos.contracts.admission import ethos_command_mutates


def test_admission_decision_is_exact_request_bound_and_non_reusable() -> None:
    subject = MutationSubject(
        action="lane.prewrite",
        resource="work/example:packages/example.py",
        expected_state={
            "head": "a" * 40,
            "lease_id": "lease:01",
            "epoch": 2,
        },
    )
    basis = DecisionBasis(
        enforcement_boundary="local_process_guard",
        identity_basis="holder_ref_equality",
        state_bindings=("root", "path", "head", "lease_id", "epoch"),
        evidence_boundary="current_local_observation",
        verifier_provenance="incumbent_runner",
        time_basis="local_observation_time",
    )
    decision = AdmissionDecision(
        verdict="pass",
        subject=subject,
        policy_refs=("commitment:work-lane-owner",),
        evidence_refs=("evidence:lease-observation",),
        basis=basis,
        why=("request_matches_current_holder_and_generation",),
        next_action="",
        required_gaps=(),
    )

    payload = decision.to_payload()
    assert payload["verdict"] == "pass"
    assert payload["subject"]["expected_state"]["epoch"] == 2
    assert payload["decision_basis"]["enforcement_boundary"] == "local_process_guard"
    assert payload["next_action"] == ""
    assert "next" not in payload
    assert payload["mints_authority"] is False
    assert payload["reusable_authorization"] is False
    assert payload["recheck_required"] is True


@pytest.mark.parametrize(
    "command",
    [
        ("ethos", "lane", "start", "feature", "--apply"),
        ("ethos", "land", "--authorize=true"),
        ("openspec", "archive", "example", "--yes", "--json"),
    ],
)
def test_mutation_classifier_recognizes_owned_and_external_effects(
    command: tuple[str, ...],
) -> None:
    assert ethos_command_mutates(command)


def test_admission_models_reject_pass_with_required_gaps() -> None:
    subject = MutationSubject(action="lane.prewrite", resource="work/example")
    basis = DecisionBasis(
        enforcement_boundary="local_process_guard",
        identity_basis="holder_ref_equality",
        evidence_boundary="current_local_observation",
        verifier_provenance="current_runner",
        time_basis="evaluation_time",
    )

    with pytest.raises(ValidationError, match="pass_with_required_gaps"):
        AdmissionDecision(
            verdict="pass",
            subject=subject,
            basis=basis,
            required_gaps=("unknown_required_fact",),
        )


def test_action_preview_is_explicitly_non_authoritative() -> None:
    preview = AdmissionDecision.action_preview(
        action="observe",
        resource="work/foreign",
        blocked_actions=("write", "land", "retire"),
        why=("foreign_lane_requires_handoff",),
    )

    assert preview == {
        "candidate_actions": ["observe"],
        "blocked_actions": ["write", "land", "retire"],
        "why": ["foreign_lane_requires_handoff"],
        "mints_authority": False,
        "recheck_required": True,
    }
    with pytest.raises(ValueError, match="action preview requires"):
        AdmissionDecision.action_preview(action="", resource="x", blocked_actions=(), why=())


def test_hook_admission_request_normalizes_pathlike_inputs() -> None:
    request = HookAdmissionRequest(
        root=Path("/repo"),
        layer="pre-tool",
        paths=(Path("README.md"),),
        editor_root=Path("/repo"),
        expected_root=Path("/repo"),
    )

    expected = (
        '{"root":"/repo","layer":"pre-tool","paths":["README.md"],'
        '"editor_root":"/repo","require_editor_root":false,"command":"",'
        '"expected_root":"/repo"}'
    )
    assert request.model_dump_json() == expected


def test_hook_admission_request_rejects_non_path_bound_context() -> None:
    with pytest.raises(ValueError, match="filesystem path"):
        HookAdmissionRequest(root=object(), layer="pre-tool")


def test_admission_boundary_rejects_type_coercion_and_nested_mutation() -> None:
    with pytest.raises(ValidationError):
        HookAdmissionRequest(root="/repo", layer=1)
    with pytest.raises((TypeError, ValidationError)):
        MutationSubject(
            action="lane.prewrite",
            resource="work/example",
            expected_state={"epoch": object()},
        )

    subject = MutationSubject(
        action="lane.prewrite",
        resource="work/example",
        expected_state={"nested": {"epoch": 1}},
    )
    with pytest.raises(TypeError):
        subject.expected_state["new"] = True
    with pytest.raises(TypeError):
        subject.expected_state["nested"]["epoch"] = 2
