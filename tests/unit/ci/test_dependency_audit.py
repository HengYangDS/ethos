"""Native dependency evidence is complete, bounded and tied to unchanged inputs."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from filelock import FileLock

import ethos.adapters.repo.runtime.materialization.input_resolution as input_resolution
from ethos.contracts.gates import load_gate_registry_declaration
from tools.ci import dependency_audit as audit
from tools.ci import sessions

if TYPE_CHECKING:
    from collections.abc import Callable


def _clean(ecosystem: str) -> dict:
    """Return native-shaped reports, not a shared fake result schema."""
    if ecosystem == "python":
        return {
            "summary": {"audited_packages": 1, "vulnerabilities": 0, "adverse_statuses": 0},
            "vulnerabilities": [],
            "adverse_statuses": [],
        }
    return {
        "auditReportVersion": 2,
        "vulnerabilities": {},
        "metadata": {
            "vulnerabilities": dict.fromkeys(
                ("info", "low", "moderate", "high", "critical", "total"), 0
            ),
            "dependencies": {"total": 1},
        },
    }


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bind the real declaration and every required native input in isolation."""
    monkeypatch.delenv("CI", raising=False)
    root = Path(__file__).resolve().parents[3]
    for name in (*audit.INPUTS, "tools/ci/dependency_audit.py", "tools/ci/sessions.py"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / name).read_bytes())
    (tmp_path / "package-lock.json").write_text('{"packages":{"":{}}}\n')
    return tmp_path


def _invoke(root: Path, **options) -> dict:
    """Read the actual persisted result even when Nox refuses the observation."""
    with suppress(pytest.fail.Exception):
        audit.run(Mock(error=pytest.fail), root=root, **options)
    return json.loads((root / audit.EVIDENCE / "dependency-audit.json").read_text())


def _transport(monkeypatch, respond: Callable) -> list[tuple[str, ...]]:
    """Replace only external execution; command selection stays real."""
    observed: list[tuple[str, ...]] = []
    monkeypatch.setattr(audit, "current_tracked_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        input_resolution,
        "resolve_node_runtime",
        lambda: SimpleNamespace(executable=Path("/fixture/node"), npm=Path("/fixture/npm-cli.js")),
        raising=False,
    )

    def execute(root: Path, command: tuple[str, ...], **options):
        observed.append(command)
        assert options["timeout"] == 120
        assert options["remove_env_prefixes"] == ("GIT_",)
        ecosystem = "npm" if any("npm-cli.js" in part for part in command) else "python"
        return respond(root, command, ecosystem)

    monkeypatch.setattr(audit, "run_command", execute)
    return observed


def _result(command, ecosystem):
    return subprocess.CompletedProcess(command, 0, json.dumps(_clean(ecosystem)), "")


def _npm_transport(monkeypatch, output: str, stderr: str = "") -> None:
    """Reuse adverse npm execution without changing raw evidence or diagnostics."""
    _transport(
        monkeypatch,
        lambda _root, cmd, ecosystem: (
            subprocess.CompletedProcess(cmd, 1, output, stderr)
            if ecosystem == "npm"
            else _result(cmd, ecosystem)
        ),
    )


def _npm_advisories(root: Path) -> dict:
    """Retain the observed one-advisory, six-package npm aggregate journey."""
    relations = {
        "braces": [],
        "micromatch": ["braces"],
        "fast-glob": ["micromatch"],
        "globby": ["fast-glob", "micromatch"],
        "@fission-ai/openspec": ["fast-glob"],
        "markdownlint-cli2": ["globby", "micromatch"],
    }
    raw = _clean("npm")
    packages = {"": {}}
    for name, via in relations.items():
        node = "node_modules/" + name
        raw["vulnerabilities"][name] = {
            "name": name,
            "via": via,
            "nodes": [node],
            "severity": "high",
        }
        packages[node] = {"version": "1.0.0", "integrity": "sha512-Zml4dHVyZQ=="}
    packages["node_modules/braces"] = {
        "version": "3.0.3",
        "integrity": "sha512-yQbXgO/OSZVD2IsiLlro+7Hf6Q18EJrKSEsdoMzKePKXct3gvD8oLcOQdIzGupr5Fj"
        "+EDe8gO/lxc1BzfMpxvA==",
    }
    raw["vulnerabilities"]["braces"]["via"] = [
        {
            "source": 1240992,
            "name": "braces",
            "dependency": "braces",
            "url": "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm",
            "range": "<=3.0.3",
        }
    ]
    raw["metadata"]["vulnerabilities"].update(high=6, total=6)
    raw["metadata"]["dependencies"]["total"] = 407
    (root / "package-lock.json").write_text(json.dumps({"packages": packages}) + "\n")
    return raw


