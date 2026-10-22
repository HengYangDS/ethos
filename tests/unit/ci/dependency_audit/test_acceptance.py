"""Exact artifact risk decisions preserve raw findings and purpose boundaries."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import tomli_w

import ethos.repository.release.resources as resource_owner
import tests
from ethos.adapters.repo.dependency_acceptance import captured_dependency_acceptance
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_INPUTS
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


def test_product_policy_accepts_only_its_exact_portable_artifact(repository, monkeypatch):
    """Product-owned release risk is consumed without changing the subject policy."""
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
    assert [record["package"] for record in payload["decision"]["approvals"]] == ["braces"]
    assert (repository / AUDIT_POLICY_PATH).read_bytes() == subject_before
    assert source.is_file()

    locked = json.loads((repository / "package-lock.json").read_text())
    locked["packages"]["node_modules/braces"]["integrity"] = "sha512-Y2hhbmdlZA=="
    (repository / "package-lock.json").write_text(json.dumps(locked) + "\n")
    assert invoke_audit(repository)["decision"]["verdict"] == "block"


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


@pytest.mark.parametrize(
    "fault", ["dangling", "cycle", "name", "advisory", "nodes", "node-path", "integrity", "version"]
)
def test_unresolved_npm_aggregate_identity_is_not_an_authorized_finding(
    repository, monkeypatch, fault
):
    """Unresolved aggregates and unbound lock identities retain findings without permission."""
    raw = npm_advisories(repository)
    authorize_fixture(repository)
    braces = raw["vulnerabilities"]["braces"]
    lock = repository / "package-lock.json"
    packages = json.loads(lock.read_text())["packages"]
    if fault in {"dangling", "cycle"}:
        braces["via"].append("absent" if fault == "dangling" else "micromatch")
    elif fault == "name":
        braces["name"] = "Braces"
    elif fault == "advisory":
        braces["via"][0]["url"] = "http://github.com/advisories/GHSA-vfj7-8cjw-p6xm"
    elif fault == "nodes":
        braces["nodes"] = []
    elif fault == "node-path":
        braces["nodes"] = ["node_modules/../node_modules/braces"]
    else:
        packages["node_modules/braces"][fault] = " "
        lock.write_text(json.dumps({"packages": packages}) + "\n")
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
    unresolved = fault in {"unbundled", "owner-missing"}
    assert strict["decision"]["verdict"] == ("unknown" if unresolved else "block")
    assert strict["decision"]["scope"] == "production-release"


_EXACT_RISK = {
    "ecosystem": "npm",
    "advisory_url": "https://github.com/advisories/GHSA-fixture",
    "package": "fixture",
    "version": "1.0.0",
    "integrity": "sha512-fixture",
    "scope": "production-release",
    "owner": "fixture:owner",
    "approval_ref": "fixture:approval",
    "rationale": "Test-only exact artifact risk.",
}


def _audit_policy(*records: dict) -> dict:
    return {
        "owner": "fixture:owner",
        "summary": "fixture",
        "runner": "fixture",
        "timeout_seconds": 1,
        "dispositions": list(records),
    }


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"owner": " fixture:owner"}, "nonblank and exact"),
        ({"rationale": " "}, "nonblank and exact"),
        ({"nodes": ["node_modules/fixture", "node_modules/fixture"]}, "nonempty and unique"),
        ({"nodes": [""]}, "nonempty and unique"),
        ({"host": "fixture-host "}, "host must be exact"),
        ({"scope": "local-development", "host": "fixture-host"}, "host, lock, nodes and expiry"),
    ],
)
def test_risk_disposition_names_exact_authority_and_local_bounds(changes, message):
    """Accepted risk keeps exact identity, distinct nodes and a bounded local context."""
    with pytest.raises(ValueError, match=message):
        AuditPolicy.model_validate(_audit_policy(_EXACT_RISK | changes))


def test_product_projection_refuses_host_bound_release_risk():
    """A portable release approval cannot carry one host's local authority."""
    source = tomli_w.dumps(_audit_policy(_EXACT_RISK | {"host": "fixture-host"})).encode()
    with pytest.raises(ValueError, match="product_audit_policy_host_bound"):
        product_audit_projection(source)


