from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.runner as gate_runner
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode

if TYPE_CHECKING:
    from pathlib import Path


def _command_case() -> tuple[PlanNode, Gate]:
    gate = Gate(id="gate", kind="test", command=("missing-tool", "--check"))
    return (
        PlanNode(id="gate", kind="check", command=gate_runner.gate_execution_identity(gate)),
        gate,
    )


def test_command_runner_surfaces_missing_command_and_nonzero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    node, gate = _command_case()
    monkeypatch.setattr(
        gate_runner.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            FileNotFoundError(2, "missing", "missing-tool")
        ),
    )
    missing = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)
    assert (missing.verdict, missing.exit_code) == ("block", 127)
    assert missing.diagnostics[0]["required_gaps"] == ["missing_command:missing-tool"]

    monkeypatch.setattr(
        gate_runner.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=7, stdout="partial output", stderr="quality failed"
        ),
    )
    failed = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)
    assert (failed.verdict, failed.exit_code, failed.stderr) == ("block", 7, "quality failed")


@pytest.mark.parametrize(
    ("exit_code", "stdout", "verdict", "gap"),
    [
        (1, "{}", "block", ""),
        (0, '{"value": 1}', "pass", ""),
        (
            0,
            '{"command":"prove","state":"done"}',
            "unknown",
            "ethos_result_verdict_missing_or_invalid",
        ),
        (
            0,
            (
                '{"command":"prove","verdict":"pass","state":"done",'
                '"diagnostics":[{"severity":"error","code":"gate_broken"}]}'
            ),
            "block",
            "ethos_result:error:gate_broken",
        ),
        (
            0,
            (
                '{"command":"ethos","verdict":"block","state":"gapped",'
                '"diagnostics":["skip",{"severity":"warning","code":"warn"}]}'
            ),
            "block",
            "ethos_result:warning:warn",
        ),
    ],
)
def test_command_runner_rejects_invalid_or_adverse_ethos_envelopes(
    exit_code: int, stdout: str, verdict: str, gap: str
) -> None:
    observed, diagnostics = gate_runner.classify_action_result(exit_code=exit_code, stdout=stdout)
    assert observed == verdict
    assert not gap or gap in diagnostics[0]["required_gaps"]


def test_proof_waves_refuse_invalid_capacity_and_unresolved_dependencies() -> None:
    gate = Gate(id="gate", kind="test", command=("check",))
    node = PlanNode(id="gate", kind="check", command=("check",), depends_on=("missing",))
    with pytest.raises(ValueError, match="proof_node_capacity_invalid"):
        gate_runner.proof_waves((node,), {"gate": gate}, capacity=0)
    with pytest.raises(ValueError, match="proof_plan_dependencies_unresolved"):
        gate_runner.proof_waves((node,), {"gate": gate}, capacity=1)


def test_proof_waves_isolate_writer_and_preserve_parallel_result_order(
    tmp_path: Path,
) -> None:
    nodes = (
        PlanNode(id="read-a", kind="check", command=("read-a",)),
        PlanNode(id="writer", kind="check", command=("writer",)),
        PlanNode(id="read-b", kind="check", command=("read-b",)),
    )
    gates = {
        "read-a": Gate(id="read-a", kind="test", command=("read-a",)),
        "writer": Gate(id="writer", kind="test", command=("writer",), writes_files=True),
        "read-b": Gate(id="read-b", kind="test", command=("read-b",)),
    }
    waves = gate_runner.proof_waves(nodes, gates, capacity=2)
    assert tuple(tuple(node.id for node in wave) for wave in waves) == (
        ("writer",),
        ("read-a", "read-b"),
    )

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node: PlanNode, gate: Gate, *, root: Path) -> gate_runner.ActionRunResult:
            assert root == tmp_path
            assert gate.id == node.id
            return gate_runner.ActionRunResult(node.id, node.command, "pass", 0)

    results = gate_runner.run_gate_waves(
        Runner(), nodes, gates, root=tmp_path, capacity=2, parallel=True
    )
    assert tuple(result.action_id for result in results) == ("writer", "read-a", "read-b")
    assert gate_runner.DryRunRunner().run(nodes[0], gates["read-a"], root=tmp_path).verdict == (
        "unknown"
    )


def test_provider_non_mapping_result_becomes_failed_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = Gate(id="gate", kind="test", providers=("ethos.fake:report",))
    node = PlanNode(id=gate.id, kind="check", command=("provider", *gate.providers))
    monkeypatch.setattr(
        gate_runner.importlib,
        "import_module",
        lambda _name: SimpleNamespace(report=lambda _root: "not-a-mapping"),
    )
    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)
    assert (result.verdict, result.diagnostics[0]["kind"]) == ("block", "gate_provider_error")


@pytest.mark.parametrize(
    ("prerequisite", "exit_code", "expected"),
    [
        ("pass", 0, ("pass", 0)),
        ("block", 1, ("block", None)),
        ("unknown", None, ("block", None)),
        ("pass", None, ("block", None)),
        ("pass", 7, ("block", None)),
        ("planned", None, ("unknown", None)),
    ],
)
def test_failed_dependency_never_executes_delivery(tmp_path, prerequisite, exit_code, expected):
    """Only passed prerequisites admit their dependent effects."""
    nodes = (
        PlanNode(id="coverage", kind="check", command=("coverage",)),
        PlanNode(id="delivery", kind="check", command=("delivery",), depends_on=("coverage",)),
        PlanNode(id="diagnostic", kind="check", command=("diagnostic",)),
    )
    gates = {node.id: Gate(id=node.id, kind="test", command=node.command) for node in nodes}
    executed = []

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert root == tmp_path
            assert gate.id == node.id
            executed.append(node.id)
            verdict = prerequisite if node.id == "coverage" else "pass"
            return gate_runner.ActionRunResult(
                node.id, node.command, verdict, exit_code if node.id == "coverage" else 0
            )

    planned = prerequisite == "planned"
    results = gate_runner.run_gate_waves(
        gate_runner.DryRunRunner() if planned else Runner(),
        nodes,
        gates,
        root=tmp_path,
        capacity=2,
        parallel=False,
    )
    assert executed == (
        []
        if planned
        else ["coverage", "diagnostic", "delivery"]
        if expected == ("pass", 0)
        else ["coverage", "diagnostic"]
    )
    assert {result.action_id for result in results} == {node.id for node in nodes}
    blocked = next(result for result in results if result.action_id == "delivery")
    assert (blocked.verdict, blocked.exit_code) == expected
    assert (
        not blocked.diagnostics
        if expected[0] != "block"
        else (blocked.diagnostics[0]["required_gaps"] == ["gate_dependency_not_proven:coverage"])
    )
