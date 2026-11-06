"""`ethos prove --readiness` runs the full plan's readiness tier alone and proves nothing more."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.runner as runner
from ethos.adapters.gates.runner import ActionRunResult
from ethos.surface.cli.proof import host
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import init_git_repo
from tests.unit.gates.test_parallel_proof import _graph

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("lint", ["pass", "block"])
def test_the_readiness_run_executes_only_the_tier_and_names_the_rest_not_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lint: str
) -> None:
    """Lint runs; the test gate is reported as not run; nothing is attested."""
    repo = init_git_repo(tmp_path / "repo")
    nodes, registry = _graph({"lint": (), "tests": ()}, trust_bearing=True)
    registry["lint"] = registry["lint"].model_copy(update={"kind": "check"})
    executed: list[str] = []

    class Runner:
        def __init__(self, **_options) -> None:
            pass

        def run(self, node, _gate, **_context):
            executed.append(node.id)
            verdict = lint if node.id == "lint" else "pass"
            return ActionRunResult(node.id, node.command, verdict, 0 if verdict == "pass" else 1)

    full = SimpleNamespace(nodes=nodes, registry=registry)
    selected = SimpleNamespace(
        nodes=nodes[:1], registry=registry, gaps=(), digest="d", result_gaps=lambda *_a, **_k: ()
    )
    monkeypatch.setattr(host, "resolve_gate_policy", lambda *_a, **_k: full)
    monkeypatch.setattr(runner, "resolve_gate_policy", lambda *_a, **_k: selected)
    monkeypatch.setattr(runner, "LocalGateRunner", Runner)
    monkeypatch.setattr(runner, "observe_execution_source", lambda *_a: {"tree": "t"})
    monkeypatch.setattr(runner, "execution_source_gaps", lambda *_a: [])

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
