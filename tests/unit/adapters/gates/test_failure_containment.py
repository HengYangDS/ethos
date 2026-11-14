"""One failing provider or gate refuses only itself; every other gate keeps its evidence."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.runner as gate_runner
import ethos.adapters.gates.verification as gate_verification
from ethos.adapters.process import ProcessExecutionError
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode

if TYPE_CHECKING:
    from pathlib import Path

NODES = (
    PlanNode(id="crash", kind="check", command=("crash",)),
    PlanNode(id="dependent", kind="check", command=("dependent",), depends_on=("crash",)),
    PlanNode(id="independent", kind="check", command=("independent",)),
)
GATES = {node.id: Gate(id=node.id, kind="test", command=node.command) for node in NODES}
UNKNOWN = ProcessExecutionError("git_process_timed_out", reason="bound", verdict="unknown")


def _crashing(error: BaseException, base: type = gate_runner.LocalGateRunner) -> object:
    """Return a runner that raises `error` for the `crash` node and passes every other node."""

    def run(_self: object, node: PlanNode, _gate: Gate, *, root: Path) -> object:
        del root
        if node.id == "crash":
            raise error
        return gate_runner.ActionRunResult(node.id, node.command, "pass", 0)

    return type("Crashing", (base,), {"run": run})()


def _graph(runner: object, root: Path, *, parallel: bool = False) -> dict:
    results = gate_runner.run_gate_graph(
        runner, NODES, GATES, root=root, capacity=2, parallel=parallel
    )
    return {result.action_id: result for result in results}


@pytest.mark.parametrize("parallel", [False, True])
@pytest.mark.parametrize("error", [KeyError("lost"), ZeroDivisionError("zero"), LookupError("x")])
def test_a_crashing_gate_refuses_itself_and_the_graph_runs_on(
    tmp_path: Path, error: Exception, *, parallel: bool
) -> None:
    """The crash blocks its gate and its dependent; the independent gate still passes."""
    results = _graph(_crashing(error), tmp_path, parallel=parallel)

    crash = results["crash"]
    (cause,) = crash.diagnostics
    assert (crash.verdict, crash.exit_code, cause["kind"]) == ("block", 1, "gate_runner_error")
    assert cause["required_gaps"] == ["gate_runner_error:crash"]
    assert cause["error"].startswith(type(error).__name__)
    assert cause["frame"].endswith(" in run")
    (held,) = results["dependent"].diagnostics
    assert held["required_gaps"] == ["gate_dependency_not_proven:crash"]
    assert results["independent"].verdict == "pass"


@pytest.mark.parametrize(
    ("error", "gaps"),
    [
        (UNKNOWN, ["gate_runner_error:crash", "git_process_timed_out"]),
        (subprocess.TimeoutExpired("crash", 1), ["gate_timeout:crash"]),
    ],
)
def test_a_contained_failure_keeps_its_verdict_class(
    tmp_path: Path, error: Exception, gaps: list[str]
) -> None:
    """A decision the error carries survives the seam, and the dependent inherits its class."""
    results = _graph(_crashing(error), tmp_path)

    assert results["crash"].verdict == "unknown"
    (cause,) = results["crash"].diagnostics
    assert cause["required_gaps"] == gaps
    assert results["dependent"].verdict == "unknown"
    if isinstance(error, ProcessExecutionError):
        assert cause["process_failure"]["code"] == "git_process_timed_out"
    else:
        assert cause["command"] == ["crash"]


def test_a_failing_preview_reads_as_blocked_not_planned(tmp_path: Path) -> None:
    """A contained preview failure keeps an exit code, so it never reads as a planned check."""
    results = _graph(_crashing(KeyError("lost"), gate_runner.DryRunRunner), tmp_path)

    assert (results["crash"].verdict, results["crash"].exit_code) == ("block", 1)
    assert (results["independent"].verdict, results["independent"].exit_code) == ("pass", 0)


def test_an_interrupt_still_stops_the_whole_run(tmp_path: Path) -> None:
    """Preservation, passing before the seam existed: an interrupt is no gate's failure."""
    with pytest.raises(KeyboardInterrupt):
        _graph(_crashing(KeyboardInterrupt()), tmp_path)


def test_a_provider_decision_keeps_its_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A provider's unknown process failure stays unknown, with the provider's gap first."""

    def report(_root: Path) -> dict[str, object]:
        raise UNKNOWN

    monkeypatch.setattr(gate_verification, "provider_target", str)
    monkeypatch.setattr(
        gate_verification.importlib, "import_module", lambda _: SimpleNamespace(report=report)
    )
    gate = Gate(id="lookup", kind="test", providers=("ethos.test:report",))
    node = PlanNode(id=gate.id, kind="check", command=gate_runner.gate_execution_identity(gate))

    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)

    assert result.verdict == "unknown"
    assert result.diagnostics[0]["required_gaps"] == [
        "gate_provider_error:lookup:ethos.test:report",
        "git_process_timed_out",
    ]
