from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

from ethos.adapters.gates import runner
from ethos.contracts.gates import GateDescriptor
from ethos.contracts.plan import PlanNode

if TYPE_CHECKING:
    from pathlib import Path

_NODE = PlanNode(id="gate", kind="check")


def _gate(*providers: str) -> GateDescriptor:
    return GateDescriptor(id="gate", kind="test", providers=providers)


def _runner(monkeypatch, **providers: object) -> runner.LocalGateRunner:
    monkeypatch.setattr(runner.importlib, "import_module", lambda _: SimpleNamespace(**providers))
    return runner.LocalGateRunner()


def test_provider_success_runs_directly(monkeypatch, tmp_path: Path) -> None:
    seen: list[Path] = []

    def success(root: Path) -> dict[str, bool]:
        seen.append(root)
        return {"ok": True}

    result = _runner(monkeypatch, success=success).run(
        _NODE, _gate("ethos.test:success"), root=tmp_path
    )

    assert (result.state, result.exit_code, seen) == ("passed", 0, [tmp_path])


def test_provider_failure_is_aggregated(monkeypatch, tmp_path: Path) -> None:
    result = _runner(monkeypatch, failed=lambda _: {"ok": False}).run(
        _NODE, _gate("ethos.test:failed"), root=tmp_path
    )

    assert (result.state, result.exit_code) == ("failed", 1)
    assert result.diagnostics[0]["required_gaps"] == [
        "gate_provider_blocked:gate:ethos.test:failed"
    ]


def test_providers_are_aggregated_in_declaration_order(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def first(_: Path) -> dict[str, bool]:
        calls.append("first")
        return {"ok": True}

    def second(_: Path) -> dict[str, bool]:
        calls.append("second")
        return {"ok": True}

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

    assert (result.state, result.exit_code) == ("failed", 1)
    assert result.diagnostics[0]["error"] == "RuntimeError: boom"
