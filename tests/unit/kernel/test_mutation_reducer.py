from __future__ import annotations

import pytest

from ethos_core.contracts.mutation import CLOSEOUT_MUTATION
from ethos_core.contracts.mutation import HANDOFF_EXPORT
from ethos_core.contracts.mutation import WORK_LANE_MUTATION
from ethos_core.contracts.mutation import LeaseFacts
from ethos_core.contracts.mutation import MutationFacts
from ethos_core.contracts.mutation import MutationRequest
from ethos_core.contracts.mutation import lease_transition
from ethos_core.contracts.mutation import reduce_guards
from ethos_core.contracts.mutation import reduce_lease_request
from ethos_core.contracts.mutation import reduce_mutation


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


def test_lease_reducer_interprets_declared_operation_requirements() -> None:
    result = reduce_lease_request(
        lease_transition("handoff_accept"),
        LeaseFacts(
            role="accepted_root",
            current_branch="work/other",
            current_head="head",
            branch="work/example",
            expect_head="",
            lease_id="",
            epoch=None,
            ttl_seconds=0,
            offer_id="",
            apply=True,
        ),
    )

    assert result.gaps == (
        "work_lane_required",
        "lane_branch_mismatch",
        "expect_head_required",
        "lease_id_required",
        "lease_epoch_required",
        "lease_ttl_invalid",
        "handoff_offer_id_required",
    )


def test_lease_transition_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="lease_operation_unknown:unknown"):
        lease_transition("unknown")


def test_guard_reducer_preserves_declared_order_deduplicates_and_applies_state() -> None:
    evaluation = reduce_guards(
        HANDOFF_EXPORT,
        apply=True,
        initial_gaps=("first", "first"),
        checks=((False, "second"),),
    )

    assert evaluation.ok is False
    assert evaluation.state == "blocked"
    assert evaluation.gaps == ("first", "second")
