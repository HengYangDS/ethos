from __future__ import annotations

import threading
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import ethos.adapters.gates.runner as gate_runner
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.gates.runner import ActionRunResult
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_proof_waves_parallelize_only_independent_read_only_gates() -> None:
    nodes = (
        PlanNode(id="a", kind="check", command=("a",)),
        PlanNode(id="b", kind="check", command=("b",)),
        PlanNode(id="c", kind="check", command=("c",), depends_on=("a",)),
        PlanNode(id="write", kind="check", command=("write",)),
        PlanNode(id="d", kind="check", command=("d",), depends_on=("b",)),
    )
    gates = {
        node.id: Gate(
            id=node.id,
            kind="test",
            command=node.command,
            depends_on=node.depends_on,
            execution_mode="subprocess",
            writes_files=node.id == "write",
        )
        for node in nodes
    }

    assert gate_runner.proof_waves(nodes, gates, capacity=4) == (
        (nodes[3],),
        (nodes[0], nodes[1]),
        (nodes[2], nodes[4]),
    )


def test_proof_waves_are_deterministic_and_capacity_bounded() -> None:
    nodes = tuple(
        PlanNode(id=node_id, kind="check", command=(node_id,)) for node_id in ("c", "a", "b")
    )
    gates = {
        node.id: Gate(id=node.id, kind="test", command=node.command, execution_mode="subprocess")
        for node in nodes
    }

    assert gate_runner.proof_waves(nodes, gates, capacity=2) == (
        (nodes[0], nodes[1]),
        (nodes[2],),
    )


def test_run_plan_checks_executes_safe_wave_concurrently_in_plan_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    nodes = tuple(PlanNode(id=node_id, kind="check", command=(node_id,)) for node_id in ("a", "b"))
    commitment = commitment_fixture(
        id="repository:test", intent="Parallel proof.", subjects=("repository:test",)
    )
    plan = compile_plan(
        commitment,
        Facts(
            repository=commitment.id,
            head=head,
            tree=git(repo, "rev-parse", "HEAD^{tree}"),
            observed_at=datetime.now(UTC),
            values={},
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

    class Policy:
        pass

    policy = Policy()
    policy.registry = registry

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
