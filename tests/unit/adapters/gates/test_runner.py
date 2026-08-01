from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.gates.runner as gate_runner
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode

if TYPE_CHECKING:
    from pathlib import Path


def _gate(*providers: str) -> Gate:
    return Gate(id="gate", kind="test", providers=providers)


def _node(gate: Gate) -> PlanNode:
    return PlanNode(id=gate.id, kind="check", command=("provider", *gate.providers))


def _runner(monkeypatch, **providers: object) -> gate_runner.LocalGateRunner:
    monkeypatch.setattr(
        gate_runner.importlib, "import_module", lambda _: SimpleNamespace(**providers)
    )
    return gate_runner.LocalGateRunner()


def test_provider_success_runs_directly(monkeypatch, tmp_path: Path) -> None:
    seen: list[Path] = []

    def success(root: Path) -> dict[str, bool]:
        seen.append(root)
        return {"verdict": "pass"}

    gate = _gate("ethos.test:success")
    result = _runner(monkeypatch, success=success).run(_node(gate), gate, root=tmp_path)

    assert (result.verdict, result.exit_code, seen) == ("pass", 0, [tmp_path])


def test_runner_rejects_gate_identity_drift(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        gate_runner.subprocess,
        "run",
        lambda command, **_: (
            calls.append(tuple(command)) or SimpleNamespace(returncode=0, stdout="", stderr="")
        ),
    )
    node = PlanNode(id="gate", kind="check", command=("old-check",))
    gate = Gate(id="gate", kind="test", command=("new-check",))

    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)

    assert calls == []
    assert result.verdict == "block"
    assert result.exit_code == 1
    assert result.diagnostics[0]["required_gaps"] == ["gate_execution_identity_mismatch:gate"]


def test_command_gate_executes_declared_python_not_ambient_canonical_identity(
    monkeypatch, tmp_path: Path
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "hijacked"
    fake_python = fake_bin / "python"
    fake_python.write_text(
        f"#!/bin/sh\nprintf hijacked > {marker}\nexit 91\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    monkeypatch.setenv("PATH", fake_bin.as_posix())
    gate = Gate(
        id="gate",
        kind="test",
        command=(sys.executable, "-c", "print('trusted')"),
    )
    node = PlanNode(
        id=gate.id,
        kind="check",
        command=gate_runner.gate_execution_identity(gate),
    )

    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)

    assert result.verdict == "pass"
    assert result.stdout == "trusted\n"
    assert not marker.exists()


def test_provider_failure_is_aggregated(monkeypatch, tmp_path: Path) -> None:
    gate = _gate("ethos.test:failed")
    result = _runner(monkeypatch, failed=lambda _: {"verdict": "block"}).run(
        _node(gate), gate, root=tmp_path
    )

    assert (result.verdict, result.exit_code) == ("block", 1)
    assert result.diagnostics[0]["required_gaps"] == [
        "gate_provider_blocked:gate:ethos.test:failed"
    ]


def test_providers_are_aggregated_in_declaration_order(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def first(_: Path) -> dict[str, bool]:
        calls.append("first")
        return {"verdict": "pass"}

    def second(_: Path) -> dict[str, bool]:
        calls.append("second")
        return {"verdict": "pass"}

    gate = _gate("ethos.test:first", "ethos.test:second")
    result = _runner(monkeypatch, first=first, second=second).run(_node(gate), gate, root=tmp_path)

    assert calls == ["first", "second"]
    assert [item["provider"] for item in json.loads(result.stdout)["providers"]] == [
        "ethos.test:first",
        "ethos.test:second",
    ]


def test_provider_exception_becomes_failed_result(monkeypatch, tmp_path: Path) -> None:
    def broken(_: Path) -> dict[str, bool]:
        message = "boom"
        raise RuntimeError(message)

    gate = _gate("ethos.test:broken")
    result = _runner(monkeypatch, broken=broken).run(_node(gate), gate, root=tmp_path)

    assert (result.verdict, result.exit_code) == ("block", 1)
    assert result.diagnostics[0]["error"] == "RuntimeError: boom"


def test_provider_warning_blocks_but_info_diagnostic_does_not(monkeypatch, tmp_path: Path) -> None:
    warning = _runner(
        monkeypatch, warning=lambda _: {"verdict": "pass", "warnings": ["deprecated"]}
    )
    warning_gate = _gate("ethos.test:warning")
    blocked = warning.run(_node(warning_gate), warning_gate, root=tmp_path)
    informed = _runner(
        monkeypatch,
        info=lambda _: {
            "verdict": "pass",
            "diagnostics": [{"severity": "info", "message": "note"}],
        },
    )

    info_gate = _gate("ethos.test:info")
    passed = informed.run(_node(info_gate), info_gate, root=tmp_path)

    assert blocked.verdict == "block"
    assert blocked.diagnostics[0]["required_gaps"] == [
        "gate_provider_warning:gate:ethos.test:warning:deprecated"
    ]
    assert passed.verdict == "pass"


def test_provider_missing_verdict_is_unknown_without_legacy_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    gate = _gate("ethos.test:legacy")
    result = _runner(monkeypatch, legacy=lambda _: {"ok": True}).run(
        _node(gate), gate, root=tmp_path
    )

    assert (result.verdict, result.exit_code) == ("unknown", 1)
    assert result.diagnostics[0]["required_gaps"] == [
        "gate_provider_unknown:gate:ethos.test:legacy"
    ]


def test_command_envelope_uses_verdict_and_plain_stderr_is_not_a_warning() -> None:
    blocked = gate_runner.classify_action_result(
        exit_code=0,
        stdout=json.dumps({"command": "status", "verdict": "unknown", "state": "unknown"}),
    )
    passed = gate_runner.classify_action_result(exit_code=0, stdout="not-json")

    assert blocked[0] == "unknown"
    assert passed == ("pass", ())
