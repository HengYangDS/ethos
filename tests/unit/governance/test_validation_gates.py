from __future__ import annotations

import json
from pathlib import Path

from ethos.repository.policy.coupling import coupling_audit_report
from ethos.repository.policy.gates import gate_graph
from ethos.repository.policy.gates import gate_registry
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.policy.schema import validate_ethos_result
from ethos.repository.policy.schema import validate_schema_instance
from ethos_core.result import EthosResult

ROLE_POLICY_SAMPLE = {
    "release_branch": "main",
    "accepted_branch": "dev",
    "candidate_branch": "candidate/dev",
    "work_branch_prefix": "work/",
    "submit_branch_prefix": "submit/",
    "semantic_order": [
        {
            "role": "release_root",
            "kind": "exact_branch",
            "config_key": "release_branch",
            "pattern": "main",
        },
        {
            "role": "accepted_root",
            "kind": "exact_branch",
            "config_key": "accepted_branch",
            "pattern": "dev",
        },
        {
            "role": "candidate",
            "kind": "exact_branch",
            "config_key": "candidate_branch",
            "pattern": "candidate/dev",
        },
        {
            "role": "work_lane",
            "kind": "branch_prefix",
            "config_key": "work_branch_prefix",
            "pattern": "work/*",
        },
        {
            "role": "submit_lane",
            "kind": "branch_prefix",
            "config_key": "submit_branch_prefix",
            "pattern": "submit/*",
        },
    ],
}


def test_schema_validation_report_covers_all_ethos_schemas() -> None:
    report = schema_validation_report()

    assert report["ok"] is True
    assert report["mode"] == "product"
    assert report["schema_count"] >= 30
    assert report["required_gaps"] == []
    assert report["schemas"]["quality-asset.schema.json"]["ok"] is True
    assert report["schemas"]["quality-finding.schema.json"]["ok"] is True
    assert report["schemas"]["quality-gate-plan.schema.json"]["ok"] is True
    assert report["schemas"]["quality-profile.schema.json"]["ok"] is True
    assert report["schemas"]["review-record.schema.json"]["ok"] is True
    assert report["schemas"]["host-capability.schema.json"]["ok"] is True
    assert report["schemas"]["campaign-closeout.schema.json"]["ok"] is True
    assert report["schemas"]["trust-envelope.schema.json"]["ok"] is True
    assert report["schemas"]["promotion-target.schema.json"]["ok"] is True
    assert report["schemas"]["capability-profile.schema.json"]["ok"] is True
    assert report["schemas"]["skill-activation.schema.json"]["ok"] is True
    assert report["schemas"]["skill-registry.schema.json"]["ok"] is True
    assert report["schemas"]["skill-package-manifest.schema.json"]["ok"] is True
    assert report["instances"]["campaign-closeout-contract"]["ok"] is True
    assert report["instances"]["trust-envelope-contract"]["ok"] is True
    assert report["instances"]["promotion-target-contract"]["ok"] is True
    assert report["instances"]["capability-profile-contract"]["ok"] is True
    assert report["instances"]["capability-profiles"]["ok"] is True
    assert report["instances"]["evolution-ledger"]["ok"] is True
    assert report["instances"]["docs-registry"]["ok"] is True
    assert report["instances"]["gate-registry"]["ok"] is True
    assert report["instances"]["quality-profile"]["ok"] is True
    assert report["instances"]["quality-gate-plan"]["ok"] is True
    assert report["instances"]["skill-registry-contract"]["ok"] is True
    assert report["instances"]["skill-package-manifest-contract"]["ok"] is True
    assert report["instances"]["live-skill-activation-contract"]["ok"] is True
    assert report["instances"]["live-skill-registry-contract"]["ok"] is True
    assert report["instances"]["live-skill-package-manifests"]["ok"] is True
    assert report["instances"]["shadow-parity-contract"]["ok"] is True
    assert report["instances"]["workspace-status-contract"]["ok"] is True
    assert report["instances"]["coupling-audit-contract"]["ok"] is True


def test_schema_validation_report_uses_product_schemas_for_adopter_root(tmp_path) -> None:
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["mode"] == "adopter"
    assert report["ok"] is True
    assert report["schema_count"] >= 24
    assert report["required_gaps"] == []
    assert report["instances"]["docs-registry"]["ok"] is True


