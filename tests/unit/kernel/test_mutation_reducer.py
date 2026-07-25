from __future__ import annotations

import pytest

from ethos.contracts.lifecycle.core import CLOSEOUT_MUTATION
from ethos.contracts.lifecycle.core import WORK_LANE_MUTATION
from ethos.contracts.lifecycle.core import LeaseFacts
from ethos.contracts.lifecycle.core import MutationFacts
from ethos.contracts.lifecycle.core import MutationRequest
from ethos.contracts.lifecycle.core import reduce_guards
from ethos.contracts.lifecycle.core import reduce_lease_request
from ethos.contracts.lifecycle.core import reduce_mutation
from ethos.contracts.workflow import load_workflow_contract_declaration

LEASE_TRANSITIONS = {
    item.id: item for item in load_workflow_contract_declaration().lease_transition
}


def test_work_lane_reducer_short_circuits_non_land_dry_runs() -> None:
    result = reduce_mutation(
        MutationRequest(command="publish", apply=False, authorized=False, expect_head="stale"),
        current_head="current",
        facts=MutationFacts(),
        transition=WORK_LANE_MUTATION,
    )

    assert result.ok is True
    assert result.state == "dry_run"
    assert result.gaps == ()


def test_work_lane_land_dry_run_checks_the_protected_role() -> None:
    result = reduce_mutation(
        MutationRequest(command="land", apply=False, authorized=False, expect_head=None),
        current_head="current",
        facts=MutationFacts(role="accepted_root"),
        transition=WORK_LANE_MUTATION,
    )

    assert result.gaps == ("protected_root_mutation",)


def test_work_lane_reducer_orders_request_lifecycle_and_evidence_gaps() -> None:
    result = reduce_mutation(
        MutationRequest(command="land", apply=True, authorized=False, expect_head=None),
        current_head="current",
        facts=MutationFacts(
            role="accepted_root",
            always_gaps=("candidate_branch_missing",),
            evidence_gaps=("proof_not_proven",),
        ),
        transition=WORK_LANE_MUTATION,
    )

    assert result == result.__class__(
        ok=False,
        state="blocked",
        gaps=(
            "authorization_required",
            "expect_head_required",
            "protected_root_mutation",
            "candidate_branch_missing",
            "proof_not_proven",
        ),
    )


def test_closeout_reducer_distinguishes_current_from_ready_and_blocked() -> None:
    request = MutationRequest(command="closeout", apply=False, authorized=False, expect_head="head")

    assert (
        reduce_mutation(
            request,
            current_head="head",
            facts=MutationFacts(role="accepted_root", current=True),
            transition=CLOSEOUT_MUTATION,
        ).state
        == "current"
    )
    assert (
        reduce_mutation(
            request,
            current_head="head",
            facts=MutationFacts(role="accepted_root"),
            transition=CLOSEOUT_MUTATION,
        ).state
        == "dry_run"
    )
    assert reduce_mutation(
        request,
        current_head="other",
        facts=MutationFacts(role="accepted_root"),
        transition=CLOSEOUT_MUTATION,
    ).gaps == ("expect_head_mismatch",)


@pytest.mark.parametrize(
    ("operation", "changes", "state", "gaps"),
    [
        pytest.param("renew", {}, "planned", (), id="renew/planned"),
        pytest.param("renew", {"apply": True}, "renewed", (), id="renew/applied"),
        pytest.param(
            "resume",
            {"contrary_decision": True},
            "blocked",
            ("lease_resume_blocked_by_decision",),
            id="resume/contrary-decision",
        ),
        pytest.param(
            "renew",
            {"expect_head": "stale"},
            "blocked",
            ("expect_head_mismatch",),
            id="renew/stale-head",
        ),
        pytest.param(
            "handoff_accept",
            {
                "role": "accepted_root",
                "current_branch": "work/other",
                "expect_head": "",
                "lease_id": "",
                "expected_epoch": None,
                "ttl_seconds": 0,
                "target_holder_ref": "",
                "offer_id": "",
                "expected_expires_at": "",
                "expected_payload_sha256": "",
                "holder_quiesced": False,
            },
            "blocked",
            (
                "work_lane_required",
                "lane_branch_mismatch",
                "expect_head_required",
                "lease_id_required",
                "lease_epoch_required",
                "lease_ttl_invalid",
                "target_holder_ref_invalid",
                "handoff_offer_id_required",
                "lease_expires_at_required",
                "lease_payload_sha256_required",
                "holder_quiescence_confirmation_required",
            ),
            id="handoff-accept/all-required-facts-missing",
        ),
    ],
)
def test_lease_transition_matrix(
    operation: str,
    changes: dict[str, object],
    state: str,
    gaps: tuple[str, ...],
) -> None:
    facts = {
        "role": "work_lane",
        "current_branch": "work/example",
        "current_head": "head",
        "branch": "work/example",
        "holder_ref": "agent:test:case:holder",
        "target_holder_ref": "agent:test:case:target" if operation.startswith("handoff_") else "",
        "actor_ref": "agent:test:case:target"
        if operation == "handoff_accept"
        else "agent:test:case:holder",
        "expect_head": "head",
        "lease_id": "lease:one",
        "expected_epoch": 1,
        "expected_expires_at": "2099-01-01T00:00:00+00:00",
        "expected_payload_sha256": "a" * 64,
        "ttl_seconds": 60,
        "offer_id": "offer:one" if operation == "handoff_accept" else "",
        "holder_quiesced": operation == "handoff_accept",
        "apply": False,
        **changes,
    }

    result = reduce_lease_request(LEASE_TRANSITIONS[operation], LeaseFacts(**facts))

    assert (result.state, result.gaps) == (state, gaps)


def test_guard_reducer_preserves_declared_order_deduplicates_and_applies_state() -> None:
    evaluation = reduce_guards(
        apply=True,
        initial_gaps=("first", "first"),
        checks=((False, "second"),),
    )

    assert evaluation.ok is False
    assert evaluation.state == "blocked"
    assert evaluation.gaps == ("first", "second")
