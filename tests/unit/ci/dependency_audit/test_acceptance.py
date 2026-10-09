"""Exact artifact risk decisions preserve raw findings and purpose boundaries."""

from __future__ import annotations

import json
import subprocess
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import ethos.repository.release.resources as resource_owner
import tests
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from ethos.repository.policy.quality.dependency_acceptance import AuditPolicy
from ethos.repository.policy.quality.dependency_acceptance import compose_audit_policies
from ethos.repository.policy.quality.dependency_acceptance import evaluate_dependency_acceptance
from ethos.repository.policy.quality.dependency_acceptance import product_audit_projection
from tests.unit.ci.dependency_audit.support import authorize_fixture
from tests.unit.ci.dependency_audit.support import clean_report
from tests.unit.ci.dependency_audit.support import invoke_audit
from tests.unit.ci.dependency_audit.support import native_result
from tests.unit.ci.dependency_audit.support import native_transport
from tests.unit.ci.dependency_audit.support import npm_advisories
from tests.unit.ci.dependency_audit.support import npm_transport
from tools.ci import dependency_audit as audit
from tools.ci import sessions


def test_local_disposition_preserves_native_findings_and_strict_release(
    repository, monkeypatch, capsys
):
    """Exact local permission never converts six native aggregates into clean release proof."""
    raw = npm_advisories(repository)
    output = json.dumps(raw)
    authorize_fixture(repository)
    npm_transport(monkeypatch, output, "native")
    for scope in ("production-release", "local-development", "production-release"):
        payload = invoke_audit(repository, scope=scope)
        assert json.loads(capsys.readouterr().out) == payload
        assert payload["verdict"] == "block"
        assert payload["decision"]["scope"] == scope
        assert payload["decision"]["verdict"] == (
            "pass" if scope == "local-development" else "block"
        )
        native = payload["checks"][1]
        assert (native["verdict"], native["finding_count"], native["exit_code"]) == ("block", 6, 1)
        assert native["stdout"] == output
        if scope == "local-development":
            assert payload["decision"]["advisory_count"] == 1
            assert payload["decision"]["covered_package_count"] == 6
            assert payload["decision"]["approvals"][0]["approval_ref"] == (
                "fixture:human-approved-risk"
            )


@pytest.mark.parametrize(
    ("scope", "ci"),
    [("production-release", False), ("production-release", True), ("local-development", False)],
)
def test_artifact_risk_acceptance_is_portable_without_hiding_native_findings(
    repository, monkeypatch, scope, ci
):
    """A release-authorized artifact is accepted across hosts and exact lock placements."""
    raw = npm_advisories(repository)
    authorize_fixture(
        repository,
        scope="production-release",
        host=None,
        expires_at=None,
        nodes=None,
        lock_sha256=None,
    )
    monkeypatch.setattr(audit.platform, "node", lambda: "another-host")
    if ci:
        monkeypatch.setenv("CI", "true")
    npm_transport(monkeypatch, json.dumps(raw))
    payload = invoke_audit(repository, scope=scope)
    assert payload["verdict"] == payload["checks"][1]["verdict"] == "block"
    assert payload["decision"]["verdict"] == "pass"
    assert payload["decision"]["advisory_count"] == 1
    assert payload["decision"]["covered_package_count"] == 6


def test_product_policy_reports_exact_findings_without_changing_subject_policy(
    repository, monkeypatch
):
    """Product reporting preserves native evidence and derives each fresh lock subject."""
    raw = npm_advisories(repository)
    source = Path(tests.__file__).resolve().parent.parent / AUDIT_POLICY_PATH
    resource_owner.canonical_resource(AUDIT_POLICY_PATH).write_bytes(
        product_audit_projection(source.read_bytes())
    )
    subject_before = (repository / AUDIT_POLICY_PATH).read_bytes()
    npm_transport(monkeypatch, json.dumps(raw))
    payload = invoke_audit(repository)
    assert payload["verdict"] == "block"
    assert payload["decision"]["verdict"] == "pass"
    assert payload["product_policy"]["path"] == AUDIT_POLICY_PATH
    assert payload["product_policy"]["build"]["source_commit"]
    assert payload["decision"]["reason"] == "reported_findings"
    assert payload["decision"]["finding_count"] == 6
    assert [record[1] for record in payload["decision"]["reported_subjects"]] == ["braces"]
    assert (repository / AUDIT_POLICY_PATH).read_bytes() == subject_before
    assert source.is_file()

    locked = json.loads((repository / "package-lock.json").read_text())
    locked["packages"]["node_modules/braces"]["integrity"] = "sha512-Y2hhbmdlZA=="
    (repository / "package-lock.json").write_text(json.dumps(locked) + "\n")
    fresh = invoke_audit(repository)
    assert fresh["decision"]["verdict"] == "pass"
    assert fresh["decision"]["reported_subjects"][0][3] == "sha512-Y2hhbmdlZA=="
    assert fresh["inputs"]["package-lock.json"] != payload["inputs"]["package-lock.json"]


