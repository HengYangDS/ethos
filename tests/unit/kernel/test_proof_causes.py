"""A proof keeps each failed gate's own cause and verdict class from execution to its result."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof_validation import assess_proof_execution
from ethos.contracts.outcome import Outcome
from ethos.contracts.outcome import OutcomeError
from tests.support.proof import conformant_proof_checks
from tests.support.proof import current_proof_plan
from tests.support.proof import proof_repository

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan

REPORT = {"verdict": "pass", "required_gaps": []}


def _timed_out(check: dict[str, object]) -> dict[str, object]:
    gate = check["action_id"]
    return check | {
        "verdict": "unknown",
        "exit_code": 124,
        "diagnostics": [
            {
                "kind": "gate_timeout",
                "timeout_seconds": 30,
                "required_gaps": [f"gate_timeout:{gate}"],
            }
        ],
        "timeout_seconds": 30,
        "timeout_source": "gate",
    }


def _assess(checks: list[dict[str, object]], *, execute: bool) -> Outcome:
    plan = cast("TransitionPlan", SimpleNamespace(verdict="pass", required_gaps=()))
    return assess_proof_execution(
        audit=REPORT,
        lifecycle=REPORT,
        plan=plan,
        checks=checks,
        runs_ok=not execute,
        execute=execute,
        full=execute,
        expected_head=None,
        current_head="a" * 40,
        scope_gaps=(),
    )


def test_assessment_keeps_a_timed_out_gate_cause_after_its_class_code() -> None:
    passing = {"action_id": "lint", "verdict": "pass", "exit_code": 0, "trust_bearing": True}
    timed = _timed_out({"action_id": "tests", "trust_bearing": True})
    assessed = _assess([timed, passing], execute=True)
    assert (assessed.verdict, assessed.gaps) == (
        "unknown",
        ("gate_unknown:tests", "gate_timeout:tests"),
    )
    assert assessed.causes == (
        {
            "subject": "tests",
            "verdict": "unknown",
            "gaps": ["gate_unknown:tests", "gate_timeout:tests"],
            "kind": "gate_timeout",
            "timeout_seconds": 30,
            "exit_code": 124,
        },
    )
    unexecuted = {
        "action_id": "tests",
        "verdict": "unknown",
        "exit_code": None,
        "trust_bearing": True,
    }
    assert _assess([unexecuted], execute=False) == Outcome()


def test_issuance_refuses_with_the_assessed_verdict_and_every_cause(tmp_path: Path) -> None:
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)
    checks = tuple(_timed_out(dict(check)) for check in conformant_proof_checks(plan))
    assessed = _assess(list(checks), execute=True)
    payload = {
        "plan": plan,
        "checks": checks,
        "verdict": assessed.verdict,
        "required_gaps": assessed.gaps,
        "issuer": "agent:test:case:proof",
        "scope": "repository",
        "boundary": "repository",
    }
    with pytest.raises(OutcomeError) as refused:
        issue_proof_attestation(repo, payload)
    outcome, gate = refused.value.outcome, checks[0]["action_id"]
    assert outcome.verdict == "unknown"
    assert outcome.gaps[:2] == (f"gate_unknown:{gate}", f"gate_timeout:{gate}")
    assert f"gate_execution_not_proven:{gate}" in outcome.gaps
    assert outcome.causes == assessed.causes
    assert refused.value.observation["artifact_reference"]
