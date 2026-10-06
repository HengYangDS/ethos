"""Native complete-scope observation, cancellation and freshness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import tomli_w
from filelock import FileLock

import ethos.adapters.repo.runtime.materialization.input_resolution as input_resolution
import ethos.repository.release.resources as resource_owner
import tests
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_INPUTS
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from tests.unit.ci.dependency_audit.support import clean_report
from tests.unit.ci.dependency_audit.support import invoke_audit
from tests.unit.ci.dependency_audit.support import native_result
from tests.unit.ci.dependency_audit.support import native_transport
from tools.ci import dependency_audit as audit


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
            return native_result(command, current)
        if fault == "timeout":
            raise subprocess.TimeoutExpired(command, 120, output="partial", stderr="deadline")
        if fault == "spawn":
            message = "spawn unavailable"
            raise OSError(message)
        raw = clean_report(current)
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

    observed = native_transport(monkeypatch, respond)
    payload = invoke_audit(repository)
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
    native_transport(monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem))
    assert invoke_audit(repository)["verdict"] == "pass"
    policy = repository / audit.POLICY
    if fault == "missing":
        policy.unlink()
    else:
        replacement = {"zero": "0", "string": '"120"', "unknown-field": "120"}[fault]
        text = policy.read_text().replace(
            "timeout_seconds = 120", "timeout_seconds = " + replacement
        )
        policy.write_text(text + ("\nundeclared = true\n" if fault == "unknown-field" else ""))
    assert invoke_audit(repository)["verdict"] == "unknown"


def test_registry_has_one_security_owner_without_making_offline_tests_online() -> None:
    """Online security guards delivery without changing the offline test plane."""
    root = Path(tests.__file__).resolve().parent.parent
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
    observed = native_transport(
        monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem)
    )
    assert invoke_audit(repository)["verdict"] == "pass"
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

        native_transport(monkeypatch, interrupt)
        with pytest.raises(KeyboardInterrupt):
            audit.run(Mock(error=pytest.fail), root=repository)
        current = json.loads(summary.read_text())
        assert (current["state"], current["verdict"], current["checks"]) == (
            "running",
            "unknown",
            [],
        )
        native_transport(monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem))
        assert invoke_audit(repository)["verdict"] == "pass"


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
        return native_result(command, current)

    native_transport(monkeypatch, respond)
    payload = invoke_audit(repository)
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
    observed = native_transport(
        monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem)
    )
    payload = invoke_audit(repository)
    assert payload["verdict"] == "unknown"
    assert len(payload["checks"]) == 2
    assert len(observed) == 1
    if text is None:
        assert lock in json.dumps(payload)


def test_product_policy_drift_invalidates_the_same_attempt(repository, monkeypatch):
    """Resource freshness is independent of subject Git inputs and saved decisions."""
    product = resource_owner.canonical_resource(AUDIT_POLICY_PATH)

    def respond(_root, command, ecosystem):
        if ecosystem == "npm":
            policy = tomllib.loads(product.read_text())
            policy["summary"] = "Changed product approval declaration"
            product.write_text(tomli_w.dumps(policy))
        return native_result(command, ecosystem)

    native_transport(monkeypatch, respond)
    payload = invoke_audit(repository)
    assert payload["decision"]["verdict"] == "block"
    assert "dependency_audit_product_policy_changed" in payload["required_gaps"]


def test_audit_workspace_closure_is_read_once_per_observation(repository, monkeypatch):
    """Local manifests and root aliases share bytes, not freshness across observations."""
    local = repository / "workspace"
    local.mkdir()
    (local / "pyproject.toml").write_text('[project]\nname = "workspace"\n')
    (local / "package.json").write_text('{"name":"workspace"}\n')
    (repository / "uv.lock").write_text(
        '[[package]]\nname = "root"\nsource = { editable = "." }\n'
        '[[package]]\nname = "workspace"\nsource = { virtual = "workspace" }\n'
    )
    (repository / "package-lock.json").write_text(
        '{"packages":{"":{},"workspace":{},"node_modules/third-party":{}}}\n'
    )
    original = Path.read_bytes
    reads = []

    def read(path):
        if path.is_relative_to(repository):
            reads.append(path.relative_to(repository).as_posix())
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    native_transport(
        monkeypatch, lambda _root, command, ecosystem: native_result(command, ecosystem)
    )
    observed = invoke_audit(repository)
    assert observed["verdict"] == "pass"
    expected = {*AUDIT_INPUTS, "workspace/pyproject.toml", "workspace/package.json"}
    selected = [name for name in reads if name in expected]
    assert set(selected) == set(observed["inputs"]) == expected
    assert all(selected.count(name) == 2 for name in expected)
    assert all(
        hashlib.sha256(original(repository / name)).hexdigest() == observed["inputs"][name]
        for name in expected
    )
    (local / "package.json").unlink()
    missing = invoke_audit(repository)
    assert missing["checks"][0]["verdict"] == "pass"
    assert missing["checks"][1]["verdict"] == "unknown"


def test_npm_command_uses_the_resolved_complete_node_runtime(monkeypatch, repository):
    """Executable and npm are selected together without the superseded Python supplier."""
    observed = native_transport(
        monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem)
    )
    runtime = SimpleNamespace(executable=repository / "node.exe", npm=repository / "npm-cli.js")
    monkeypatch.setattr(input_resolution, "resolve_node_runtime", lambda: runtime, raising=False)
    assert invoke_audit(repository)["verdict"] == "pass"
    assert observed[1][:2] == (str(runtime.executable), str(runtime.npm))


def test_node_resolution_failure_keeps_both_audit_observations(repository, monkeypatch):
    """Command selection failure preserves the missing ecosystem's uncertainty receipt."""
    native_transport(monkeypatch, lambda _root, cmd, ecosystem: native_result(cmd, ecosystem))

    def unavailable():
        message = "fixture_native_node_unavailable"
        raise ValueError(message)

    monkeypatch.setattr(input_resolution, "resolve_node_runtime", unavailable)
    payload = invoke_audit(repository)
    assert [(c["ecosystem"], c["verdict"]) for c in payload["checks"]] == [
        ("python", "pass"),
        ("npm", "unknown"),
    ]
    assert payload["checks"][1]["reason"] == "native_execution_unavailable"
    assert payload["checks"][1]["failure"]["kind"] == "ValueError"