def test_product_policy_composition_preserves_exact_records_and_subject_execution(
    repository,
):
    """Composition deduplicates identities, not distinct authorization constraints."""
    npm_advisories(repository)
    authorize_fixture(repository)
    authorize_fixture(
        repository,
        scope="production-release",
        host=None,
        expires_at=None,
        nodes=None,
        lock_sha256=None,
    )
    raw = (repository / AUDIT_POLICY_PATH).read_bytes()
    subject = AuditPolicy.model_validate(tomllib.loads(raw.decode()))
    projected = product_audit_projection(raw)
    product = AuditPolicy.model_validate(tomllib.loads(projected.decode()))
    assert product_audit_projection(projected) == projected
    assert product.dispositions == [subject.dispositions[1]]
    different = product.dispositions[0].model_copy(update={"owner": "fixture:other-owner"})
    composed = compose_audit_policies(
        subject, product.model_copy(update={"dispositions": [*product.dispositions, different]})
    )
    assert composed.dispositions == [*subject.dispositions, different]
    assert composed.runner == subject.runner
    assert composed.timeout_seconds == subject.timeout_seconds
    assert (
        subject.dispositions == AuditPolicy.model_validate(tomllib.loads(raw.decode())).dispositions
    )


@pytest.mark.parametrize("fault", ["expired", "lock", "nodes", "new-advisory"])
def test_exact_disposition_does_not_cover_changed_or_expired_findings(
    repository, monkeypatch, fault
):
    """Only current exact approved identities can grant the narrower local scope."""
    raw = npm_advisories(repository)
    changes = {
        "expired": {"expires_at": datetime(2000, 1, 1, tzinfo=UTC)},
        "lock": {"lock_sha256": "0" * 64},
        "nodes": {"nodes": ["node_modules/other"]},
    }
    authorize_fixture(repository, **changes.get(fault, {}))
    if fault == "new-advisory":
        extra = dict(raw["vulnerabilities"]["braces"]["via"][0])
        extra["url"] = "https://github.com/advisories/GHSA-xxxx-yyyy-zzzz"
        raw["vulnerabilities"]["braces"]["via"].append(extra)
    npm_transport(monkeypatch, json.dumps(raw))
    payload = invoke_audit(repository, scope="local-development")
    assert payload["verdict"] == payload["decision"]["verdict"] == "block"
    if fault == "expired":
        assert "expired" in json.dumps(payload["decision"])


@pytest.mark.parametrize("fault", ["dangling", "cycle"])
def test_unresolved_npm_aggregate_identity_is_not_an_authorized_finding(
    repository, monkeypatch, fault
):
    """Missing aggregate references and cycles retain native findings without local permission."""
    raw = npm_advisories(repository)
    authorize_fixture(repository)
    raw["vulnerabilities"]["braces"]["via"].append(
        "absent" if fault == "dangling" else "micromatch"
    )
    npm_transport(monkeypatch, json.dumps(raw))
    payload = invoke_audit(repository, scope="local-development")
    assert payload["verdict"] == "block"
    assert payload["decision"]["verdict"] == "unknown"
    assert payload["decision"]["reason"] == "finding_identity_unavailable"


