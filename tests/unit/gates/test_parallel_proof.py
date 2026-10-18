"""Behavioral contracts for dependency-ready proof execution."""

from __future__ import annotations

import json
import threading
from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

import ethos.adapters.gates.runner as gate_runner
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.profile import repository_identity
from ethos.contracts.gates import Gate
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import execution_succeeded
from ethos.repository.policy.gates import ResolvedGatePolicy
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import declare_fixture_documentation_proof
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.proof import conformant_proof_checks
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.repo.proof_execution_carrier import ProofExecutionCarrier


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


def test_execution_carrier_rejects_policy_drift_before_running_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A matching source is insufficient when the execution policy differs."""
    repo = init_git_repo(tmp_path / "repo")
    nodes, registry = _graph({"a": ()}, execution_mode="subprocess", trust_bearing=True)
    plan = _proof_plan(repo, nodes)
    monkeypatch.setattr(
        proof_cli,
        "resolve_gate_policy",
        lambda *_args, **_kwargs: SimpleNamespace(
            gates=tuple(registry.values()), digest="different-policy"
        ),
    )
    monkeypatch.setattr(proof_cli, "LocalGateRunner", lambda: pytest.fail("gate ran"))
    carrier = cast("ProofExecutionCarrier", SimpleNamespace(recheck=lambda: None))
    with pytest.raises(ValueError, match=r"^proof_execution_environment_mismatch$"):
        proof_cli.run_plan_checks(repo=repo, plan=plan, execute=True, carrier=carrier)


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
        proof_cli,
        "resolve_gate_policy",
        lambda *_a, **_k: SimpleNamespace(gates=tuple(registry.values())),
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
        assert isinstance(check["started_after_seconds"], (int, float))
        assert isinstance(check["duration_seconds"], (int, float))
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
        def run(self, node, gate, *, root):
            assert gate.id == node.id
            assert root == tmp_path
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


@pytest.mark.parametrize("capacity", [1, 2, 4, 8])
def test_full_proof_overlaps_independent_install_and_test_branches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys, capacity: int
) -> None:
    """One declared wheel serves sibling checks without moving the final proof floor."""
    repo = init_git_repo(tmp_path / "repo")
    declaration = load_gate_registry_declaration()
    selected = declaration.proof_gates(full=True)
    policy = ResolvedGatePolicy(declaration, None, selected)
    plan = _proof_plan(repo, policy.nodes, policy)
    siblings = {"unit-architecture", "local-install-smoke"}
    started = threading.Barrier(2)

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert root == repo
            assert gate.id == node.id
            if capacity >= 4 and node.id in siblings:
                started.wait(timeout=2)
            return ActionRunResult(node.id, node.command, "pass", 0)

    monkeypatch.setattr(proof_cli, "resolve_gate_policy", lambda *_a, **_k: policy)
    monkeypatch.setattr(proof_cli, "LocalGateRunner", Runner)
    checks, passed = proof_cli.run_plan_checks(
        repo=repo, plan=plan, execute=True, capacity=capacity
    )
    assert passed is True
    assert [check["action_id"] for check in checks] == [node.id for node in policy.nodes]
    events = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    scheduled = {
        event["action_id"]: index
        for index, event in enumerate(events)
        if event["event"] == "gate_scheduled"
    }
    completed = {
        event["action_id"]: index
        for index, event in enumerate(events)
        if event["event"] == "gate_completed"
    }
    if capacity >= 4:
        assert max(scheduled[name] for name in siblings) < min(completed[name] for name in siblings)
    else:
        assert min(completed[name] for name in siblings) < max(scheduled[name] for name in siblings)
    assert completed["build"] < min(scheduled[name] for name in siblings)
    assert completed["dependency-vulnerabilities"] < scheduled["local-install-smoke"]
    assert max(completed[name] for name in siblings) < scheduled["generated-artifacts"]
    assert completed["unit-architecture"] < scheduled["coverage-floor"]
    assert "local-install-smoke" not in {gate.id for gate in declaration.proof_gates()}


@pytest.mark.parametrize("verdict", ["block", "unknown"])
@pytest.mark.parametrize(
    "failed_gate", ["unit-architecture", "coverage-floor", "local-install-smoke"]
)
def test_full_proof_requires_every_independent_acceptance_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, verdict: Verdict, failed_gate: str
) -> None:
    """Sibling execution cannot turn a failed or incomplete final obligation into PASS."""
    repo = init_git_repo(tmp_path / "repo")
    declaration = load_gate_registry_declaration()
    policy = ResolvedGatePolicy(declaration, None, declaration.proof_gates(full=True))
    plan = _proof_plan(repo, policy.nodes, policy)
    executed = []

    class Runner(gate_runner.LocalGateRunner):
        def run(self, node, gate, *, root):
            assert root == repo
            assert gate.id == node.id
            executed.append(node.id)
            exit_code = {"pass": 0, "block": 1, "unknown": None}[verdict]
            return ActionRunResult(
                node.id,
                node.command,
                verdict if node.id == failed_gate else "pass",
                exit_code if node.id == failed_gate else 0,
            )

    monkeypatch.setattr(proof_cli, "resolve_gate_policy", lambda *_a, **_k: policy)
    monkeypatch.setattr(proof_cli, "LocalGateRunner", Runner)
    checks, passed = proof_cli.run_plan_checks(repo=repo, plan=plan, execute=True, capacity=4)
    by_id = {check["action_id"]: check for check in checks}
    assert passed is False
    assert len(checks) == len(policy.nodes)
    assert by_id[failed_gate]["verdict"] == verdict
    assert "local-install-smoke" in executed
    assert by_id["local-install-smoke"]["verdict"] == (
        verdict if failed_gate == "local-install-smoke" else "pass"
    )
    if failed_gate == "unit-architecture":
        assert "coverage-floor" not in executed
        assert not execution_succeeded(by_id["coverage-floor"])


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
    assert isinstance(tests["diagnostics"], list)
    (diagnostic,) = tests["diagnostics"]
    assert diagnostic["kind"] == "gate_dependency"
    by_id = {check["action_id"]: check for check in checks}
    assert {key for key in executed if not execution_succeeded(by_id[key])} == {readiness_gate}
    expected = [
        f"gate_dependency_not_proven:{dependency}"
        for dependency in sorted(registry["unit-architecture"].depends_on)
        if not execution_succeeded(by_id[dependency])
    ]
    assert expected
    assert diagnostic["required_gaps"] == expected
    build = by_id["build"]
    assert isinstance(build["diagnostics"], list)
    (build_diagnostic,) = build["diagnostics"]
    assert build_diagnostic["kind"] == "gate_dependency"
    assert f"gate_dependency_not_proven:{readiness_gate}" in build_diagnostic["required_gaps"]
    assert registry["generated-artifacts"].providers == registry["repository-audit"].providers[1:]
    assert registry["generated-artifacts"].depends_on == (postexecution_dependency,)


@pytest.mark.parametrize("boundary", ["execution", "issuance"])
def test_bound_product_origin_rejects_recompiled_policy_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    """A self-consistent plan digest cannot change the owner's gate-selection provenance."""
    repo = init_git_repo(tmp_path / "repo")
    declare_fixture_documentation_proof(repo)
    head = commit_fixture(repo, "bind selected common source")
    policy = resolve_gate_policy(
        repo, tree_ref=head, gate_ids=("schemas",), product_gate_ids=("schemas",)
    )
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    altered = policy.projection | {"owner": {"kind": "forged"}}
    plan = compile_plan(
        None,
        Facts(
            repository=repository_identity(repo, tree_ref=head),
            head=head,
            tree=tree,
            observed_at=datetime.now(UTC),
            values={
                "gate_ids": policy.gate_ids,
                "execution_source": {"worktree": tree, "index": tree},
            },
        ),
        policy.nodes,
        policy=altered,
    )
    assert plan.inputs.policy == canonical_json_digest(altered)
    if boundary == "execution":
        monkeypatch.setattr(
            "ethos.surface.cli.root.proof.LocalGateRunner",
            lambda: pytest.fail("tampered source plan executed"),
        )
        with pytest.raises(ValueError, match="proof_execution_environment_mismatch"):
            proof_cli.run_plan_checks(repo=repo, plan=plan, execute=True)
    else:
        with pytest.raises(ValueError, match="proof_plan_binding_mismatch"):
            issue_proof_attestation(
                repo,
                {
                    "plan": plan,
                    "checks": conformant_proof_checks(plan),
                    "verdict": "pass",
                    "issuer": "agent:test:case:proof",
                    "scope": "quality",
                    "boundary": "focused",
                },
            )
