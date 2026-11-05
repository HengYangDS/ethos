"""Results compose their parts without losing a cause or a verdict class."""

from __future__ import annotations

from ethos.adapters.process import ProcessExecutionError
from ethos.contracts.outcome import CAUSE_LIMIT
from ethos.contracts.outcome import Outcome
from ethos.contracts.outcome import OutcomeError
from ethos.contracts.outcome import outcome_of
from ethos.contracts.outcome import refusal
from ethos.result import EthosResult

TIMEOUT = Outcome.part(
    "unknown",
    "gate_unknown:tests",
    ("gate_timeout:tests",),
    subject="tests",
    facts={"kind": "gate_timeout", "timeout_seconds": 30},
)


def test_combine_reduces_verdicts_and_keeps_every_part_in_order() -> None:
    lint = Outcome.part("block", "gate_failed:lint", ("quality_gate_failed:lint",), subject="lint")
    assert Outcome().combine(TIMEOUT).verdict == "unknown"
    combined = Outcome().combine(TIMEOUT, lint, Outcome.of("block", "expected_head_mismatch"))
    assert combined.verdict == "block"
    assert combined.gaps == (
        "gate_unknown:tests",
        "gate_timeout:tests",
        "gate_failed:lint",
        "quality_gate_failed:lint",
        "expected_head_mismatch",
    )
    assert combined.causes == (
        {
            "subject": "tests",
            "verdict": "unknown",
            "gaps": ["gate_unknown:tests", "gate_timeout:tests"],
            "kind": "gate_timeout",
            "timeout_seconds": 30,
        },
        {
            "subject": "lint",
            "verdict": "block",
            "gaps": ["gate_failed:lint", "quality_gate_failed:lint"],
        },
    )
    assert Outcome().combine() == Outcome() == Outcome.of("pass")
    assert Outcome.of("pass", "unmet", "unmet").gaps == ("unmet",)
    assert Outcome.of("pass", "unmet").verdict == "block"


def test_a_part_keeps_its_class_code_first_and_counts_what_it_omits() -> None:
    causes = (*(f"cause:{index}" for index in range(CAUSE_LIMIT + 2)), "gate_failed:x", "cause:0")
    part = Outcome.part("block", "gate_failed:x", causes, subject="x")
    assert part.gaps == ("gate_failed:x", *causes[:CAUSE_LIMIT])
    assert part.causes[0]["omitted_gap_count"] == 2
    assert "omitted_gap_count" not in TIMEOUT.causes[0]


def test_next_action_comes_from_a_part_that_carries_the_combined_verdict() -> None:
    waiting = Outcome.of("unknown", "a", next_action="wait")
    assert waiting.combine(Outcome.of("block", "b", next_action="repair b")).next_action == (
        "repair b"
    )
    assert waiting.combine(Outcome.of("block", "c")).next_action == "wait"


def test_errors_carry_every_gap_and_the_verdict_their_producer_declared() -> None:
    error = refusal("first", "second")
    assert isinstance(error, OutcomeError)
    assert isinstance(error, ValueError)
    assert str(error) == "first"
    assert outcome_of(error) == Outcome.of("block", "first", "second")
    assert outcome_of(refusal("late", verdict="unknown")).verdict == "unknown"
    timed_out = ProcessExecutionError("git_process_timed_out", reason="deadline", verdict="unknown")
    assert outcome_of(timed_out) == Outcome.of("unknown", "git_process_timed_out")
    assert str(timed_out) == "git_process_timed_out"
    observed = ProcessExecutionError(
        "lead", reason="r", observation={"required_gaps": ["a", "lead"]}
    )
    assert (outcome_of(observed).gaps, str(observed)) == (("a", "lead"), "lead")
    assert outcome_of(ValueError(" plain ")) == Outcome.of("block", "plain")
    assert outcome_of(RuntimeError()) == Outcome.of("block", "RuntimeError")


def test_one_conversion_builds_every_boundary_result() -> None:
    result = EthosResult.from_outcome("prove", TIMEOUT, fallback="ethos plan --changed --json")
    assert (result.verdict, result.state, result.required_gaps, result.next_action) == (
        "unknown",
        "unknown",
        TIMEOUT.gaps,
        "ethos plan --changed --json",
    )
    assert result.to_dict()["diagnostics"] == list(TIMEOUT.causes)
    declared = Outcome.of("block", "gap", next_action="repair the gap")
    assert EthosResult.from_outcome("x", declared, fallback="other").next_action == "repair the gap"
    chosen = EthosResult.from_outcome("x", declared, state="gapped", next_action="refresh")
    assert (chosen.state, chosen.next_action) == ("gapped", "refresh")
