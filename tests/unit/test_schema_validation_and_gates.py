from __future__ import annotations

import json

from ethos_governance.gates import gate_graph, gate_registry
from ethos_governance.schema_validation import (
    schema_validation_report,
    validate_ethos_result,
    validate_schema_instance,
)
from ethos_kernel.result import EthosResult


def test_schema_validation_report_covers_all_ethos_schemas() -> None:
    report = schema_validation_report()

    assert report["ok"] is True
    assert report["schema_count"] >= 15
    assert report["required_gaps"] == []
    assert report["instances"]["evolution-ledger"]["ok"] is True
    assert report["instances"]["docs-registry"]["ok"] is True
    assert report["instances"]["gate-registry"]["ok"] is True


def test_result_payload_validates_against_schema() -> None:
    result = EthosResult(command="status", ok=True, state="ready").to_dict()

    validation = validate_ethos_result(result)

    assert validation["ok"] is True
    json.dumps(validation)


def test_schema_instance_validation_reports_data_gaps() -> None:
    validation = validate_schema_instance(
        "evolution-ledger.schema.json",
        {"hypothesis": [{"id": "x", "campaign": "c", "state": "active"}]},
    )

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_gate_registry_has_real_default_gates() -> None:
    registry = gate_registry()

    assert {"self-audit", "claims", "docs-registry", "schemas"} <= set(registry)
    assert registry["self-audit"].command[-4:] == ("audit", "--mode", "shape", "--json")
    assert {"unit-architecture", "ruff", "build"} <= set(registry)


def test_gate_graph_can_select_requested_gates() -> None:
    graph = gate_graph(("self-audit", "claims"))

    assert [node.id for node in graph.nodes] == ["self-audit", "claims"]
    assert graph.validate().ok is True


def test_full_gate_graph_includes_build_after_tests_and_lint() -> None:
    graph = gate_graph(full=True)
    nodes = {node.id: node for node in graph.nodes}

    assert "build" in nodes
    assert nodes["build"].depends_on == ("unit-architecture", "ruff")
