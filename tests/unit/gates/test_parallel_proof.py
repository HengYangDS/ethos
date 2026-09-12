"""Behavioral contracts for dependency-ready proof execution."""

from __future__ import annotations

import threading
from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.runner as gate_runner
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.gates.runner import ActionRunResult
from ethos.contracts.gates import Gate
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("parallel", [False, True])
@pytest.mark.parametrize("capacity", [1, 2, 4])
def test_graph_capacity_writer_exclusion_and_result_order(tmp_path, parallel, capacity):
    """Observed overlap, not a proposed wave, determines scheduling safety."""
    lock = threading.Lock()
    active = set()
    counts = []
    executed = []
    nodes = tuple(
        PlanNode(id=name, kind="check", command=(name,), depends_on=dependencies)
        for name, dependencies in (
            ("a", ()),
            ("b", ()),
            ("write", ("a",)),
            ("c", ("write",)),
            ("d", ("b",)),
        )
    )
    gates = {
        node.id: Gate(
            id=node.id, kind="test", command=node.command, writes_files=node.id == "write"
        )
        for node in nodes
    }

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert gate.id == node.id
            assert root == tmp_path
            with lock:
                assert "write" not in active
                assert node.id != "write" or not active
                active.add(node.id)
                counts.append(len(active))
                executed.append(node.id)
            with lock:
                active.remove(node.id)
            return ActionRunResult(node.id, node.command, "pass", 0)

    results = gate_runner.run_gate_graph(
        Runner(), nodes, gates, root=tmp_path, capacity=capacity, parallel=parallel
    )
    assert max(counts) <= (capacity if parallel else 1)
    assert set(executed) == {node.id for node in nodes}
    assert len(executed) == len(set(executed))
    assert executed.index("a") < executed.index("write") < executed.index("c")
    assert executed.index("b") < executed.index("d")
    assert [result.action_id for result in results] == [node.id for node in nodes]
    assert all(result.verdict == "pass" for result in results)


def test_run_plan_checks_executes_ready_checks_concurrently_in_plan_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    nodes = tuple(PlanNode(id=node_id, kind="check", command=(node_id,)) for node_id in ("a", "b"))
    commitment = commitment_fixture(id="repository:test", acceptance=("acceptance:fixture",))
    plan = compile_plan(
        commitment,
        Facts(
            repository=commitment.id,
            head=head,
            tree=tree,
            observed_at=datetime.now(UTC),
            values={"execution_source": {"worktree": tree, "index": tree}},
        ),
        nodes,
        policy={},
    )
    registry = {
        node.id: Gate(
            id=node.id,
            kind="test",
            command=node.command,
            execution_mode="subprocess",
            trust_bearing=True,
        )
        for node in nodes
    }
    barrier = threading.Barrier(2)

    policy = SimpleNamespace(registry=registry)

    class Runner:
        def run(self, node, _gate, *, root: Path):
            root.resolve(strict=True)
            barrier.wait(timeout=2)
            return ActionRunResult(node.id, node.command, "pass", 0)

    monkeypatch.setattr(proof_cli, "resolve_gate_policy", lambda *_a, **_k: policy)
    monkeypatch.setattr(proof_cli, "LocalGateRunner", Runner)

    checks, passed = proof_cli.run_plan_checks(repo=repo, plan=plan, execute=True, capacity=2)

    assert passed is True
    assert [check["action_id"] for check in checks] == ["a", "b"]


def test_ready_child_does_not_wait_for_unrelated_slow_reader(tmp_path: Path) -> None:
    """An independent slow reader must not create a global wave barrier."""
    started = threading.Barrier(2)
    child_started = threading.Event()
    observations = []
    nodes = (
        PlanNode(id="fast", kind="check", command=("fast",)),
        PlanNode(id="slow", kind="check", command=("slow",)),
        PlanNode(id="child", kind="check", command=("child",), depends_on=("fast",)),
    )
    gates = {node.id: Gate(id=node.id, kind="test", command=node.command) for node in nodes}

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert gate.id == node.id
            assert root == tmp_path
            if node.id in {"fast", "slow"}:
                started.wait(timeout=2)
            if node.id == "slow":
                observations.append(child_started.wait(timeout=1))
            if node.id == "child":
                child_started.set()
            return ActionRunResult(node.id, node.command, "pass", 0)

    results = gate_runner.run_gate_graph(
        Runner(), nodes, gates, root=tmp_path, capacity=2, parallel=True
    )
    assert observations == [True]
    assert [result.action_id for result in results] == [node.id for node in nodes]


