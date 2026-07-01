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
    assert report["mode"] == "product"
    assert report["schema_count"] >= 21
    assert report["required_gaps"] == []
    assert report["schemas"]["campaign-closeout.schema.json"]["ok"] is True
    assert report["instances"]["campaign-closeout-contract"]["ok"] is True
    assert report["instances"]["evolution-ledger"]["ok"] is True
    assert report["instances"]["docs-registry"]["ok"] is True
    assert report["instances"]["gate-registry"]["ok"] is True
    assert report["instances"]["shadow-parity-contract"]["ok"] is True
    assert report["instances"]["workspace-status-contract"]["ok"] is True


def test_schema_validation_report_uses_product_schemas_for_adopter_root(tmp_path) -> None:
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["mode"] == "adopter"
    assert report["ok"] is True
    assert report["schema_count"] >= 21
    assert report["required_gaps"] == []
    assert report["instances"]["docs-registry"]["ok"] is True


def test_schema_validation_adopter_partial_schemas_do_not_replace_product_contracts(
    tmp_path,
) -> None:
    schema_dir = tmp_path / "schemas" / "ethos"
    schema_dir.mkdir(parents=True)
    (schema_dir / "custom.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["mode"] == "adopter"
    assert report["ok"] is True
    assert report["schema_count"] >= 21
    assert report["instances"]["docs-registry"]["ok"] is True


def test_result_payload_validates_against_schema() -> None:
    result = EthosResult(command="status", ok=True, state="ready").to_dict()

    validation = validate_ethos_result(result)

    assert validation["ok"] is True
    json.dumps(validation)


def test_workspace_status_payload_validates_worktree_bindings() -> None:
    payload = {
        "root": "/repo",
        "branch": "dev",
        "dirty": False,
        "changed_paths": [],
        "role": "accepted_root",
        "candidate": {
            "branch": "candidate/dev",
            "exists": True,
            "head": "abc123",
            "worktree_exists": True,
            "worktree_path": "/repo-candidate-dev",
            "worktree_binding": "linked",
        },
        "worktrees": [
            {
                "path": "/repo",
                "head": "abc123",
                "branch": "dev",
                "role": "accepted_root",
                "worktree_binding": "current",
            },
            {
                "path": "/repo-candidate-dev",
                "head": "abc123",
                "branch": "candidate/dev",
                "role": "candidate",
                "worktree_binding": "linked",
            },
        ],
        "branch_bindings": [
            {
                "branch": "main",
                "role": "release_root",
                "head": "abc123",
                "worktree_path": "",
                "worktree_binding": "unbound",
            },
            {
                "branch": "dev",
                "role": "accepted_root",
                "head": "abc123",
                "worktree_path": "/repo",
                "worktree_binding": "current",
            },
            {
                "branch": "candidate/dev",
                "role": "candidate",
                "head": "abc123",
                "worktree_path": "/repo-candidate-dev",
                "worktree_binding": "linked",
            },
        ],
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "closeout_support": {
            "supported": False,
            "branch": "",
            "target_branch": "candidate/dev",
            "target_path": "/repo-candidate-dev",
            "operation": "",
            "owner": "",
            "required_gaps": ["protected_root_mutation"],
        },
        "required_gaps": [],
    }

    validation = validate_schema_instance("workspace-status.schema.json", payload)

    assert validation["ok"] is True
    json.dumps(validation)


def test_workspace_status_schema_rejects_ui_projection_fields() -> None:
    payload = {
        "root": "/repo",
        "branch": "dev",
        "dirty": False,
        "changed_paths": [],
        "role": "accepted_root",
        "candidate": {
            "branch": "candidate/dev",
            "exists": True,
            "head": "abc123",
            "worktree_exists": True,
            "worktree_path": "/repo-candidate-dev",
            "worktree_binding": "linked",
            "open_action": "open_worktree",
        },
        "worktrees": [],
        "branch_bindings": [
            {
                "branch": "main",
                "role": "release_root",
                "head": "abc123",
                "worktree_path": "",
                "worktree_binding": "unbound",
            },
            {
                "branch": "dev",
                "role": "accepted_root",
                "head": "abc123",
                "worktree_path": "/repo",
                "worktree_binding": "current",
            },
            {
                "branch": "candidate/dev",
                "role": "candidate",
                "head": "abc123",
                "worktree_path": "/repo-candidate-dev",
                "worktree_binding": "linked",
            }
        ],
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "closeout_support": {
            "supported": False,
            "branch": "",
            "target_branch": "candidate/dev",
            "target_path": "/repo-candidate-dev",
            "operation": "",
            "owner": "",
            "required_gaps": ["protected_root_mutation"],
        },
        "required_gaps": [],
    }

    validation = validate_schema_instance("workspace-status.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_schema_instance_validation_reports_data_gaps() -> None:
    validation = validate_schema_instance(
        "evolution-ledger.schema.json",
        {"hypothesis": [{"id": "x", "campaign": "c", "state": "active"}]},
    )

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_schema_validation_uses_product_schemas_for_adopter_without_local_schemas(
    tmp_path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "project.toml").write_text("[meta]\nname = 'sample'\n", encoding="utf-8")
    (tmp_path / "docs" / "current").mkdir(parents=True)
    (tmp_path / "docs" / "current" / "README.md").write_text(
        "---\nsubject: docs:current\nrole: reference\nstate: current\nrelations: test\n---\n"
        "# Current Docs\n",
        encoding="utf-8",
    )

    report = schema_validation_report(tmp_path)

    assert report["ok"] is True
    assert report["mode"] == "adopter"
    assert report["schema_count"] >= 19
    assert report["instances"]["docs-registry"]["ok"] is True


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