def _captured_payload(**changes) -> tuple[str, dict[str, bytes]]:
    sources = {name: f"captured {name}\n".encode() for name in AUDIT_INPUTS}
    payload = {
        "command": "dependency-audit",
        "head": "a" * 40,
        "inputs": {name: hashlib.sha256(value).hexdigest() for name, value in sources.items()},
    }
    payload.update(changes)
    return json.dumps(payload), sources


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("command", "dependency_audit_payload_invalid"),
        ("head", "dependency_audit_head_mismatch"),
        ("inputs", "dependency_audit_inputs_missing"),
        ("path", "dependency_audit_input_path_invalid"),
        ("changed", "dependency_audit_inputs_changed"),
        ("workspace", "dependency_audit_workspace_inputs_missing"),
    ],
)
def test_captured_acceptance_binds_exact_same_attempt_inputs(fault, reason):
    """Source permission reads only the exact captured audit attempt and its inputs."""
    stdout, sources = _captured_payload()
    payload = json.loads(stdout)
    if fault == "command":
        payload["command"] = "other"
    elif fault == "head":
        payload["head"] = "b" * 40
    elif fault == "inputs":
        payload["inputs"].pop("uv.lock")
    elif fault == "path":
        payload["inputs"] = {"../outside": "0" * 64, **payload["inputs"]}
    elif fault == "changed":
        sources["uv.lock"] = b"changed\n"
    else:
        sources["uv.lock"] = b"version = 1\n"
        sources["package-lock.json"] = b'{"packages": {"": {}, "packages/app": {}}}\n'
        payload["inputs"].update(
            {
                name: hashlib.sha256(sources[name]).hexdigest()
                for name in ("uv.lock", "package-lock.json")
            }
        )
    decision = captured_dependency_acceptance(
        json.dumps(payload), head="a" * 40, source=sources.__getitem__, scope="production-release"
    )
    assert decision == {"scope": "production-release", "verdict": "unknown", "reason": reason}


def _native_observation(fault: str) -> tuple[dict, bytes]:
    lock = b'{"packages": {"": {}}}\n'
    checks = [
        {
            "ecosystem": ecosystem,
            "exit_code": 0,
            "stdout": json.dumps(clean_report(ecosystem)),
            "verdict": "pass",
            "reason": "clean",
        }
        for ecosystem in ("python", "npm")
    ]
    payload = {
        "state": "finished",
        "required_gaps": [],
        "checks": checks,
        "verdict": "pass",
        "inputs": {"package-lock.json": hashlib.sha256(lock).hexdigest()},
    }
    if fault == "incomplete":
        payload["state"] = "running"
    elif fault == "verdict":
        checks[0]["verdict"] = "block"
    elif fault == "reduction":
        payload["verdict"] = "block"
    else:
        checks[1].update(exit_code=1, verdict="unknown", reason="native_execution_failed")
        payload.update(verdict="unknown", required_gaps=["npm:native_execution_failed"])
    return payload, lock


@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("incomplete", "dependency_audit_incomplete"),
        ("verdict", "native_audit_verdict_mismatch"),
        ("reduction", "native_audit_reduction_mismatch"),
        ("npm-exit", "native_execution_failed"),
    ],
)
def test_captured_verdicts_are_reinterpreted_from_native_output(fault, reason):
    """A saved summary never stands in for the exact native result it reduces."""
    payload, lock = _native_observation(fault)
    decision = evaluate_dependency_acceptance(
        AuditPolicy.model_validate(_audit_policy()),
        payload,
        lock_source=lock,
        scope="local-development",
        host="fixture-host",
        now=datetime(2026, 1, 1, tzinfo=UTC),
        ci=False,
    )
    assert decision == {"scope": "local-development", "verdict": "unknown", "reason": reason}


@pytest.mark.parametrize("change", ["reading-build", "policy-bytes"])
def test_captured_product_policy_is_bound_by_content_not_reading_build(
    repository, monkeypatch, change
):
    """A lane-built proof and the installed hook read one product policy through two builds."""
    native_transport(monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem))
    payload = invoke_audit(repository)
    binding = payload["product_policy"]
    if change == "reading-build":
        payload["product_policy"] = {
            **binding,
            "build": {**binding["build"], "source_commit": "c" * 40},
        }
    else:
        payload["product_policy"] = {**binding, "sha256": "0" * 64}
    decision = captured_dependency_acceptance(
        json.dumps(payload),
        head="a" * 40,
        source=lambda name: (repository / name).read_bytes(),
        scope="production-release",
    )
    assert decision["verdict"] == ("pass" if change == "reading-build" else "unknown"), decision
    if change == "policy-bytes":
        assert decision["reason"] == "dependency_audit_product_policy_changed"


@pytest.mark.parametrize("subject", ["product-source", "adopter", "tampered"])
def test_product_source_binds_the_policy_its_head_commits(repository, monkeypatch, subject):
    """The product's own source may change its policy; elsewhere a drifted product refuses."""
    native_transport(monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem))
    committed = repository / AUDIT_POLICY_PATH
    shipped = Path(resource_owner.files("ethos")) / "resources" / AUDIT_POLICY_PATH
    predecessor = shipped.read_bytes()
    committed.write_text(committed.read_text().replace("summary = ", 'summary = "Renewed" #', 1))
    shipped.write_bytes(product_audit_projection(committed.read_bytes()))
    payload = invoke_audit(repository)
    shipped.write_bytes(predecessor)
    if subject == "tampered":
        payload["product_policy"] = {**payload["product_policy"], "sha256": "0" * 64}

    decision = captured_dependency_acceptance(
        json.dumps(payload),
        head="a" * 40,
        source=lambda name: (repository / name).read_bytes(),
        scope="production-release",
        product_source=subject != "adopter",
    )

    if subject == "product-source":
        assert decision["verdict"] == "pass", decision
    else:
        assert decision["reason"] == "dependency_audit_product_policy_changed", decision
