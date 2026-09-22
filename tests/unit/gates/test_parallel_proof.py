"""Behavioral contracts for dependency-ready proof execution."""

from __future__ import annotations

import json
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
from ethos.repository.policy.gates import ResolvedGatePolicy
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _proof_plan(repo, nodes, policy=None):
    """Bind a test graph to its actual immutable repository subject."""
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    commitment = commitment_fixture(id="repository:test", acceptance=("acceptance:fixture",))
    return compile_plan(
        commitment,
        Facts(
            repository=commitment.id,
            head=git(repo, "rev-parse", "HEAD"),
            tree=tree,
            observed_at=datetime.now(UTC),
            values={
                "execution_source": {"worktree": tree, "index": tree},
                **({"gate_ids": tuple(node.id for node in nodes)} if policy else {}),
            },
        ),
        nodes,
        policy=policy.projection if policy else {},
    )


def _graph(dependencies, *, writer="", **attributes):
    """Compile each test's explicit topology into consistent node and gate declarations."""
    nodes = tuple(
        PlanNode(id=name, kind="check", command=(name,), depends_on=parents)
        for name, parents in dependencies.items()
    )
    return nodes, {
        node.id: Gate(
            id=node.id,
            kind="test",
            command=node.command,
            writes_files=node.id == writer,
            **attributes,
        )
        for node in nodes
    }


@pytest.mark.parametrize("parallel", [False, True])
@pytest.mark.parametrize("capacity", [1, 2, 4])
@pytest.mark.parametrize("writer_ready", [False, True])
def test_graph_capacity_writer_exclusion_and_result_order(
    tmp_path, parallel, capacity, writer_ready
):
    """Observed overlap, not a proposed wave, determines scheduling safety."""
    lock = threading.Lock()
    active = set()
    counts = []
    executed = []
    nodes, gates = _graph(
        {"a": (), "b": (), "write": () if writer_ready else ("a",), "c": ("write",), "d": ("b",)},
        writer="write",
    )

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
    assert sorted(executed) == sorted(gates)
    assert executed[0] == "write" if writer_ready else executed.index("a") < executed.index("write")
    assert executed.index("write") < executed.index("c")
    assert executed.index("b") < executed.index("d")
    assert [result.action_id for result in results] == [node.id for node in nodes]
    assert all(result.verdict == "pass" for result in results)


@pytest.mark.parametrize("mode", ["parallel", "interrupted", "dry-run"])
def test_run_plan_checks_executes_ready_checks_concurrently_in_plan_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, mode: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    nodes, registry = _graph(
        {"a": (), "b": ("a",) if mode == "interrupted" else ()},
        execution_mode="subprocess",
        trust_bearing=True,
    )
    plan = _proof_plan(repo, nodes)
    barrier = threading.Barrier(2)

    class Runner:
        def run(self, node, _gate, *, root: Path):
            root.resolve(strict=True)
            if mode == "parallel":
                barrier.wait(timeout=2)
            if mode == "interrupted" and node.id == "b":
                message = "late gate did not complete"
                raise TimeoutError(message)
            return ActionRunResult(node.id, node.command, "pass", 0)

    monkeypatch.setattr(
        proof_cli, "resolve_gate_policy", lambda *_a, **_k: SimpleNamespace(registry=registry)
    )
    monkeypatch.setattr(proof_cli, "LocalGateRunner", Runner)

    if mode == "interrupted":
        with pytest.raises(TimeoutError, match="late gate"):
            proof_cli.run_plan_checks(repo=repo, plan=plan, execute=True, capacity=2)
    else:
        checks, passed = proof_cli.run_plan_checks(
            repo=repo, plan=plan, execute=mode != "dry-run", capacity=2
        )
        assert passed is True
        assert [check["action_id"] for check in checks] == ["a", "b"]
    captured = capsys.readouterr()
    assert captured.out == ""
    events = [json.loads(line) for line in captured.err.splitlines()]
    if mode == "dry-run":
        assert not events
        assert all(check["verdict"] == "unknown" for check in checks)
        assert all(check["duration_seconds"] is None for check in checks)
        return
    assert all(
        event["head"] == plan.facts["head"]
        and event["plan_digest"] == plan.digest
        and event["satisfies_repository_proof"] is False
        for event in events
    )
    finished = [event for event in events if event["event"] == "gate_completed"]
    assert {event["action_id"] for event in finished} == (
        {"a"} if mode == "interrupted" else {"a", "b"}
    )
    assert {event["action_id"] for event in events if event["event"] == "gate_scheduled"} == {
        "a",
        "b",
    }
    assert all(event["verdict"] == "pass" and event["duration_seconds"] >= 0 for event in finished)
    if mode == "interrupted":
        assert [event["event"] for event in events] == [
            "gate_scheduled",
            "gate_completed",
            "gate_scheduled",
        ]
        return

    for check in checks:
        assert check["started_after_seconds"] >= 0
        assert check["duration_seconds"] >= 0


