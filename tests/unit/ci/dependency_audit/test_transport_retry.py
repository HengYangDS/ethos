"""Only a failed npm advisory request is observed again; every attempt stays in the receipt."""

from __future__ import annotations

import json
import subprocess

import pytest

from ethos.repository.policy.quality.dependency_acceptance import interpret_native_audit
from tests.unit.ci.dependency_audit.support import clean_report
from tests.unit.ci.dependency_audit.support import invoke_audit
from tests.unit.ci.dependency_audit.support import native_result
from tests.unit.ci.dependency_audit.support import native_transport
from tools.ci import dependency_audit as audit

_BULK = "https://registry.npmjs.org/-/npm/v1/security/advisories/bulk"


def _request_failed(reason: str = "socket hang up") -> str:
    """Return npm's own JSON for an advisory request that never produced a report."""
    return json.dumps(
        {
            "message": f"request to {_BULK} failed, reason: {reason}",
            "error": {"summary": "", "detail": ""},
        }
    )


def _finding() -> str:
    raw = clean_report("npm")
    raw["vulnerabilities"] = {"test-package": {"name": "test-package"}}
    raw["metadata"]["vulnerabilities"].update(high=1, total=1)
    return json.dumps(raw)


@pytest.mark.parametrize(
    ("output", "exit_code", "reason"),
    [
        (_request_failed(), 1, "advisory_request_failed"),
        (_request_failed("getaddrinfo ENOTFOUND registry.npmjs.org"), 1, "advisory_request_failed"),
        (
            json.dumps({"message": "request to https://example.test/other failed"}),
            1,
            "native_output_invalid",
        ),
        (_request_failed(), 0, "native_output_invalid"),
        ("not-json", 1, "native_output_invalid"),
        (_finding(), 1, "vulnerabilities_or_adverse_statuses"),
    ],
)
def test_only_a_failed_bulk_advisory_request_is_a_transport_failure(
    output: str, exit_code: int, reason: str
) -> None:
    assert interpret_native_audit("npm", output, exit_code)[1] == reason


def _npm_sequence(monkeypatch: pytest.MonkeyPatch, outputs: list[tuple[int, str]]) -> list:
    pending = list(outputs)

    def respond(_root, command, ecosystem):
        if ecosystem == "python":
            return native_result(command, ecosystem)
        code, output = pending.pop(0)
        return subprocess.CompletedProcess(command, code, output, f"npm diagnostic {code}")

    monkeypatch.setattr(audit, "_RETRY_PAUSE_SECONDS", 0)
    return native_transport(monkeypatch, respond)


def test_a_failed_request_followed_by_a_clean_report_passes_with_both_attempts(
    repository, monkeypatch
) -> None:
    clean = json.dumps(clean_report("npm"))
    observed = _npm_sequence(monkeypatch, [(1, _request_failed()), (0, clean)])

    payload = invoke_audit(repository)

    npm = payload["checks"][1]
    assert (payload["verdict"], npm["verdict"], npm["reason"]) == ("pass", "pass", "clean")
    assert [attempt["reason"] for attempt in npm["attempts"]] == [
        "advisory_request_failed",
        "clean",
    ]
    assert "npm diagnostic 1" in npm["attempts"][0]["stderr"]
    assert len(observed) == 3


def test_repeated_request_failure_stops_after_three_attempts(repository, monkeypatch) -> None:
    observed = _npm_sequence(monkeypatch, [(1, _request_failed())] * 3)

    payload = invoke_audit(repository)

    npm = payload["checks"][1]
    assert (payload["verdict"], npm["reason"]) == ("unknown", "advisory_request_failed")
    assert len(npm["attempts"]) == 3
    assert len(observed) == 4
    assert payload["decision"]["verdict"] != "pass"


@pytest.mark.parametrize("output", ["finding", "malformed"])
def test_findings_and_malformed_reports_are_observed_once(
    repository, monkeypatch, output: str
) -> None:
    raw = _finding() if output == "finding" else "not-json"
    observed = _npm_sequence(monkeypatch, [(1, raw)])

    payload = invoke_audit(repository)

    npm = payload["checks"][1]
    assert len(observed) == 2
    assert len(npm["attempts"]) == 1
    assert npm["verdict"] == ("block" if output == "finding" else "unknown")