def _authorize(root: Path, **changes) -> None:
    """Create an explicitly test-only approval, never a live policy exception."""
    locked = json.loads((root / "package-lock.json").read_text())["packages"]["node_modules/braces"]
    record = {
        "ecosystem": "npm",
        "advisory_url": "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm",
        "package": "braces",
        "version": locked["version"],
        "integrity": locked["integrity"],
        "nodes": ["node_modules/braces"],
        "lock_sha256": hashlib.sha256((root / "package-lock.json").read_bytes()).hexdigest(),
        "scope": "local-development",
        "host": platform.node(),
        "owner": "fixture:owner",
        "approval_ref": "fixture:human-approved-risk",
        "rationale": "Test-only bounded local iteration; no production or release permission.",
        "expires_at": datetime(2050, 1, 1, tzinfo=UTC),
    }
    record.update(changes)
    rendered = ["\n[[dispositions]]"]
    for key, value in record.items():
        text = value.isoformat() if isinstance(value, datetime) else json.dumps(value)
        rendered.append(f"{key} = {text}")
    policy = root / audit.POLICY
    policy.write_text(policy.read_text().replace("dispositions = []\n", "") + "\n".join(rendered))


@pytest.mark.parametrize("ecosystem", ["python", "npm"])
@pytest.mark.parametrize(
    "fault", ["clean", "finding", "malformed", "counts", "nonzero", "timeout", "spawn"]
)
def test_nonpassing_ecosystem_does_not_hide_the_other(
    repository, monkeypatch, ecosystem, fault
) -> None:
    """One bad result is retained while the other ecosystem is still observed."""

    def respond(_root, command, current):
        if current != ecosystem:
            return _result(command, current)
        if fault == "timeout":
            raise subprocess.TimeoutExpired(command, 120, output="partial", stderr="deadline")
        if fault == "spawn":
            message = "spawn unavailable"
            raise OSError(message)
        raw = _clean(current)
        if fault == "finding":
            if current == "python":
                raw["vulnerabilities"] = [{"id": "test-advisory"}]
                raw["summary"]["vulnerabilities"] = 1
            else:
                raw["vulnerabilities"] = {"test-package": {"name": "test-package"}}
                raw["metadata"]["vulnerabilities"].update(high=1, total=1)
        if fault == "counts":
            if current == "python":
                raw["summary"]["vulnerabilities"] = True
            else:
                raw["metadata"]["vulnerabilities"]["total"] = True
        return subprocess.CompletedProcess(
            command,
            int(fault in {"finding", "nonzero"}),
            "not-json" if fault == "malformed" else json.dumps(raw),
            "native diagnostic",
        )

    observed = _transport(monkeypatch, respond)
    payload = _invoke(repository)
    assert len(observed) == 2
    assert payload["verdict"] == (
        "pass" if fault == "clean" else "block" if fault == "finding" else "unknown"
    )
    assert [check["ecosystem"] for check in payload["checks"]] == ["python", "npm"]
    assert "--frozen" in observed[0]
    assert {"--package-lock-only", "--ignore-scripts", "--include=dev"} <= set(observed[1])
    assert payload["inputs"]["package-lock.json"]
    failed = next(check for check in payload["checks"] if check["ecosystem"] == ecosystem)
    assert (failed["verdict"] == "pass") is (fault == "clean")
    assert failed["stderr"]
    if fault == "timeout":
        assert failed["stdout"] == "partial"
        assert "deadline" in failed["stderr"]