@pytest.mark.parametrize("verdict", ["block", "unknown"])
@pytest.mark.parametrize("readiness_gate", ["ruff", "python-size", "source-budget"])
def test_public_proof_stops_heavy_work_after_readiness_failure(
    monkeypatch, tmp_path, verdict, readiness_gate
):
    """A real registry edge must stop the public proof transport before testing."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    declaration = load_gate_registry_declaration()
    selected = declaration.proof_gates(full=True)
    registry = {gate.id: gate for gate in selected}
    nodes = tuple(
        PlanNode(id=g.id, kind="check", command=gate_execution_identity(g), depends_on=g.depends_on)
        for g in selected
    )
    commitment = commitment_fixture(
        id="repository:readiness", acceptance=("no-heavy-after-failure",)
    )
    plan = compile_plan(
        commitment,
        Facts(
            repository=commitment.id,
            head=head,
            tree=tree,
            observed_at=datetime.now(UTC),
            values={"execution_source": {"worktree": tree, "index": tree}},
        ),
        nodes,
        policy={},
    )
    executed = []

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert gate.id == node.id
            assert root == repo
            executed.append(node.id)
            return ActionRunResult(
                node.id,
                node.command,
                verdict if node.id == readiness_gate else "pass",
                1 if node.id == readiness_gate else 0,
            )

    monkeypatch.setattr(
        proof_cli, "resolve_gate_policy", lambda *_a, **_k: SimpleNamespace(registry=registry)
    )
    monkeypatch.setattr(proof_cli, "LocalGateRunner", Runner)
    checks, passed = proof_cli.run_plan_checks(repo=repo, plan=plan, execute=True, capacity=2)
    assert passed is False
    assert "schemas" in executed
    assert not {"unit-architecture", "coverage-floor", "build", "local-install-smoke"}.intersection(
        executed
    )
    assert len(checks) == len(nodes)
    tests = next(check for check in checks if check["action_id"] == "unit-architecture")
    assert tests["exit_code"] is None
    assert tests["diagnostics"] == [
        {
            "kind": "gate_dependency",
            "required_gaps": [f"gate_dependency_not_proven:{readiness_gate}"],
        }
    ]


def test_ready_writer_waits_for_running_reader_and_precedes_queued_reader(tmp_path, monkeypatch):
    """Writer exclusion is tested while a reader is provably still active."""
    started = threading.Barrier(2)
    release = threading.Event()
    order = []
    nodes = (
        PlanNode(id="fast", kind="check", command=("fast",)),
        PlanNode(id="slow", kind="check", command=("slow",)),
        PlanNode(id="writer", kind="check", command=("writer",), depends_on=("fast",)),
        PlanNode(id="queued", kind="check", command=("queued",), depends_on=("fast",)),
    )
    gates = {
        node.id: Gate(
            id=node.id, kind="test", command=node.command, writes_files=node.id == "writer"
        )
        for node in nodes
    }

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert root == tmp_path
            assert gate.id == node.id
            if node.id in {"fast", "slow"}:
                started.wait(timeout=2)
            if node.id == "slow":
                assert release.wait(timeout=2)
            order.append(node.id)
            return ActionRunResult(node.id, node.command, "pass", 0)

    wait = gate_runner.wait

    def observe_drain(futures, **kwargs):
        if len(futures) == 1:
            release.set()
        return wait(futures, **kwargs)

    monkeypatch.setattr(gate_runner, "wait", observe_drain)
    try:
        result = gate_runner.run_gate_graph(
            Runner(), nodes, gates, root=tmp_path, capacity=2, parallel=True
        )
    finally:
        release.set()
    assert order.index("slow") < order.index("writer")
    assert order.index("writer") < order.index("queued")
    assert len(result) == len(nodes)
