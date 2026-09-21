"""Native dependency evidence is complete, bounded and tied to unchanged inputs."""

from __future__ import annotations

import json
import subprocess
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from filelock import FileLock

from ethos.contracts.gates import load_gate_registry_declaration
from tools.ci import dependency_audit as audit

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
def repository(tmp_path: Path) -> Path:
    """Bind the real declaration and every required native input in isolation."""
    root = Path(__file__).resolve().parents[3]
    for name in (*audit.INPUTS, "tools/ci/dependency_audit.py", "tools/ci/sessions.py"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / name).read_bytes())
    (tmp_path / "package-lock.json").write_text('{"packages":{"":{}}}\n')
    return tmp_path


def _invoke(root: Path) -> dict:
    """Read the actual persisted result even when Nox refuses the observation."""
    with suppress(pytest.fail.Exception):
        audit.run(Mock(error=pytest.fail), root=root)
    return json.loads((root / audit.EVIDENCE / "dependency-audit.json").read_text())


def _transport(monkeypatch, respond: Callable) -> list[tuple[str, ...]]:
    """Replace only external execution; command selection stays real."""
    observed: list[tuple[str, ...]] = []
    monkeypatch.setattr(audit, "current_tracked_head", lambda _root: "a" * 40)

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