@pytest.mark.parametrize("fault", ["missing", "zero", "string", "unknown-field"])
def test_invalid_policy_replaces_previous_success(repository, monkeypatch, fault) -> None:
    """An invalid declaration cannot inherit an older clean receipt."""
    _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    assert _invoke(repository)["verdict"] == "pass"
    policy = repository / audit.POLICY
    if fault == "missing":
        policy.unlink()
    else:
        replacement = {"zero": "0", "string": '"120"', "unknown-field": "120"}[fault]
        text = policy.read_text().replace(
            "timeout_seconds = 120", "timeout_seconds = " + replacement
        )
        policy.write_text(text + ("\nundeclared = true\n" if fault == "unknown-field" else ""))
    assert _invoke(repository)["verdict"] == "unknown"


def test_registry_has_one_security_owner_without_making_offline_tests_online() -> None:
    """Online security guards delivery without changing the offline test plane."""
    root = Path(__file__).resolve().parents[3]
    declaration = load_gate_registry_declaration(root / "system/gates.toml")
    registry = declaration.registry()
    assert "python-vulnerabilities" not in registry
    assert "dependency-vulnerabilities" in registry
    assert "dependency-vulnerabilities" in {gate.id for gate in declaration.proof_gates(full=True)}
    for selected in ((), ("unit-architecture",)):
        assert "dependency-vulnerabilities" not in {
            gate.id for gate in declaration.proof_gates(selected)
        }
    for gate_id in ("build", "local-install-smoke"):
        assert "dependency-vulnerabilities" in {
            gate.id for gate in declaration.proof_gates((gate_id,))
        }


@pytest.mark.parametrize("fault", ["contention", "interrupt"])
def test_active_evidence_is_preserved_and_interruption_recovers(repository, monkeypatch, fault):
    """Concurrent readers preserve the slot; interrupted owners invalidate and recover."""
    observed = _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    assert _invoke(repository)["verdict"] == "pass"
    evidence = repository / audit.EVIDENCE
    summary = evidence / "dependency-audit.json"
    previous = summary.read_bytes()
    observed.clear()
    if fault == "contention":
        with (
            FileLock(evidence / ".dependency-audit.lock", timeout=0),
            pytest.raises(pytest.fail.Exception, match="dependency_audit_in_use"),
        ):
            audit.run(Mock(error=pytest.fail), root=repository)
        assert not observed
        assert summary.read_bytes() == previous
    else:

        def interrupt(_root, _command, _ecosystem):
            raise KeyboardInterrupt

        _transport(monkeypatch, interrupt)
        with pytest.raises(KeyboardInterrupt):
            audit.run(Mock(error=pytest.fail), root=repository)
        current = json.loads(summary.read_text())
        assert (current["state"], current["verdict"], current["checks"]) == (
            "running",
            "unknown",
            [],
        )
        _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
        assert _invoke(repository)["verdict"] == "pass"


@pytest.mark.parametrize(
    "path", ["uv.lock", "package.json", audit.POLICY, "tools/ci/sessions.py", "python", "npm"]
)
def test_native_input_drift_invalidates_result(repository, monkeypatch, path):
    """Root and local-workspace inputs belong to the same native freshness closure."""
    target = repository / path
    ecosystem = path if path in {"python", "npm"} else "npm"
    if path in {"python", "npm"}:
        filename = "pyproject.toml" if path == "python" else "package.json"
        target = repository / "packages/local" / filename
        target.parent.mkdir(parents=True)
        target.write_text('name="local"' if path == "python" else '{"name":"local"}')
        lock, contents = (
            ("uv.lock", '[[package]]\nname="local"\n[package.source]\neditable="packages/local"\n')
            if path == "python"
            else ("package-lock.json", '{"packages":{"":{},"packages/local":{}}}')
        )
        (repository / lock).write_text(contents)

    def respond(_root, command, current):
        if current == ecosystem:
            target.write_bytes(target.read_bytes() + b"\n")
        return _result(command, current)

    _transport(monkeypatch, respond)
    payload = _invoke(repository)
    assert payload["verdict"] == "block"
    assert "dependency_audit_inputs_changed" in payload["required_gaps"]


