from __future__ import annotations

from ethos_core.contracts.mutation import CLOSEOUT_MUTATION
from ethos_core.contracts.mutation import WORK_LANE_MUTATION
from ethos_core.contracts.mutation import MutationFacts
from ethos_core.contracts.mutation import MutationRequest
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
