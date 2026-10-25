"""Findings without a stable upstream fix are reported; fixable or unobserved ones still block."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC
from datetime import datetime

import pytest

from ethos.adapters.repo.dependency_acceptance import captured_dependency_acceptance
from ethos.repository.policy.quality.dependency_acceptance import AuditPolicy
from ethos.repository.policy.quality.dependency_acceptance import evaluate_dependency_acceptance
from tests.unit.ci.dependency_audit.support import authorize_fixture
from tests.unit.ci.dependency_audit.support import clean_report
from tests.unit.ci.dependency_audit.support import invoke_audit
from tests.unit.ci.dependency_audit.support import native_result
from tests.unit.ci.dependency_audit.support import native_transport
from tests.unit.ci.dependency_audit.support import npm_advisories

UNDICI = "https://github.com/advisories/GHSA-3wwx-pv8p-q78v"
JINJA = "GHSA-cpwx-vrp4-4pq7"


def _transport(monkeypatch, raw: dict, latest: dict[str, object]) -> list[tuple[str, ...]]:
    """Answer registry views from an explicit observation; other execution stays native-shaped."""
    output = json.dumps(raw)

    def respond(_root, command, ecosystem):
        if "view" in command:
            name = command[command.index("view") + 1].removesuffix("@latest")
            value = latest.get(name)
            if isinstance(value, BaseException):
                raise value
            if value is None:
                return subprocess.CompletedProcess(command, 1, "", "npm error code E404")
            return subprocess.CompletedProcess(command, 0, json.dumps(value, indent=2) + "\n", "")
        if ecosystem == "npm":
            return subprocess.CompletedProcess(command, 1, output, "")
        return native_result(command, ecosystem)

    return native_transport(monkeypatch, respond)


def _views(observed: list[tuple[str, ...]]) -> list[str]:
    return [command[command.index("view") + 1] for command in observed if "view" in command]


@pytest.mark.parametrize("scope", ["production-release", "local-development"])
@pytest.mark.parametrize(
    ("latest", "verdict"),
    [
        ({"braces": "3.0.3"}, "pass"),
        ({"braces": ["3.0.3"]}, "pass"),
        ({"braces": "3.0.4"}, "block"),
        ({}, "block"),
        ({"braces": 3}, "block"),
        ({"braces": ["3.0.3", "3.0.2"]}, "block"),
        ({"braces": [""]}, "block"),
        ({"braces": subprocess.TimeoutExpired(("npm", "view"), 120)}, "block"),
    ],
)
def test_finding_at_latest_stable_release_is_reported_not_blocking(
    repository, monkeypatch, scope, latest, verdict
):
    """Only a locked artifact that already is its latest stable release has no upgrade fix."""
    raw = npm_advisories(repository)
    observed = _transport(monkeypatch, raw, latest)
    payload = invoke_audit(repository, scope=scope)
    assert payload["verdict"] == payload["checks"][1]["verdict"] == "block"
    assert payload["checks"][1]["finding_count"] == 6
    assert _views(observed) == ["braces@latest"]
    expected = {"braces": "3.0.3"} if verdict == "pass" else {}
    if latest.get("braces") == "3.0.4":
        expected = {"braces": "3.0.4"}
    assert payload["upstream"]["npm"] == expected
    decision = payload["decision"]
    assert (decision["scope"], decision["verdict"]) == (scope, verdict)
    if verdict == "pass":
        assert decision["reason"] == "unfixed_upstream_findings_reported"
        assert decision["unapproved_subjects"] == []
        assert [subject[1:3] for subject in decision["unfixed_upstream_subjects"]] == [
            ["braces", "3.0.3"]
        ]
        assert decision["covered_package_count"] == 6
    else:
        assert decision["reason"] == "unapproved_or_expired_findings"
        assert decision["unfixed_upstream_subjects"] == []
        assert [subject[1] for subject in decision["unapproved_subjects"]] == ["braces"]


def _bundled(repository) -> dict:
    """Lock npm 12.2.0 with a bundled component and its native advisory aggregate."""
    lock = {
        "packages": {
            "": {},
            "node_modules/npm": {"version": "12.2.0", "integrity": "sha512-bnBt"},
            "node_modules/npm/node_modules/undici": {"version": "6.28.0", "inBundle": True},
        }
    }
    (repository / "package-lock.json").write_text(json.dumps(lock) + "\n")
    raw = clean_report("npm")
    raw["vulnerabilities"]["undici"] = {
        "name": "undici",
        "via": [{"name": "undici", "dependency": "undici", "url": UNDICI, "range": "<6.28.1"}],
        "nodes": ["node_modules/npm/node_modules/undici"],
        "severity": "high",
    }
    raw["metadata"]["vulnerabilities"].update(high=1, total=1)
    raw["metadata"]["dependencies"]["total"] = 407
    return raw


@pytest.mark.parametrize(("release", "verdict"), [("12.2.0", "pass"), ("12.3.0", "block")])
def test_bundled_component_is_decided_by_its_owning_release(
    repository, monkeypatch, release, verdict
):
    """A bundled component is decided by the latest release of the package that ships it."""
    observed = _transport(monkeypatch, _bundled(repository), {"npm": release})
    payload = invoke_audit(repository)
    assert _views(observed) == ["npm@latest"]
    assert payload["checks"][1]["verdict"] == "block"
    assert payload["decision"]["verdict"] == verdict
    if verdict == "pass":
        [subject] = payload["decision"]["unfixed_upstream_subjects"]
        assert subject[:3] == [UNDICI, "undici", "6.28.0"]
        assert subject[4] == ["node_modules/npm/node_modules/undici"]


@pytest.mark.parametrize("scope", ["local-development", "production-release"])
def test_exact_approval_keeps_precedence_over_reporting(repository, monkeypatch, scope):
    """An approved subject stays an explicit authorization, not an unfixed-upstream report."""
    raw = npm_advisories(repository)
    authorize_fixture(repository, scope=scope)
    observed = _transport(monkeypatch, raw, {})
    payload = invoke_audit(repository, scope=scope)
    assert _views(observed) == []
    assert payload["checks"][1]["verdict"] == "block"
    assert payload["upstream"]["npm"] == {}
    decision = payload["decision"]
    assert (decision["verdict"], decision["reason"]) == ("pass", "authorized_findings")
    assert decision["unfixed_upstream_subjects"] == []
    assert decision["approvals"][0]["approval_ref"] == "fixture:human-approved-risk"


@pytest.mark.parametrize(
    ("change", "verdict", "reason"),
    [
        ("none", "pass", "unfixed_upstream_findings_reported"),
        ("missing", "block", "unapproved_or_expired_findings"),
        ("malformed", "unknown", "finding_identity_unavailable"),
    ],
)
def test_captured_upstream_observation_is_reevaluated_without_network(
    repository, monkeypatch, change, verdict, reason
):
    """Landing and hooks re-read the same-attempt observation; absence never grants permission."""
    _transport(monkeypatch, npm_advisories(repository), {"braces": "3.0.3"})
    payload = invoke_audit(repository)
    if change == "missing":
        payload.pop("upstream")
    elif change == "malformed":
        payload["upstream"] = ["braces"]
    decision = captured_dependency_acceptance(
        json.dumps(payload),
        head="a" * 40,
        source=lambda name: (repository / name).read_bytes(),
        scope="production-release",
    )
    assert (decision["verdict"], decision["reason"]) == (verdict, reason)


def _python_decision(fixes: list[str], adverse: list[dict] | None = None) -> dict:
    report = {
        "summary": {"audited_packages": 3, "vulnerabilities": 1, "adverse_statuses": 0},
        "vulnerabilities": [
            {
                "dependency": {"name": "jinja2", "version": "3.1.2"},
                "id": JINJA,
                "fix_versions": fixes,
                "link": "https://nvd.nist.gov/vuln/detail/CVE-2025-27516",
            }
        ],
        "adverse_statuses": adverse or [],
    }
    report["summary"]["adverse_statuses"] = len(report["adverse_statuses"])
    lock = b'{"packages": {"": {}}}\n'
    reason = "vulnerabilities_or_adverse_statuses"
    checks = [
        {"ecosystem": "python", "exit_code": 1, "stdout": json.dumps(report)},
        {"ecosystem": "npm", "exit_code": 0, "stdout": json.dumps(clean_report("npm"))},
    ]
    checks[0].update(verdict="block", reason=reason)
    checks[1].update(verdict="pass", reason="clean")
    payload = {
        "state": "finished",
        "required_gaps": [f"python:{reason}"],
        "checks": checks,
        "verdict": "block",
        "inputs": {"package-lock.json": hashlib.sha256(lock).hexdigest()},
    }
    policy = {"owner": "o", "summary": "s", "runner": "r", "timeout_seconds": 120}
    return evaluate_dependency_acceptance(
        AuditPolicy.model_validate(policy),
        payload,
        lock_source=lock,
        scope="production-release",
        host="fixture-host",
        now=datetime(2026, 10, 13, tzinfo=UTC),
        ci=True,
    )


@pytest.mark.parametrize(
    ("fixes", "verdict"),
    [
        ([], "pass"),
        (["3.1.6"], "block"),
        (["4.0.0rc1"], "pass"),
        (["2.11.3"], "pass"),
        (["2.11.3", "3.1.6"], "block"),
        (["unparseable"], "block"),
    ],
)
def test_python_advisory_without_newer_stable_fix_is_reported(fixes, verdict):
    """Native fix versions decide: only a newer official stable release is a fix."""
    decision = _python_decision(fixes)
    assert decision["verdict"] == verdict
    subjects = decision["unfixed_upstream_subjects" if verdict == "pass" else "unapproved_subjects"]
    assert subjects == [(f"python:{JINJA}", "jinja2", "3.1.2", "", ())]


def test_python_adverse_status_remains_strict():
    """Yanked or otherwise adverse packages are not advisories and keep the strict result."""
    decision = _python_decision([], adverse=[{"name": "jinja2", "status": "yanked"}])
    assert decision == {
        "scope": "production-release",
        "verdict": "block",
        "reason": "strict_native_result",
    }