def test_schema_validation_adopter_partial_schemas_do_not_replace_product_contracts(
    tmp_path,
) -> None:
    schema_dir = tmp_path / "system" / "schemas" / "kernel"
    schema_dir.mkdir(parents=True)
    (schema_dir / "custom.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["mode"] == "adopter"
    assert report["ok"] is True
    assert report["schema_count"] >= 24
    assert report["instances"]["docs-registry"]["ok"] is True


def test_schema_validation_keeps_adopter_capability_profiles_advisory(
    tmp_path,
) -> None:
    (tmp_path / "docs").mkdir()
    profile_dir = tmp_path / "openspec" / "specs" / "legacy-family"
    profile_dir.mkdir(parents=True)
    (profile_dir / "capability.toml").write_text(
        'family = "legacy-family"\nowner_object = "legacy-kernel"\nprimary_invariant = "legacy repository owns its own capability profile"\nrouting_question = "Is this adopter capability in scope?"\ndecision_axes = ["adopter_metadata"]\n\n[boundary_rules]\nlegacy = "legacy adopter profile shape remains adopter-owned metadata"\n',
        encoding="utf-8",
    )

    report = schema_validation_report(tmp_path)
    profiles = report["instances"]["capability-profiles"]

    assert report["mode"] == "adopter"
    assert report["ok"] is True
    assert profiles["ok"] is True
    assert profiles["required_gaps"] == []
    assert profiles["advisory_gaps"]
    assert "openspec/specs/legacy-family/capability.toml" in profiles["advisory_gaps"][0]


def test_result_payload_validates_against_schema() -> None:
    result = EthosResult(command="status", ok=True, state="ready").to_dict()

    validation = validate_ethos_result(result)

    assert validation["ok"] is True
    json.dumps(validation)


def test_gate_schema_accepts_quality_descriptor_fields() -> None:
    payload = {
        "id": "markdown-links",
        "kind": "docs",
        "command": ["lychee", "--offline", "docs"],
        "policy": "required",
        "profile": "product",
        "toolchain": "quality-adapter",
        "asset_classes": ["markdown-docs"],
        "dimensions": ["links", "anchors"],
        "execution_mode": "adapter",
        "evidence_class": "diagnostic",
        "trust_bearing": False,
        "tool_adapter": "lychee",
        "writes_files": False,
        "network_policy": "offline",
        "version_source": "adopter-toolchain",
        "depends_on": [],
    }

    validation = validate_schema_instance("gate.schema.json", payload)

    assert validation["ok"] is True


def test_campaign_schema_accepts_lane_closeout_steps() -> None:
    payload = {
        "id": "terminal-openspec-productization",
        "state": "active",
        "owner": "ethos-maintainers",
        "objective": "Complete terminal OpenSpec productization through closeout-ready lanes.",
        "claim_id": "ethos-terminal-openspec-productization",
        "steps": [
            {
                "id": "campaign-orchestration",
                "title": "Campaign orchestration",
                "state": "closed",
                "ordinal": 1,
                "depends_on": [],
                "openspec_change": "ethos-campaign-orchestration",
                "work_lane": "work/campaign-orchestration",
                "claim_id": "ethos-campaign-orchestration",
                "closeout": {
                    "state": "retired",
                    "accepted_head": "a" * 40,
                    "candidate_head": "a" * 40,
                    "evidence": ["evidence/chronicle/campaign-orchestration/2026-07-02.md"],
                },
            }
        ],
    }

    validation = validate_schema_instance("campaign.schema.json", payload)

    assert validation["ok"] is True


def test_proof_run_schema_uses_trust_bearing_lattice() -> None:
    payload = {
        "action_id": "proof-policy",
        "command": ["ethos", "quality", "proof-policy", "--json"],
        "exit_code": 0,
        "stdout": "{}",
        "stderr": "",
        "state": "proven",
        "evidence_class": "proof",
        "verdict": "passed",
        "trust_bearing": True,
        "diagnostics": [],
        "governance_ref": "",
    }

    validation = validate_schema_instance("proof-run.schema.json", payload)

    assert validation["ok"] is True


def test_proof_run_schema_rejects_proven_without_trust_bearing() -> None:
    payload = {
        "action_id": "claims",
        "command": ["ethos", "quality", "claims", "--json"],
        "exit_code": 0,
        "stdout": "{}",
        "stderr": "",
        "state": "proven",
        "evidence_class": "contract",
        "verdict": "passed",
        "trust_bearing": False,
        "diagnostics": [],
        "governance_ref": "",
    }

    validation = validate_schema_instance("proof-run.schema.json", payload)

    assert validation["ok"] is False


def test_proof_run_schema_rejects_trust_bearing_non_proven_state() -> None:
    payload = {
        "action_id": "claims",
        "command": ["ethos", "quality", "claims", "--json"],
        "exit_code": None,
        "stdout": "",
        "stderr": "",
        "state": "planned",
        "evidence_class": "contract",
        "verdict": "not_run",
        "trust_bearing": True,
        "diagnostics": [],
        "governance_ref": "",
    }

    validation = validate_schema_instance("proof-run.schema.json", payload)

    assert validation["ok"] is False


def test_waived_proof_run_schema_requires_governance_reference() -> None:
    payload = {
        "action_id": "waiver",
        "command": ["ethos", "prove"],
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "state": "accepted-risk",
        "evidence_class": "proof",
        "verdict": "accepted",
        "trust_bearing": False,
        "diagnostics": [],
        "governance_ref": "",
    }

    validation = validate_schema_instance("proof-run.schema.json", payload)

    assert validation["ok"] is False


def test_workspace_status_payload_validates_worktree_bindings() -> None:
    payload = {
        "root": "/repo",
        "branch": "dev",
        "dirty": False,
        "changed_paths": [],
        "dirty_provenance": {
            "dirty": False,
            "state": "clean",
            "entries": [],
            "summary": {
                "tracked": 0,
                "untracked": 0,
                "deleted": 0,
                "conflicted": 0,
                "unavailable": 0,
            },
        },
        "role": "accepted_root",
        "role_policy": ROLE_POLICY_SAMPLE,
        "runtime_binding": {
            "kind": "workspace_status_runtime_binding",
            "state": "bound_to_audit_root",
            "audit_root": "/repo",
            "runner_module_path": "/repo/packages/ethos/src/ethos/__init__.py",
            "runner_source_root": "/repo",
            "schema_source_root": "/repo",
            "runner_matches_audit_root": True,
            "schema_matches_audit_root": True,
            "advisory_gaps": [],
            "next_action": "runner, schema, and audit root are aligned",
        },
        "landing_readiness": {
            "kind": "landing_readiness",
            "state": "not_work_lane",
            "branch": "dev",
            "head": "abc123",
            "candidate_branch": "candidate/dev",
            "candidate_head": "abc123",
            "required_gaps": [],
            "next_action": "start or enter a Work Lane before landing",
        },
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
                "claim_id": "",
                "claim_binding": "unbound",
            },
            {
                "branch": "dev",
                "role": "accepted_root",
                "head": "abc123",
                "worktree_path": "/repo",
                "worktree_binding": "current",
                "claim_id": "",
                "claim_binding": "missing",
            },
            {
                "branch": "candidate/dev",
                "role": "candidate",
                "head": "abc123",
                "worktree_path": "/repo-candidate-dev",
                "worktree_binding": "linked",
                "claim_id": "",
                "claim_binding": "missing",
            },
        ],
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "coordination": {
            "kind": "work_lane_coordination",
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
            "invalid_states": {"categories": {}, "category_count": 0, "gap_count": 0},
            "foreign_work_lane_count": 0,
            "unbound_work_lane_count": 0,
            "unbound_work_lane_refs": [],
            "missing_lease_count": 0,
            "overlap_count": 0,
            "unknown_scope_count": 0,
            "next_action": ("no Work Lane coordination action required"),
            "migration_recommendations": [],
        },
        "closeout_support": {
            "supported": False,
            "branch": "",
            "target_branch": "candidate/dev",
            "target_path": "/repo-candidate-dev",
            "operation": "",
            "owner": "",
            "claim_id": "",
            "claim_binding": "unbound",
            "required_gaps": ["protected_root_mutation"],
        },
        "stage_gates": {
            "authoring_allowed": False,
            "integration_allowed": False,
            "accepted_closeout_allowed": False,
            "blocked_stage": "authoring",
            "blocker_owner": "",
            "recommended_next_command": "ethos lane start <name>",
            "next_commands": ["ethos lane start <name>"],
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
        "role_policy": ROLE_POLICY_SAMPLE,
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
                "claim_id": "",
                "claim_binding": "unbound",
            },
            {
                "branch": "dev",
                "role": "accepted_root",
                "head": "abc123",
                "worktree_path": "/repo",
                "worktree_binding": "current",
                "claim_id": "",
                "claim_binding": "missing",
            },
            {
                "branch": "candidate/dev",
                "role": "candidate",
                "head": "abc123",
                "worktree_path": "/repo-candidate-dev",
                "worktree_binding": "linked",
                "claim_id": "",
                "claim_binding": "missing",
            },
        ],
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "coordination": {
            "kind": "work_lane_coordination",
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
            "invalid_states": {"categories": {}, "category_count": 0, "gap_count": 0},
            "foreign_work_lane_count": 0,
            "unbound_work_lane_count": 0,
            "unbound_work_lane_refs": [],
            "missing_lease_count": 0,
            "overlap_count": 0,
            "unknown_scope_count": 0,
            "next_action": ("no Work Lane coordination action required"),
        },
        "closeout_support": {
            "supported": False,
            "branch": "",
            "target_branch": "candidate/dev",
            "target_path": "/repo-candidate-dev",
            "operation": "",
            "owner": "",
            "claim_id": "",
            "claim_binding": "unbound",
            "required_gaps": ["protected_root_mutation"],
        },
        "stage_gates": {
            "authoring_allowed": False,
            "integration_allowed": False,
            "accepted_closeout_allowed": False,
            "blocked_stage": "authoring",
            "blocker_owner": "",
            "recommended_next_command": "ethos lane start <name>",
            "next_commands": ["ethos lane start <name>"],
        },
        "required_gaps": [],
    }

    validation = validate_schema_instance("workspace-status.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_trust_envelope_contract_requires_complete_carriers() -> None:
    valid = {
        "claim_id": "sample-trust",
        "state": "active",
        "boundary": {"owner": "repository", "scope": "governance"},
        "evidence": {
            "dated": "evidence/sample.md",
            "digest_trusted": True,
        },
        "carriers": {
            "openspec": "openspec/changes/sample-change",
        },
        "fallback": "stop promotion and keep prior contract",
        "kill_signal": "required lifecycle carrier missing",
        "promotion": {
            "targets": [
                {
                    "kind": "source",
                    "path": "packages/ethos/src/ethos/repository/evidence/claims.py",
                },
                {
                    "kind": "openspec",
                    "path": "openspec/specs/repository-governance/spec.md",
                },
            ],
            "ready": True,
        },
        "required_gaps": [],
    }

    assert validate_schema_instance("trust-envelope.schema.json", valid)["ok"] is True

    malformed = {
        "claim_id": "sample-trust",
        "state": "active",
        "boundary": {"owner": "repository"},
        "evidence": {"dated": "evidence/sample.md"},
        "carriers": {},
        "promotion": {"targets": []},
        "required_gaps": ["sample-trust:carriers.openspec_missing"],
    }

    validation = validate_schema_instance("trust-envelope.schema.json", malformed)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_promotion_target_contract_rejects_provider_paths() -> None:
    valid = {
        "kind": "evidence",
        "path": "evidence/sample.md",
        "description": "dated evidence promoted into repository truth",
    }

    assert validate_schema_instance("promotion-target.schema.json", valid)["ok"] is True

    validation = validate_schema_instance(
        "promotion-target.schema.json",
        {"kind": "gitlab", "path": "https://example.invalid/merge_requests/1"},
    )

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_capability_profile_contract_validates_boundary_and_proof_metadata() -> None:
    valid = {
        "family": "ethos-repository",
        "owner": {
            "package": "ethos-repository",
            "scope": "repository lifecycle governance",
        },
        "primary_invariant": "repository truth is promoted through claims and evidence",
        "routing_question": "Does this change alter repository trust admission?",
        "decision_axes": ["lifecycle", "surface", "authority"],
        "boundary_rules": [
            "OpenSpec records are specification carriers, not truth owners",
            "adopter-specific terms stay in profiles or evidence",
        ],
        "recommended_facets": {
            "lifecycle": ["authoring", "validation", "archive"],
            "surface": ["docs", "openspec", "schema"],
            "authority": ["docs", "openspec", "claim", "evidence"],
        },
        "proof_profile": {
            "default_command": "ethos prove --json",
            "executed_command": "ethos prove --execute --json",
            "required_gates": ["claims", "schemas"],
        },
    }

    assert validate_schema_instance("capability-profile.schema.json", valid)["ok"] is True

    validation = validate_schema_instance(
        "capability-profile.schema.json",
        {
            "family": "ethos-repository",
            "owner": {"package": "ethos-repository"},
            "proof_profile": {"default_command": "ethos prove --json"},
        },
    )

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_coupling_audit_payload_validates_binding_registry_contract() -> None:
    validation = validate_schema_instance(
        "coupling-audit.schema.json",
        coupling_audit_report(Path.cwd()),
    )

    assert validation["ok"] is True
    json.dumps(validation)


def test_coupling_audit_schema_rejects_ui_projection_fields() -> None:
    payload = coupling_audit_report(Path.cwd())
    payload["binding_registry"][0]["open_label"] = "Open Worktree"

    validation = validate_schema_instance("coupling-audit.schema.json", payload)

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

    assert {"repository-audit", "claims", "docs-registry", "schemas", "playbooks-v2"} <= set(
        registry
    )
    assert registry["repository-audit"].command[-4:] == ("audit", "--mode", "shape", "--json")
    assert registry["playbooks-v2"].command[-3:] == (
        "--mode",
        "v2-strict",
        "--json",
    )
    assert {"unit-architecture", "ruff", "build", "python-types", "docstrings"} <= set(registry)
    assert registry["ruff"].command == (".config/ci/scripts/run-python-lint.sh",)
    assert registry["ruff"].dimensions == ("lint", "format", "ratchet")
    assert registry["python-types"].command == ("ethos", "quality", "types", "--json")
    assert registry["docstrings"].command == (".config/ci/scripts/run-docstring-coverage.sh",)
    assert registry["python-types"].execution_mode == "inprocess"


def test_gate_registry_classifies_product_toolchain_profile() -> None:
    registry = gate_registry()

    for gate_id in ("repository-audit", "claims", "docs-registry", "schemas", "playbooks-v2"):
        assert registry[gate_id].profile == "product"
        assert registry[gate_id].toolchain == "ethos"

    for gate_id in ("unit-architecture", "ruff", "build", "python-types", "docstrings"):
        assert registry[gate_id].profile == "product-toolchain"
        assert registry[gate_id].toolchain == "uv-python"


def test_gate_graph_can_select_requested_gates() -> None:
    graph = gate_graph(("repository-audit", "claims"))

    assert [node.id for node in graph.nodes] == ["repository-audit", "claims"]
    assert graph.validate().ok is True


def test_default_gate_graph_includes_ci_owner_quality_floor() -> None:
    graph = gate_graph()
    node_ids = [node.id for node in graph.nodes]

    assert node_ids == [
        "repository-audit",
        "claims",
        "docs-registry",
        "schemas",
        "playbooks-v2",
        "unit-architecture",
        "ruff",
        "python-types",
        "docstrings",
        "toml-config",
        "yaml-config",
        "shell-lint",
        "format-policy",
    ]
    nodes = {node.id: node for node in graph.nodes}
    assert nodes["ruff"].to_dict()["command"] == [".config/ci/scripts/run-python-lint.sh"]
    assert nodes["toml-config"].to_dict()["command"] == [".config/ci/scripts/run-config-lint.sh"]
    assert nodes["shell-lint"].to_dict()["command"] == [".config/ci/scripts/run-shell-lint.sh"]


def test_adopter_profile_gate_graph_uses_profile_safe_default_floor(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text(
        """schema_version = 1
profile_id = \"sample-adopter\"
profile_version = \"1\"
ethos_contract_version = \"1\"

[repository]
kind = \"software\"
root_subject = \"sample\"
""",
        encoding="utf-8",
    )

    graph = gate_graph(root=tmp_path)
    node_ids = [node.id for node in graph.nodes]

    assert node_ids == [
        "repository-audit",
        "claims",
        "schemas",
        "playbooks-v2",
        "format-policy",
        "asset-determinism",
        "schema-contracts",
        "proof-policy",
    ]
    commands = [node.to_dict()["command"] for node in graph.nodes]
    assert [".config/ci/scripts/run-python-lint.sh"] not in commands
    assert [".config/ci/scripts/run-python-tests.sh"] not in commands
    assert [".config/ci/scripts/run-docstring-coverage.sh"] not in commands


def test_full_gate_graph_includes_build_after_tests_and_lint() -> None:
    graph = gate_graph(full=True)
    nodes = {node.id: node for node in graph.nodes}

    assert "build" in nodes
    assert "docstrings" in nodes
    assert nodes["build"].depends_on == ("unit-architecture", "ruff")
    assert nodes["ruff"].to_dict()["command"] == [".config/ci/scripts/run-python-lint.sh"]
    assert nodes["build"].to_dict()["command"] == ["uv", "build", "--all-packages"]
    assert {"markdown-structure", "format-policy", "asset-determinism"} <= nodes.keys()
    assert {"schema-contracts", "proof-policy"} <= nodes.keys()
    assert nodes["python-types"].to_dict()["command"] == ["ethos", "quality", "types", "--json"]


def test_repository_audit_reports_design_integrity_contract() -> None:
    from ethos.repository.audit import repository_audit

    report = repository_audit(Path.cwd(), openspec_mode="shape")
    design = report["design_integrity"]

    assert design["ok"] is True
    assert design["not_a_truth_store"] is True
    assert design["scope"] == "canonical_product_design_docs"
    assert design["required_gaps"] == []
    assert report["required_gaps"] == []


def test_repository_audit_blocks_design_truth_center_regression(tmp_path: Path) -> None:
    from ethos.repository.audit import DESIGN_INTEGRITY_DOCS
    from ethos.repository.audit import repository_audit

    for relative in DESIGN_INTEGRITY_DOCS:
        source = Path.cwd() / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    product = tmp_path / "docs/governance/product-design-contract.md"
    product.write_text(
        product.read_text(encoding="utf-8") + "\nVendorTruthCenter becomes product_self.\n",
        encoding="utf-8",
    )

    report = repository_audit(tmp_path, openspec_mode="shape")
    gaps = report["design_integrity"]["required_gaps"]

    assert report["design_integrity"]["ok"] is False
    assert (
        "design_integrity_forbidden_term:docs/governance/product-design-contract.md:VendorTruthCenter"
        in gaps
    )
    assert (
        "design_integrity_forbidden_term:docs/governance/product-design-contract.md:product_self"
        in gaps
    )
    assert any(
        str(gap).startswith("design_integrity_forbidden_term:") for gap in report["required_gaps"]
    )


def test_repository_audit_blocks_vendor_center_leak(tmp_path: Path) -> None:
    from ethos.repository.audit import DESIGN_INTEGRITY_DOCS
    from ethos.repository.audit import repository_audit

    for relative in DESIGN_INTEGRITY_DOCS:
        source = Path.cwd() / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    command_plane = tmp_path / "docs/reference/command-plane.md"
    command_plane.write_text(
        command_plane.read_text(encoding="utf-8") + "\nOpenAI owns the command plane.\n",
        encoding="utf-8",
    )

    report = repository_audit(tmp_path, openspec_mode="shape")
    gaps = report["design_integrity"]["required_gaps"]

    assert report["design_integrity"]["ok"] is False
    assert "design_integrity_vendor_center_leak:docs/reference/command-plane.md:OpenAI" in gaps
    assert any(
        str(gap).startswith("design_integrity_vendor_center_leak:")
        for gap in report["required_gaps"]
    )


def test_repository_audit_blocks_vendor_projection_files(tmp_path: Path) -> None:
    from ethos.repository.audit import DESIGN_INTEGRITY_DOCS
    from ethos.repository.audit import repository_audit

    for relative in DESIGN_INTEGRITY_DOCS:
        source = Path.cwd() / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("vendor projection", encoding="utf-8")

    report = repository_audit(tmp_path, openspec_mode="shape")
    gaps = report["design_integrity"]["required_gaps"]

    assert report["design_integrity"]["ok"] is False
    assert "design_integrity_forbidden_projection_path:CLAUDE.md" in gaps
    assert "design_integrity_forbidden_projection_path:CLAUDE.md" in report["required_gaps"]
