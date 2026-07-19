from __future__ import annotations

from pathlib import Path

import pytest

from ethos_core.contracts.admission import AdmissionDecision
from ethos_core.contracts.admission import DecisionBasis
from ethos_core.contracts.admission import HookAdmissionRequest
from ethos_core.contracts.admission import MutationSubject


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
        verdict="allow",
        subject=subject,
        policy_refs=("commitment:work-lane-owner",),
        evidence_refs=("evidence:lease-observation",),
        basis=basis,
        why=("request_matches_current_holder_and_generation",),
        next=(),
        required_gaps=(),
    )

    payload = decision.to_payload()
    assert payload["verdict"] == "allow"
    assert payload["subject"]["expected_state"]["epoch"] == 2
    assert payload["decision_basis"]["enforcement_boundary"] == "local_process_guard"
    assert payload["mints_authority"] is False
    assert payload["reusable_authorization"] is False
    assert payload["recheck_required"] is True


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

    assert (
        request.model_dump_json()
        == '{"root":"/repo","layer":"pre-tool","paths":["README.md"],"editor_root":"/repo","require_editor_root":false,"command":"","expected_root":"/repo"}'
    )


def test_hook_admission_request_rejects_non_path_bound_context() -> None:
    with pytest.raises(ValueError, match="filesystem path"):
        HookAdmissionRequest(root=object(), layer="pre-tool")