@pytest.mark.parametrize(
    ("lock", "text"),
    [
        ("uv.lock", None),
        ("package-lock.json", None),
        ("uv.lock", "[[package]]\nsource=17\n"),
        ("uv.lock", "package=[17]\n"),
        ("package-lock.json", '{"packages":null}'),
    ],
)
def test_unavailable_native_scope_preserves_other_observation(repository, monkeypatch, lock, text):
    """Missing and malformed scopes cannot become empty successful observations."""
    target = repository / lock
    if text is None:
        target.unlink()
    else:
        target.write_text(text)
    observed = _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    payload = _invoke(repository)
    assert payload["verdict"] == "unknown"
    assert len(payload["checks"]) == 2
    assert len(observed) == 1
    if text is None:
        assert lock in json.dumps(payload)


def test_local_disposition_preserves_native_findings_and_strict_release(repository, monkeypatch):
    """Exact local permission never converts six native aggregates into clean release proof."""
    raw = _npm_advisories(repository)
    output = json.dumps(raw)
    _authorize(repository)
    _npm_transport(monkeypatch, output, "native")
    for scope in ("production-release", "local-development", "production-release"):
        payload = _invoke(repository, scope=scope)
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


@pytest.mark.parametrize("fault", ["expired", "lock", "nodes", "new-advisory"])
def test_exact_disposition_does_not_cover_changed_or_expired_findings(
    repository, monkeypatch, fault
):
    """Only current exact approved identities can grant the narrower local scope."""
    raw = _npm_advisories(repository)
    changes = {
        "expired": {"expires_at": datetime(2000, 1, 1, tzinfo=UTC)},
        "lock": {"lock_sha256": "0" * 64},
        "nodes": {"nodes": ["node_modules/other"]},
    }
    _authorize(repository, **changes.get(fault, {}))
    if fault == "new-advisory":
        extra = dict(raw["vulnerabilities"]["braces"]["via"][0])
        extra["url"] = "https://github.com/advisories/GHSA-xxxx-yyyy-zzzz"
        raw["vulnerabilities"]["braces"]["via"].append(extra)
    _npm_transport(monkeypatch, json.dumps(raw))
    payload = _invoke(repository, scope="local-development")
    assert payload["verdict"] == payload["decision"]["verdict"] == "block"
    if fault == "expired":
        assert "expired" in json.dumps(payload["decision"])


@pytest.mark.parametrize("fault", ["dangling", "cycle"])
def test_unresolved_npm_aggregate_identity_is_not_an_authorized_finding(
    repository, monkeypatch, fault
):
    """Missing aggregate references and cycles retain native findings without local permission."""
    raw = _npm_advisories(repository)
    _authorize(repository)
    raw["vulnerabilities"]["braces"]["via"].append(
        "absent" if fault == "dangling" else "micromatch"
    )
    _npm_transport(monkeypatch, json.dumps(raw))
    payload = _invoke(repository, scope="local-development")
    assert payload["verdict"] == "block"
    assert payload["decision"]["verdict"] == "unknown"
    assert payload["decision"]["reason"] == "finding_identity_unavailable"