@pytest.mark.parametrize(
    "fault", ["python-adverse", "timeout", "drift", "naive-expiry", "policy-revoked-before-inputs"]
)
def test_local_approval_cannot_replace_observation_and_valid_policy(repository, monkeypatch, fault):
    """Approved findings cannot cover another failure, source drift or an invalid expiry."""
    raw = npm_advisories(repository)
    unapproved = (repository / audit.POLICY).read_bytes()
    authorize_fixture(
        repository,
        **(
            {"expires_at": datetime(2050, 1, 1, tzinfo=UTC).replace(tzinfo=None)}
            if fault == "naive-expiry"
            else {}
        ),
    )

    def respond(root, cmd, ecosystem):
        if ecosystem == "npm":
            if fault == "timeout":
                raise subprocess.TimeoutExpired(cmd, 120, output="partial", stderr="deadline")
            if fault == "drift":
                target = root / "package.json"
                target.write_bytes(target.read_bytes() + b"\n")
            return subprocess.CompletedProcess(cmd, 1, json.dumps(raw), "")
        if fault == "python-adverse":
            python = clean_report("python")
            python["summary"]["adverse_statuses"] = 1
            python["adverse_statuses"] = [{"name": "fixture", "status": "quarantined"}]
            return subprocess.CompletedProcess(cmd, 1, json.dumps(python), "")
        return native_result(cmd, ecosystem)

    native_transport(monkeypatch, respond)
    if fault == "policy-revoked-before-inputs":
        validate = audit.AuditPolicy.model_validate

        def revoke(data, **options):
            policy = validate(data, **options)
            (repository / audit.POLICY).write_bytes(unapproved)
            return policy

        monkeypatch.setattr(audit.AuditPolicy, "model_validate", revoke)
    payload = invoke_audit(repository, scope="local-development")
    assert payload["decision"]["verdict"] != "pass"
    if fault == "timeout":
        assert payload["checks"][1]["reason"] == "native_execution_unavailable"
        assert payload["checks"][1]["stdout"] == "partial"
    if fault == "naive-expiry":
        assert payload["state"] == "unavailable"


def test_local_disposition_is_bound_to_host_and_evaluation_time(repository, monkeypatch):
    """A copied approval or old receipt cannot authorize another host or renew expiry."""
    raw = npm_advisories(repository)
    expires = datetime(2050, 1, 1, tzinfo=UTC)
    authorize_fixture(repository, expires_at=expires)
    npm_transport(monkeypatch, json.dumps(raw))
    with monkeypatch.context() as patch:
        patch.setattr(audit.platform, "node", lambda: "other-host.invalid")
        assert invoke_audit(repository, scope="local-development")["decision"]["verdict"] == "block"

    with monkeypatch.context() as patch:
        patch.setenv("CI", "true")
        decision = invoke_audit(repository, scope="local-development")["decision"]
        assert decision["verdict"] == "block"
        assert decision["reason"] == "local_development_context_required"

    class ExpiredClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return expires.astimezone(tz)

    monkeypatch.setattr(audit, "datetime", ExpiredClock)
    payload = invoke_audit(repository, scope="local-development")
    assert payload["decision"]["verdict"] == "block"
    assert payload["decision"]["expired_approvals"] == ["fixture:human-approved-risk"]


def test_default_scope_and_native_remediation_remain_strict(repository, monkeypatch):
    """The local selector is explicit and genuine clean observations need no exception."""
    native_transport(monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem))
    session = Mock(posargs=(), error=pytest.fail)
    monkeypatch.setattr(sessions, "RUNTIME", SimpleNamespace(root=repository))
    monkeypatch.setenv("ETHOS_AUDIT_SCOPE", "local-development")
    sessions.vulnerabilities(session)
    payload = json.loads((repository / audit.EVIDENCE / "dependency-audit.json").read_text())
    assert payload["verdict"] == "pass"
    assert payload["decision"]["scope"] == "production-release"
    for arguments in (("--scope", "other"), ("--local-development",)):
        session.posargs = arguments
        with pytest.raises(ValueError, match="dependency_audit_scope_invalid"):
            sessions.vulnerabilities(session)


