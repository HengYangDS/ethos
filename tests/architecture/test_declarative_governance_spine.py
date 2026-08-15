"""Runtime proof that declarative gate providers compile to one execution path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "gate_id",
    [
        "docs-registry",
        "evidence-freshness",
        "module-layout",
        "playbooks-v2",
        "product-boundary",
        "python-types",
        "repository-audit",
        "schemas",
    ],
)
def test_declarative_offline_provider_executes_through_the_shared_runner(
    gate_id: str,
) -> None:
    gate = load_gate_registry_declaration().registry("runtime")[gate_id]
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
