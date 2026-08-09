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
    ("stdout", "verdict", "gap"),
    [
        (
            '{"command":"prove","state":"done"}',
            "unknown",
            "ethos_result_verdict_missing_or_invalid",
        ),
        (
            (
                '{"command":"prove","verdict":"pass","state":"done",'
                '"diagnostics":[{"severity":"error","code":"gate_broken"}]}'
            ),
            "block",
            "ethos_result:error:gate_broken",
        ),
    ],
)
def test_command_runner_rejects_invalid_or_adverse_ethos_envelopes(
    stdout: str, verdict: str, gap: str
) -> None:
    observed, diagnostics = gate_runner.classify_action_result(exit_code=0, stdout=stdout)
    assert observed == verdict
    assert gap in diagnostics[0]["required_gaps"]


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

    class Runner:
        def run(self, node: PlanNode, _gate: Gate, *, root: Path) -> gate_runner.ActionRunResult:
            assert root == tmp_path
            return gate_runner.ActionRunResult(node.id, node.command, "pass", 0)

    results = gate_runner.run_gate_waves(
        Runner(), nodes, gates, root=tmp_path, capacity=2, parallel=True
    )
    assert tuple(result.action_id for result in results) == ("writer", "read-a", "read-b")
