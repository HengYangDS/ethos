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


def _graph(dependencies, *, writer="", resource_locks=None, **attributes):
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
            resource_locks=(resource_locks or {}).get(node.id),
            **attributes,
        )
        for node in nodes
    }


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
        def run(self, node, _gate, **_context):
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


@pytest.mark.parametrize("domain", [False, "output", None, "source/child", "source"])
@pytest.mark.parametrize(
    ("parallel", "capacity"), [(False, 1), (False, 4), (True, 1), (True, 2), (True, 4)]
)
def test_ready_child_does_not_wait_for_unrelated_slow_reader(
    tmp_path: Path, domain, parallel, capacity
) -> None:
    """Actual resource conflicts alone determine whether a ready child must wait."""
    started = threading.Barrier(2)
    progress = threading.Event()
    release_by = "queued" if domain in {None, "source/child", "source"} else "child"
    order = []
    concurrent = parallel and capacity > 1
    locks = {name: {"source/child": "shared"} for name in ("fast", "slow", "child", "queued")}
    if domain:
        locks["child"] = {str(domain): "exclusive"}
    nodes, gates = _graph(
        {"fast": (), "slow": (), "child": ("fast",), "queued": ("fast",)},
        writer="child" if domain is not False else "",
        resource_locks=locks if domain is not None else None,
    )

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, _gate, **_context):
            if concurrent and node.id in {"fast", "slow"}:
                started.wait(timeout=2)
            if concurrent and node.id == "slow":
                assert progress.wait(timeout=2)
            order.append(node.id)
            if node.id == release_by:
                progress.set()
            return ActionRunResult(node.id, node.command, "pass", 0)

    results = gate_runner.run_gate_graph(
        Runner(), nodes, gates, root=tmp_path, capacity=capacity, parallel=parallel
    )
    assert [result.action_id for result in results] == [node.id for node in nodes]
    assert not concurrent or order.index(release_by) < order.index("slow")
    assert not concurrent or release_by != "queued" or order.index("slow") < order.index("child")


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
    (diagnostic,) = tests["diagnostics"]
    assert diagnostic["kind"] == "gate_dependency"
    assert f"gate_dependency_not_proven:{readiness_gate}" in diagnostic["required_gaps"]
    assert registry["generated-artifacts"].providers == registry["repository-audit"].providers[1:]
    assert registry["generated-artifacts"].depends_on == (postexecution_dependency,)