@pytest.mark.parametrize(
    "fault", ["none", "owner-integrity", "unbundled", "owner-missing", "additional-node"]
)
def test_bundled_advisory_uses_owning_lock_artifact(repository, monkeypatch, fault):
    """Native bundle ownership authorizes exact components, not lexical package names."""
    raw = npm_advisories(repository)
    packages = json.loads((repository / "package-lock.json").read_text())["packages"]
    owner = "node_modules/fixture-cli"
    bundled = owner + "/node_modules/container"
    node = bundled + "/node_modules/braces"
    integrity = "sha512-YnVuZGxlZA=="
    packages[owner] = {
        "version": "2.0.0",
        "integrity": integrity,
        "bundleDependencies": ["container"],
    }
    packages[bundled] = {"version": "1.0.0", "inBundle": True}
    packages[node] = {"version": "3.0.3", "inBundle": True}
    raw["vulnerabilities"]["braces"]["nodes"] = [node]
    if fault == "owner-integrity":
        packages[owner]["integrity"] = "sha512-ZHJpZnQ="
    elif fault == "unbundled":
        del packages[node]["inBundle"]
    elif fault == "owner-missing":
        del packages[owner]
    elif fault == "additional-node":
        raw["vulnerabilities"]["braces"]["nodes"].append("node_modules/braces")
    (repository / "package-lock.json").write_text(json.dumps({"packages": packages}) + "\n")
    authorize_fixture(repository, integrity=integrity, nodes=[node])
    output = json.dumps(raw)
    npm_transport(monkeypatch, output, "native bundle diagnostic")
    local = invoke_audit(repository, scope="local-development")
    assert local["verdict"] == "block"
    assert local["checks"][1]["stdout"] == output
    assert local["decision"]["verdict"] == (
        "pass"
        if fault == "none"
        else "unknown"
        if fault in {"unbundled", "owner-missing"}
        else "block"
    )
    strict = invoke_audit(repository)
    assert strict["decision"]["verdict"] == "block"
    assert strict["decision"]["scope"] == "production-release"


@pytest.mark.parametrize(
    ("scope", "ci"),
    [("production-release", False), ("production-release", True), ("local-development", False)],
)
def test_declared_advisory_reporting_preserves_native_evidence(repository, monkeypatch, scope, ci):
    """Complete findings are disclosed without blocking an explicitly reporting owner."""
    raw = npm_advisories(repository)
    output = json.dumps(raw)
    policy = repository / audit.POLICY
    policy.write_text(policy.read_text() + '\nfinding_action = "report"\n')
    if ci:
        monkeypatch.setenv("CI", "true")
    npm_transport(monkeypatch, output)
    payload = invoke_audit(repository, scope=scope)
    assert payload["verdict"] == "block"
    assert payload["checks"][1]["stdout"] == output
    assert payload["decision"]["verdict"] == "pass"
    assert payload["decision"]["reason"] == "reported_findings"
    assert payload["decision"]["finding_count"] == 6


def test_reported_advisories_do_not_authorize_inconsistent_observation(repository, monkeypatch):
    """Advisory disposition never waives native exits or captured manifest identity."""
    raw = npm_advisories(repository)
    policy_path = repository / audit.POLICY
    policy_path.write_text(policy_path.read_text() + '\nfinding_action = "report"\n')
    npm_transport(monkeypatch, json.dumps(raw))
    payload = invoke_audit(repository)
    policy = AuditPolicy.model_validate(tomllib.loads(policy_path.read_text()))
    options = {
        "lock_source": (repository / "package-lock.json").read_bytes(),
        "scope": "production-release",
        "host": "native-host",
        "now": datetime.now(UTC),
        "ci": False,
    }
    assert evaluate_dependency_acceptance(policy, payload, **options)["verdict"] == "pass"
    for exit_code in (0, 2):
        inconsistent = json.loads(json.dumps(payload))
        inconsistent["checks"][1]["exit_code"] = exit_code
        assert evaluate_dependency_acceptance(policy, inconsistent, **options)["verdict"] != "pass"
    assert (
        evaluate_dependency_acceptance(policy, payload, **{**options, "lock_source": b"{}"})[
            "verdict"
        ]
        != "pass"
    )


def test_reporting_preserves_non_advisory_python_failure(repository, monkeypatch):
    """A native quarantine is not a disclosed advisory and remains a refusal."""
    policy = repository / audit.POLICY
    policy.write_text(policy.read_text() + '\nfinding_action = "report"\n')

    def respond(_root, command, ecosystem):
        raw = clean_report(ecosystem)
        if ecosystem == "python":
            raw["summary"]["adverse_statuses"] = 1
            raw["adverse_statuses"] = [{"name": "fixture", "status": "quarantined"}]
        return subprocess.CompletedProcess(command, int(ecosystem == "python"), json.dumps(raw), "")

    native_transport(monkeypatch, respond)
    payload = invoke_audit(repository)
    assert payload["verdict"] == payload["decision"]["verdict"] == "block"
    assert payload["decision"]["reason"] == "native_adverse_statuses"
