from __future__ import annotations

from ethos_core.contracts.admission import AdmissionDecision
from ethos_core.contracts.admission import DecisionBasis
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
