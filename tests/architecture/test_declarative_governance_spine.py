"""Runtime proof that declarative gate providers compile to one execution path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.registries import proof_registry

ROOT = Path(__file__).resolve().parents[2]


def test_proof_floor_has_no_workspace_history_precondition() -> None:
    """Current proof is independent of a historical directory layout."""
    assert "evidence-freshness" not in proof_registry()
    assert not (ROOT / "evidence").exists()
    assert not (ROOT / "docs/evidence").exists()


@pytest.mark.parametrize(
    "gate_id",
    [
        "docs-registry",
        "module-layout",
        "skills",
        "product-boundary",
        "python-types",
        "repository-audit",
        "schemas",
    ],
)
def test_declarative_offline_provider_executes_through_the_shared_runner(
    gate_id: str,
) -> None:
    gate = proof_registry()[gate_id]
    assert gate.providers
    assert gate.network_policy == "offline"
    assert gate.writes_files is False

    result = LocalGateRunner().run(
        PlanNode(
            id=gate.id,
            kind="check",
            command=gate_execution_identity(gate),
            depends_on=gate.depends_on,
        ),
        gate,
        root=ROOT,
    )
    payload = json.loads(result.stdout)

    assert payload["gate"] == gate_id
    assert [item["provider"] for item in payload["providers"]] == list(gate.providers)
    assert result.verdict == payload["verdict"]
    assert result.exit_code == (0 if payload["verdict"] == "pass" else 1)