@pytest.mark.parametrize(
    "fault", ["python-adverse", "timeout", "drift", "naive-expiry", "policy-revoked-before-inputs"]
)
def test_local_approval_cannot_replace_observation_and_valid_policy(repository, monkeypatch, fault):
    """Approved findings cannot cover another failure, source drift or an invalid expiry."""
    raw = _npm_advisories(repository)
    unapproved = (repository / audit.POLICY).read_bytes()
    _authorize(
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
            python = _clean("python")
            python["summary"]["adverse_statuses"] = 1
            python["adverse_statuses"] = [{"name": "fixture", "status": "quarantined"}]
            return subprocess.CompletedProcess(cmd, 1, json.dumps(python), "")
        return _result(cmd, ecosystem)

    _transport(monkeypatch, respond)
    if fault == "policy-revoked-before-inputs":
        validate = audit.AuditPolicy.model_validate

        def revoke(data, **options):
            policy = validate(data, **options)
            (repository / audit.POLICY).write_bytes(unapproved)
            return policy

        monkeypatch.setattr(audit.AuditPolicy, "model_validate", revoke)
    payload = _invoke(repository, scope="local-development")
    assert payload["decision"]["verdict"] != "pass"
    if fault == "timeout":
        assert payload["checks"][1]["reason"] == "native_execution_unavailable"
        assert payload["checks"][1]["stdout"] == "partial"
    if fault == "naive-expiry":
        assert payload["state"] == "unavailable"


def test_npm_command_uses_the_resolved_complete_node_runtime(monkeypatch, repository):
    """Executable and npm are selected together without the superseded Python supplier."""
    observed = _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    runtime = SimpleNamespace(executable=repository / "node.exe", npm=repository / "npm-cli.js")
    monkeypatch.setattr(input_resolution, "resolve_node_runtime", lambda: runtime, raising=False)
    assert _invoke(repository)["verdict"] == "pass"
    assert observed[1][:2] == (str(runtime.executable), str(runtime.npm))


def test_local_disposition_is_bound_to_host_and_evaluation_time(repository, monkeypatch):
    """A copied approval or old receipt cannot authorize another host or renew expiry."""
    raw = _npm_advisories(repository)
    expires = datetime(2050, 1, 1, tzinfo=UTC)
    _authorize(repository, expires_at=expires)
    _npm_transport(monkeypatch, json.dumps(raw))
    with monkeypatch.context() as patch:
        patch.setattr(audit.platform, "node", lambda: "other-host.invalid")
        assert _invoke(repository, scope="local-development")["decision"]["verdict"] == "block"

    with monkeypatch.context() as patch:
        patch.setenv("CI", "true")
        decision = _invoke(repository, scope="local-development")["decision"]
        assert decision["verdict"] == "block"
        assert decision["reason"] == "local_development_context_required"

    class ExpiredClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return expires.astimezone(tz)

    monkeypatch.setattr(audit, "datetime", ExpiredClock)
    payload = _invoke(repository, scope="local-development")
    assert payload["decision"]["verdict"] == "block"
    assert payload["decision"]["expired_approvals"] == ["fixture:human-approved-risk"]


def test_default_scope_and_native_remediation_remain_strict(repository, monkeypatch):
    """The local selector is explicit and genuine clean observations need no exception."""
    _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
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
    raw = _npm_advisories(repository)
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
    _authorize(repository, integrity=integrity, nodes=[node])
    output = json.dumps(raw)
    _npm_transport(monkeypatch, output, "native bundle diagnostic")
    local = _invoke(repository, scope="local-development")
    assert local["verdict"] == "block"
    assert local["checks"][1]["stdout"] == output
    assert local["decision"]["verdict"] == (
        "pass"
        if fault == "none"
        else "unknown"
        if fault in {"unbundled", "owner-missing"}
        else "block"
    )
    strict = _invoke(repository)
    assert strict["decision"]["verdict"] == "block"
    assert strict["decision"]["scope"] == "production-release"


def test_node_resolution_failure_keeps_both_audit_observations(repository, monkeypatch):
    """Command selection failure preserves the missing ecosystem's uncertainty receipt."""
    _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))

    def unavailable():
        message = "fixture_native_node_unavailable"
        raise ValueError(message)

    monkeypatch.setattr(input_resolution, "resolve_node_runtime", unavailable)
    payload = _invoke(repository)
    assert [(c["ecosystem"], c["verdict"]) for c in payload["checks"]] == [
        ("python", "pass"),
        ("npm", "unknown"),
    ]
    assert payload["checks"][1]["reason"] == "native_execution_unavailable"
    assert payload["checks"][1]["failure"]["kind"] == "ValueError"
