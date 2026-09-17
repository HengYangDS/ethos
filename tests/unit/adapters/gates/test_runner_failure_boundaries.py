"""Gate failure, declaration and dependency execution boundaries."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.runner as gate_runner
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("boundary", ["nonzero", "missing", "denied"])
def test_command_runner_surfaces_missing_command_and_nonzero_exit(
    tmp_path: Path, boundary: str
) -> None:
    command = {
        "missing": (str(tmp_path / "missing-tool"),),
        "denied": (str(tmp_path),),
        "nonzero": (
            sys.executable,
            "-c",
            "import sys; print('output'); print('failure',file=sys.stderr); sys.exit(7)",
        ),
    }[boundary]
    gate = Gate(id="gate", kind="test", command=command)
    node = PlanNode(id=gate.id, kind="check", command=gate_runner.gate_execution_identity(gate))
    if boundary == "denied":
        with pytest.raises(gate_runner.ProcessExecutionError) as failure:
            gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)
        assert isinstance(failure.value.__cause__, PermissionError)
        return
    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)
    assert (result.verdict, result.exit_code) == ("block", 127 if boundary == "missing" else 7)
    if boundary == "missing":
        assert result.diagnostics[0]["required_gaps"] == [f"missing_command:{command[0]}"]
        assert result.diagnostics[0]["cwd"] == str(tmp_path)
    else:
        assert (result.stdout, result.stderr) == ("output\n", "failure\n")


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


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("capacity", "proof_node_capacity_invalid"),
        ("missing", "missing_dependency"),
        ("cycle", "cycle_detected"),
        ("duplicate", "duplicate_node_id"),
    ],
)
def test_gate_graph_rejects_invalid_plan_before_execution(tmp_path, case, message):
    gate = Gate(id="gate", kind="test", command=("check",))
    dependencies = ("missing",) if case == "missing" else ("gate",) if case == "cycle" else ()
    node = PlanNode(id="gate", kind="check", command=gate.command, depends_on=dependencies)
    nodes = (node, node) if case == "duplicate" else (node,)

    class Runner(gate_runner.LocalGateRunner):
        def run(self, *_args, **_kwargs):
            pytest.fail("an invalid plan executed a check")

    with pytest.raises(ValueError, match=message):
        gate_runner.run_gate_graph(
            Runner(),
            nodes,
            {"gate": gate},
            root=tmp_path,
            capacity=0 if case == "capacity" else 1,
            parallel=True,
        )


def test_gate_graph_prioritizes_exclusive_writer_and_returns_input_order(tmp_path: Path) -> None:
    nodes = tuple(
        PlanNode(id=name, kind="check", command=(name,)) for name in ("read-a", "writer", "read-b")
    )
    gates = {
        node.id: Gate(
            id=node.id, kind="test", command=node.command, writes_files=node.id == "writer"
        )
        for node in nodes
    }
    observed = []

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert root == tmp_path
            assert gate.id == node.id
            observed.append(node.id)
            return gate_runner.ActionRunResult(node.id, node.command, "pass", 0)

    results = gate_runner.run_gate_graph(
        Runner(), nodes, gates, root=tmp_path, capacity=2, parallel=True
    )
    assert observed[0] == "writer"
    assert tuple(result.action_id for result in results) == tuple(node.id for node in nodes)
    assert (
        gate_runner.DryRunRunner().run(nodes[0], gates["read-a"], root=tmp_path).verdict
        == "unknown"
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
    results = gate_runner.run_gate_graph(
        gate_runner.DryRunRunner() if planned else Runner(),
        nodes,
        gates,
        root=tmp_path,
        capacity=2,
        parallel=False,
    )
    assert executed == [
        node.id
        for node in nodes
        if not planned and (node.id != "delivery" or expected == ("pass", 0))
    ]
    assert {result.action_id for result in results} == {node.id for node in nodes}
    blocked = next(result for result in results if result.action_id == "delivery")
    assert (blocked.verdict, blocked.exit_code) == expected
    for result in results:
        if planned or (result.exit_code is None and result.action_id == "delivery"):
            assert result.started_after_seconds is result.duration_seconds is None
        else:
            assert result.started_after_seconds >= 0
            assert result.duration_seconds >= 0
    assert (
        not blocked.diagnostics
        if expected[0] != "block"
        else (blocked.diagnostics[0]["required_gaps"] == ["gate_dependency_not_proven:coverage"])
    )
