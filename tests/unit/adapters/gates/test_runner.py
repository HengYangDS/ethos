from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.gates.runner as gate_runner
from ethos.contracts.gates import GateDescriptor
from ethos.contracts.plan import PlanNode

if TYPE_CHECKING:
    from pathlib import Path

_NODE = PlanNode(id="gate", kind="check")


def _gate(*providers: str) -> GateDescriptor:
    return GateDescriptor(id="gate", kind="test", providers=providers)


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

    result = _runner(monkeypatch, success=success).run(
        _NODE, _gate("ethos.test:success"), root=tmp_path
    )

    assert (result.verdict, result.exit_code, seen) == ("pass", 0, [tmp_path])


def test_provider_failure_is_aggregated(monkeypatch, tmp_path: Path) -> None:
    result = _runner(monkeypatch, failed=lambda _: {"verdict": "block"}).run(
        _NODE, _gate("ethos.test:failed"), root=tmp_path
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

    result = _runner(monkeypatch, first=first, second=second).run(
        _NODE, _gate("ethos.test:first", "ethos.test:second"), root=tmp_path
    )

    assert calls == ["first", "second"]
    assert [item["provider"] for item in json.loads(result.stdout)["providers"]] == [
        "ethos.test:first",
        "ethos.test:second",
    ]


def test_provider_exception_becomes_failed_result(monkeypatch, tmp_path: Path) -> None:
    def broken(_: Path) -> dict[str, bool]:
        message = "boom"
        raise RuntimeError(message)

    result = _runner(monkeypatch, broken=broken).run(
        _NODE, _gate("ethos.test:broken"), root=tmp_path
    )

    assert (result.verdict, result.exit_code) == ("block", 1)
    assert result.diagnostics[0]["error"] == "RuntimeError: boom"


def test_provider_warning_blocks_but_info_diagnostic_does_not(monkeypatch, tmp_path: Path) -> None:
    warning = _runner(
        monkeypatch, warning=lambda _: {"verdict": "pass", "warnings": ["deprecated"]}
    )
    blocked = warning.run(_NODE, _gate("ethos.test:warning"), root=tmp_path)
    informed = _runner(
        monkeypatch,
        info=lambda _: {
            "verdict": "pass",
            "diagnostics": [{"severity": "info", "message": "note"}],
        },
    )

    passed = informed.run(_NODE, _gate("ethos.test:info"), root=tmp_path)

    assert blocked.verdict == "block"
    assert blocked.diagnostics[0]["required_gaps"] == [
        "gate_provider_warning:gate:ethos.test:warning:deprecated"
    ]
    assert passed.verdict == "pass"


def test_provider_missing_verdict_is_unknown_without_legacy_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    result = _runner(monkeypatch, legacy=lambda _: {"ok": True}).run(
        _NODE, _gate("ethos.test:legacy"), root=tmp_path
    )

    assert (result.verdict, result.exit_code) == ("unknown", 1)
    assert result.diagnostics[0]["required_gaps"] == [
        "gate_provider_unknown:gate:ethos.test:legacy"
    ]


def test_command_envelope_uses_verdict_and_plain_stderr_is_not_a_warning(tmp_path: Path) -> None:
    blocked = gate_runner.classify_action_result(
        exit_code=0,
        stdout=json.dumps({"command": "status", "verdict": "unknown", "state": "unknown"}),
    )
    passed = gate_runner.classify_action_result(exit_code=0, stdout="not-json")

    assert blocked[0] == "unknown"
    assert passed == ("pass", ())
