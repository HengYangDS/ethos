"""Double only external audit and quality tool execution for public journeys."""

from functools import partial

import pytest

import ethos.adapters.gates.code_quality as code_quality
import ethos.adapters.gates.native.attempt as gate_attempt
from ethos.repository.policy.quality.gate_composition import canonical_gate_command
from tests.unit.land.source_acceptance.support import COMMAND
from tests.unit.land.source_acceptance.support import native_result
from tests.unit.land.source_acceptance.support import quality_report


@pytest.fixture
def audit_attempts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Keep actual proof, intent, Git hooks and CAS while doubling external tools."""
    attempts: list[str] = []
    original_run = gate_attempt.run_command

    def external_run(root, command, **options):
        if canonical_gate_command(tuple(command)) != COMMAND:
            return original_run(root, command, **options)
        result = native_result(root, command)
        attempts.append(result.stdout)
        return result

    monkeypatch.setattr(gate_attempt, "run_command", external_run)
    for axis, name in (("behavior", "behavior_report"), ("static-analysis", "static_report")):
        monkeypatch.setattr(code_quality, name, partial(quality_report, axis=axis))
    return attempts
