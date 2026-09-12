"""Native dependency evidence is complete, bounded and tied to unchanged inputs."""

from __future__ import annotations

import json
import subprocess
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import pytest
from filelock import FileLock

from ethos.contracts.gates import load_gate_registry_declaration
from tools.ci import dependency_audit as audit

if TYPE_CHECKING:
    from collections.abc import Callable

    import nox


class Session:
    """Capture Nox's failure boundary without another executor."""

    def log(self, _message: str) -> None:
        """Accept the human projection of the recorded observation."""

    def error(self, message: str) -> None:
        """Mirror Nox's non-passing session result."""
        raise RuntimeError(message)


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
    with suppress(RuntimeError):
        audit.run(cast("nox.Session", Session()), root=root)
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


def test_security_entrypoint_observes_npm_after_clean_python(repository, monkeypatch) -> None:
    """The original Python-only false-green regression exercises the new owner."""
    observed = _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    payload = _invoke(repository)
    assert len(observed) == 2, "The required npm lock was never audited"
    assert payload["verdict"] == "pass", payload
    assert [check["ecosystem"] for check in payload["checks"]] == ["python", "npm"]
    assert "--frozen" in observed[0]
    assert {"--package-lock-only", "--ignore-scripts", "--include=dev"} <= set(observed[1])
    assert payload["inputs"]["package-lock.json"]


@pytest.mark.parametrize("ecosystem", ["python", "npm"])
@pytest.mark.parametrize("fault", ["finding", "malformed", "counts", "nonzero", "timeout", "spawn"])
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
    assert payload["verdict"] == ("block" if fault == "finding" else "unknown")
    failed = next(check for check in payload["checks"] if check["ecosystem"] == ecosystem)
    assert failed["verdict"] != "pass"
    assert failed["stderr"]
    if fault == "timeout":
        assert failed["stdout"] == "partial"
        assert "deadline" in failed["stderr"]


@pytest.mark.parametrize("missing", ["uv.lock", "package-lock.json"])
def test_missing_lock_still_observes_other_ecosystem(repository, monkeypatch, missing) -> None:
    """Missing input is neither empty scope nor reason to skip other diagnostics."""
    (repository / missing).unlink()
    observed = _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    payload = _invoke(repository)
    assert payload["verdict"] != "pass"
    assert len(observed) == 1
    assert len(payload["checks"]) == 2
    assert missing in json.dumps(payload)


@pytest.mark.parametrize("path", ["uv.lock", "package.json", audit.POLICY, "tools/ci/sessions.py"])
def test_input_drift_invalidates_result(repository, monkeypatch, path) -> None:
    """Clean native output cannot certify a different manifest, lock, policy or runner."""

    def respond(root, command, ecosystem):
        if ecosystem == "npm":
            target = root / path
            target.write_bytes(target.read_bytes() + b"\n")
        return _result(command, ecosystem)

    _transport(monkeypatch, respond)
    payload = _invoke(repository)
    assert payload["verdict"] == "block"
    assert "dependency_audit_inputs_changed" in payload["required_gaps"]


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
    assert "dependency-vulnerabilities" not in {
        gate.id for gate in declaration.proof_gates(("unit-architecture",))
    }
    for gate_id in ("build", "local-install-smoke"):
        assert "dependency-vulnerabilities" in {
            gate.id for gate in declaration.proof_gates((gate_id,))
        }


def test_concurrent_observer_cannot_replace_active_receipt(repository, monkeypatch) -> None:
    """An already owned evidence slot rejects reentry without clobbering its result."""
    observed = _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    evidence = repository / audit.EVIDENCE
    evidence.mkdir(parents=True)
    summary = evidence / "dependency-audit.json"
    summary.write_text('{"state":"running","verdict":"unknown","owner":"first"}')
    previous = summary.read_bytes()
    with (
        FileLock(evidence / ".dependency-audit.lock", timeout=0),
        pytest.raises(RuntimeError, match="dependency_audit_in_use"),
    ):
        audit.run(cast("nox.Session", Session()), root=repository)
    assert not observed
    assert summary.read_bytes() == previous


def test_interruption_replaces_old_success_and_allows_recovery(repository, monkeypatch) -> None:
    """A killed attempt has no green receipt and releases its coordination lock."""
    _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    assert _invoke(repository)["verdict"] == "pass"

    def interrupt(_root, _command, _ecosystem):
        raise KeyboardInterrupt

    _transport(monkeypatch, interrupt)
    with pytest.raises(KeyboardInterrupt):
        audit.run(cast("nox.Session", Session()), root=repository)
    summary = repository / audit.EVIDENCE / "dependency-audit.json"
    current = json.loads(summary.read_text())
    assert current["state"] == "running"
    assert current["verdict"] == "unknown"
    assert current["checks"] == []
    _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    assert _invoke(repository)["verdict"] == "pass"


@pytest.mark.parametrize("ecosystem", ["python", "npm"])
def test_workspace_manifest_drift_invalidates_native_result(repository, monkeypatch, ecosystem):
    """Both native workspace graphs contribute local manifests to freshness."""
    manifest = (
        repository
        / "packages/local"
        / ("pyproject.toml" if ecosystem == "python" else "package.json")
    )
    manifest.parent.mkdir(parents=True)
    manifest.write_text('name = "local"' if ecosystem == "python" else '{"name":"local"}')
    if ecosystem == "python":
        (repository / "uv.lock").write_text(
            '[[package]]\nname="local"\n[package.source]\neditable="packages/local"\n'
        )
    else:
        (repository / "package-lock.json").write_text('{"packages":{"":{},"packages/local":{}}}')

    def respond(_root, command, current):
        if current == ecosystem:
            manifest.write_text(manifest.read_text() + "\n")
        return _result(command, current)

    _transport(monkeypatch, respond)
    assert _invoke(repository)["verdict"] == "block"


@pytest.mark.parametrize(
    ("lock", "text"),
    [
        ("uv.lock", "[[package]]\nsource=17\n"),
        ("package-lock.json", '{"packages":null}'),
    ],
)
def test_malformed_workspace_scope_is_unknown_not_an_unhandled_failure(
    repository,
    monkeypatch,
    lock,
    text,
):
    """Malformed local workspace scope preserves the other native observation."""
    (repository / lock).write_text(text)
    observed = _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    payload = _invoke(repository)
    assert payload["verdict"] == "unknown"
    assert len(payload["checks"]) == 2
    assert len(observed) == 1


def test_python_workspace_source_must_be_a_mapping(repository, monkeypatch):
    """Malformed package entries cannot crash native-input accounting."""
    (repository / "uv.lock").write_text("package=[17]\n")
    _transport(monkeypatch, lambda _root, cmd, ecosystem: _result(cmd, ecosystem))
    payload = _invoke(repository)
    assert payload["verdict"] == "unknown"
    assert len(payload["checks"]) == 2
