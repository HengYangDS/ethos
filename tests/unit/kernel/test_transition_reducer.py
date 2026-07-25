from __future__ import annotations

from ethos.contracts.transitions import CLOSEOUT_TRANSITION
from ethos.contracts.transitions import GUARDED_TRANSITION
from ethos.contracts.transitions import WORK_LANE_TRANSITION
from ethos.contracts.transitions import TransitionFacts
from ethos.contracts.transitions import TransitionRequest
from ethos.contracts.transitions import reduce_transition


def test_transition_reducer_orders_and_deduplicates_every_hard_gap() -> None:
    decision = reduce_transition(
        WORK_LANE_TRANSITION,
        TransitionRequest(command="land", apply=True),
        TransitionFacts(
            current_head="current",
            role="accepted_root",
            initial_gaps=("first", "first"),
            checks=((False, "second"),),
            evidence_gaps=("proof_not_proven",),
        ),
    )

    assert decision.verdict == "block"
    assert decision.state == "blocked"
    assert decision.required_gaps == (
        "authorization_required",
        "expect_head_required",
        "protected_root_mutation",
        "first",
        "second",
        "proof_not_proven",
    )


def test_transition_reducer_distinguishes_unknown_current_planned_and_applied() -> None:
    unknown = reduce_transition(
        CLOSEOUT_TRANSITION,
        TransitionRequest(),
        TransitionFacts(unknown_gaps=("candidate_head_unavailable",)),
    )
    current = reduce_transition(
        CLOSEOUT_TRANSITION,
        TransitionRequest(),
        TransitionFacts(role="accepted_root", current=True),
    )
    planned = reduce_transition(
        CLOSEOUT_TRANSITION,
        TransitionRequest(),
        TransitionFacts(role="accepted_root"),
    )
    applied = reduce_transition(
        CLOSEOUT_TRANSITION,
        TransitionRequest(apply=True, authorized=True, expect_head="head"),
        TransitionFacts(current_head="head", role="accepted_root"),
    )

    assert (unknown.verdict, unknown.state) == ("unknown", "unknown")
    assert (current.verdict, current.state) == ("pass", "current")
    assert (planned.verdict, planned.state) == ("pass", "dry_run")
    assert (applied.verdict, applied.state) == ("pass", "closeout_ready")


def test_work_lane_non_land_dry_run_short_circuits_without_observation() -> None:
    result = reduce_transition(
        WORK_LANE_TRANSITION,
        TransitionRequest(command="publish"),
        TransitionFacts(),
    )

    assert result.ok is True
    assert result.state == "dry_run"
    assert result.gaps == ()


def test_guarded_transition_preserves_order_and_deduplicates() -> None:
    evaluation = reduce_transition(
        GUARDED_TRANSITION,
        TransitionRequest(apply=True),
        TransitionFacts(initial_gaps=("first", "first"), checks=((False, "second"),)),
    )

    assert evaluation.ok is False
    assert evaluation.state == "blocked"
    assert evaluation.gaps == ("first", "second")