def test_ready_child_does_not_wait_for_unrelated_slow_reader(tmp_path: Path) -> None:
    """An independent slow reader must not create a global wave barrier."""
    started = threading.Barrier(2)
    child_started = threading.Event()
    observations = []
    nodes, gates = _graph({"fast": (), "slow": (), "child": ("fast",)})

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
@pytest.mark.parametrize(
    ("execution_kind", "postexecution_dependency"),
    [("test", "unit-architecture"), ("package", "coverage-floor")],
)
@pytest.mark.parametrize(
    "readiness_gate",
    [
        gate.id
        for gate in load_gate_registry_declaration().proof_gates(full=True)
        if gate.kind not in {"test", "package"} and "unit-architecture" not in gate.depends_on
    ],
)
def test_public_proof_stops_heavy_work_after_readiness_failure(
    monkeypatch, tmp_path, verdict, readiness_gate, execution_kind, postexecution_dependency
):
    """Selected source failures stop public proof without expanding its scope."""
    repo = init_git_repo(tmp_path / "repo")
    declaration = load_gate_registry_declaration()
    selected = tuple(
        gate.model_copy(update={"kind": execution_kind})
        if gate.id == "unit-architecture"
        else gate.model_copy(update={"depends_on": (postexecution_dependency,)})
        if gate.id == "generated-artifacts"
        else gate
        for gate in declaration.proof_gates(full=True)
    )
    declaration = declaration.model_copy(update={"gates": selected})
    policy = ResolvedGatePolicy(declaration, None, selected)
    registry = policy.registry
    nodes = policy.nodes
    plan = _proof_plan(repo, nodes, policy)
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

    monkeypatch.setattr(proof_cli, "resolve_gate_policy", lambda *_a, **_k: policy)
    monkeypatch.setattr(proof_cli, "LocalGateRunner", Runner)
    checks, passed = proof_cli.run_plan_checks(repo=repo, plan=plan, execute=True, capacity=2)
    assert passed is False
    assert readiness_gate in executed
    assert not {"unit-architecture", "coverage-floor", "build", "local-install-smoke"}.intersection(
        executed
    )
    assert len(checks) == len(nodes)
    tests = next(check for check in checks if check["action_id"] == "unit-architecture")
    assert tests["exit_code"] is None
    assert len(tests["diagnostics"]) == 1
    assert tests["diagnostics"][0]["kind"] == "gate_dependency"
    assert (
        f"gate_dependency_not_proven:{readiness_gate}" in tests["diagnostics"][0]["required_gaps"]
    )
    assert registry["generated-artifacts"].providers == registry["repository-audit"].providers[1:]
    assert registry["generated-artifacts"].depends_on == (postexecution_dependency,)


def test_ready_writer_waits_for_running_reader_and_precedes_queued_reader(tmp_path, monkeypatch):
    """Writer exclusion is tested while a reader is provably still active."""
    started = threading.Barrier(2)
    release = threading.Event()
    order = []
    nodes, gates = _graph(
        {"fast": (), "slow": (), "writer": ("fast",), "queued": ("fast",)}, writer="writer"
    )

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
