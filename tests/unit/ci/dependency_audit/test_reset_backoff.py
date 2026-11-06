"""An advisory service that resets connections for minutes is ridden out, then named."""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

import pytest

from ethos.repository.policy.quality.dependency_acceptance import interpret_native_audit
from tests.unit.ci.dependency_audit.support import clean_report
from tests.unit.ci.dependency_audit.support import invoke_audit
from tests.unit.ci.dependency_audit.support import native_result
from tests.unit.ci.dependency_audit.support import native_transport
from tools.ci import dependency_audit as audit

_ROOT = Path(__file__).resolve().parents[4]
# uv's own diagnostic when its OSV query fails, as GitLab verify job 65919 recorded it.
_RESET = (
    "error: Request failed after 3 retries\n"
    "  cause: error sending request for url (https://api.osv.dev/v1/querybatch)\n"
    "  cause: client error (Connect)\n"
    "  cause: Connection reset by peer (os error 104)\n"
)


@pytest.mark.parametrize(
    ("stdout", "exit_code", "stderr", "reason"),
    [
        ("", 2, _RESET, "advisory_request_failed"),
        ("", 2, "error: something else\n", "native_output_invalid"),
        ("", 0, _RESET, "native_output_invalid"),
        ("{", 2, _RESET, "native_output_invalid"),
    ],
    ids=["reset", "other-error", "clean-exit", "partial-report"],
)
def test_only_a_python_audit_without_a_report_and_a_failed_request_is_a_transport_failure(
    stdout: str, exit_code: int, stderr: str, reason: str
) -> None:
    assert interpret_native_audit("python", stdout, exit_code, stderr)[1] == reason


def _python_sequence(monkeypatch: pytest.MonkeyPatch, outputs: list[tuple[int, str, str]]):
    pending = list(outputs)
    pauses: list[float] = []

    def respond(_root, command, ecosystem):
        if ecosystem == "npm":
            return native_result(command, ecosystem)
        code, stdout, stderr = pending.pop(0)
        return subprocess.CompletedProcess(command, code, stdout, stderr)

    monkeypatch.setattr(audit.time, "sleep", pauses.append)
    return native_transport(monkeypatch, respond), pauses


def test_a_burst_of_resets_is_ridden_out_with_the_backoff(repository, monkeypatch) -> None:
    clean = json.dumps(clean_report("python"))
    outputs = [(2, "", _RESET)] * 3 + [(0, clean, "")]
    _observed, pauses = _python_sequence(monkeypatch, outputs)

    payload = invoke_audit(repository)

    python = payload["checks"][0]
    assert (python["verdict"], python["reason"]) == ("pass", "clean")
    assert [attempt["reason"] for attempt in python["attempts"]] == [
        "advisory_request_failed",
        "advisory_request_failed",
        "advisory_request_failed",
        "clean",
    ]
    assert pauses == [60, 120, 240]


def test_a_lasting_outage_is_reported_by_its_native_reason(repository, monkeypatch) -> None:
    _observed, pauses = _python_sequence(monkeypatch, [(2, "", _RESET)] * 4)

    payload = invoke_audit(repository)

    python = payload["checks"][0]
    assert (python["verdict"], python["reason"]) == ("unknown", "advisory_request_failed")
    assert len(python["attempts"]) == 4
    assert pauses == [60, 120, 240]
    assert payload["decision"] == {
        "scope": "production-release",
        "verdict": "unknown",
        "reason": "advisory_request_failed",
    }


def test_the_audit_gate_declares_a_budget_that_fits_the_backoff() -> None:
    gates = tomllib.loads((_ROOT / "system/repository-gates.toml").read_text(encoding="utf-8"))
    gate = next(gate for gate in gates["gates"] if gate["id"] == "dependency-vulnerabilities")
    policy = tomllib.loads(
        (_ROOT / ".config/checks/dependency-vulnerabilities/policy.toml").read_text(
            encoding="utf-8"
        )
    )
    # Each attempt runs within the policy's timeout, and every pause runs before a retry.
    attempts = len(audit.BACKOFF_SECONDS) + 1
    budget = sum(audit.BACKOFF_SECONDS) + attempts * policy["timeout_seconds"]
    assert gate["timeout_seconds"] >= budget
