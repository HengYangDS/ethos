"""`ethos prove --readiness` runs the full plan's readiness tier alone and proves nothing more."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.application.proof.host as host
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.gates.runner import readiness_tier
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tracked_head
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import init_git_repo


def _graph() -> tuple[tuple[PlanNode, ...], dict[str, Gate]]:
    """A readiness gate and a test gate, so the tier holds lint and leaves the test gate out."""
    nodes = (
        PlanNode(id="lint", kind="check", command=("lint",)),
        PlanNode(id="tests", kind="check", command=("tests",)),
    )
    registry = {
        "lint": Gate(id="lint", kind="check", command=("lint",), trust_bearing=True),
        "tests": Gate(id="tests", kind="test", command=("tests",), trust_bearing=True),
    }
    return nodes, registry


@pytest.mark.parametrize("lint", ["pass", "block"])
def test_the_readiness_run_executes_only_the_tier_and_names_the_rest_not_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lint: str
) -> None:
    """Lint runs; the test gate is reported as not run; nothing is attested."""
    repo = init_git_repo(tmp_path / "repo")
    nodes, registry = _graph()
    executed: list[str] = []

    class Runner:
        def __init__(self, **_options) -> None:
            pass

        def run(self, node, _gate, **_context):
            executed.append(node.id)
            verdict = lint if node.id == "lint" else "pass"
            return ActionRunResult(node.id, node.command, verdict, 0 if verdict == "pass" else 1)

    full = SimpleNamespace(nodes=nodes, registry=registry, gaps=(), digest="d")
    monkeypatch.setattr(host, "resolve_gate_policy", lambda *_a, **_k: full)
    monkeypatch.setattr(host, "LocalGateRunner", Runner)
    monkeypatch.setattr(
        host, "observe_execution_source", lambda *_a: {"worktree": "t", "index": "t"}
    )
    monkeypatch.setattr(host, "current_tree", lambda *_a: "t")

    result = host.readiness_observation(repo=repo, expect_head=None)

    assert executed == ["lint"]
    assert result.verdict == lint
    assert list(result.summary["not_run"]) == ["tests"]
    assert result.summary["proof_attestation_issued"] is False
    assert result.data["attestation"] == {}
    assert [check["action_id"] for check in result.data["checks"]] == ["lint"]


def test_the_readiness_mode_refuses_a_selection_or_a_dry_run(tmp_path: Path) -> None:
    """The readiness run always uses the full plan and executes; any narrowing refuses."""
    repo = init_git_repo(tmp_path / "repo")
    for extra in (("--execute", "--gate", "lint"), ("--execute", "--host"), ()):
        result = run_ethos_blocked("prove", "--readiness", *extra, "--json", cwd=repo)
        assert "proof_readiness_options_invalid" in result["required_gaps"]


def test_a_readiness_run_owes_no_test_bound_obligation_of_the_real_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ETHOS maps behavior to a test gate; its readiness run must not owe that obligation.

    A readiness run once re-resolved its tier as a selection, which refused at once with
    `quality_obligation_unproven:behavior` on this repository and ran nothing. Here the real
    committed gate policy, tier and obligation checks run; only the gates and the source binding,
    which a working checkout under test cannot hold still, are replaced.
    """
    root = Path(__file__).resolve().parents[3]
    head = current_tracked_head(root)
    full = resolve_gate_policy(root, tree_ref=head, full=True)
    tier = set(readiness_tier(full.nodes, full.registry))
    executed: list[str] = []

    class Runner:
        def __init__(self, **_options) -> None:
            pass

        def run(self, node, _gate, **_context):
            executed.append(node.id)
            return ActionRunResult(node.id, node.command, "pass", 0)

    monkeypatch.setattr(host, "LocalGateRunner", Runner)
    monkeypatch.setattr(
        host, "observe_execution_source", lambda *_a: {"worktree": "t", "index": "t"}
    )
    monkeypatch.setattr(host, "current_tree", lambda *_a: "t")
    result = host.readiness_observation(repo=root, expect_head=head)

    assert not any(gap.startswith("quality_obligation_unproven") for gap in result.required_gaps)
    assert set(executed) == tier
    assert set(result.summary["not_run"]) == {node.id for node in full.nodes} - tier
