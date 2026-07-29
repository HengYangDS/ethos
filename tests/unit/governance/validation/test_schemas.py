from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.repository.audit import REQUIRED_SCHEMAS
from ethos.repository.policy.coupling.audit import coupling_audit_report
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.policy.schema import validate_ethos_result
from ethos.repository.policy.schema import validate_schema_instance
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.result import EthosResult

ROLE_POLICY_SAMPLE = {
    "release_branch": "main",
    "accepted_branch": "dev",
    "candidate_branch": "candidate/dev",
    "work_branch_prefix": "work/",
    "proposal_branch_prefix": "proposal/",
    "release_mirror": "independent",
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
            "role": "proposal_lane",
            "kind": "branch_prefix",
            "config_key": "proposal_branch_prefix",
            "pattern": "proposal/*",
        },
    ],
}


def test_schema_validation_report_covers_all_ethos_schemas() -> None:
    report = schema_validation_report()

    assert report["ok"] is True
    assert report["mode"] == "product"
    assert set(REQUIRED_SCHEMAS) <= set(report["schemas"])
    assert report["required_gaps"] == []
    assert report["schemas"]["quality-asset.schema.json"]["ok"] is True
    assert report["schemas"]["quality-gate-plan.schema.json"]["ok"] is True
    assert report["schemas"]["quality-profile.schema.json"]["ok"] is True
    assert report["schemas"]["review-record.schema.json"]["ok"] is True
    assert report["schemas"]["host-capability.schema.json"]["ok"] is True
    assert report["schemas"]["skill-activation.schema.json"]["ok"] is True
    assert report["schemas"]["skill-registry.schema.json"]["ok"] is True
    assert report["schemas"]["skill-package-manifest.schema.json"]["ok"] is True
    assert report["instances"]["docs-registry"]["ok"] is True
    assert report["instances"]["gate-registry"]["ok"] is True
    assert report["instances"]["quality-profile"]["ok"] is True
    assert report["instances"]["quality-gate-plan"]["ok"] is True
    assert report["instances"]["live-skill-activation-contract"]["ok"] is True
    assert report["instances"]["live-skill-registry-contract"]["ok"] is True
    assert report["instances"]["live-skill-package-manifests"]["ok"] is True
    assert report["instances"]["coupling-audit-contract"]["ok"] is True


def test_container_contract_is_not_a_product_schema_or_profile_field() -> None:
    report = schema_validation_report()

    assert "container-contract" not in report["schemas"]
    assert "container-contract" not in report["instances"]
    profile = RepositoryProfileDeclaration.bootstrap("example").model_dump(mode="python")
    profile["container_contract"] = {"schema_version": 1, "manifest": ".ethos/container.toml"}
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate(profile)


def test_schema_validation_report_uses_product_schemas_for_adopter_root(
    tmp_path,
) -> None:
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


def test_schema_validation_rejects_retired_capability_profile_schema(tmp_path) -> None:
    schema_dir = tmp_path / "system" / "schemas" / "kernel"
    schema_dir.mkdir(parents=True)
    (schema_dir / "capability-profile.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["schema_retired:capability-profile.schema.json"]
    assert report["schemas"]["capability-profile.schema.json"]["ok"] is False


def test_result_payload_validates_against_schema() -> None:
    result = EthosResult(command="status", ok=True, state="ready").to_dict()

    validation = validate_ethos_result(result)

    assert validation["ok"] is True
    json.dumps(validation)


def test_result_payload_accepts_governed_repository_context() -> None:
    result = EthosResult(
        command="status",
        ok=True,
        state="ready",
        governance_context={
            "contract": "governed_repository",
            "profile": "generic",
            "repository": "/workspace/repo",
            "authority": {
                "contract_ref": "system/authority.toml",
                "resolver": "contextual",
                "query_axes": [
                    "subject",
                    "predicate",
                    "scope",
                    "plane",
                    "validity",
                    "context",
                ],
                "unknown_verdict": "block",
                "currentness_requirements": [
                    "integrity",
                    "declared_authority",
                    "binding_match",
                    "validity",
                    "no_more_specific_active_owner",
                ],
                "conflict_verdict": "block",
                "novel_semantics": "model_gap",
            },
            "reader_projection_commands": ["ethos status"],
            "truth_boundary": "repository",
            "profile_boundary": "profile_or_adapter",
        },
    ).to_dict()

    validation = validate_ethos_result(result)

    assert validation["ok"] is True
    json.dumps(validation)


@pytest.mark.parametrize(
    "invalid",
    [
        {"rank": 1},
        {"order": []},
        {
            "query": {
                "required": ["subject", "predicate", "scope", "plane", "context"],
                "unknown_verdict": "block",
            }
        },
    ],
)
def test_contextual_authority_schema_rejects_global_rank_or_noncanonical_query_axes(
    invalid: dict[str, object],
) -> None:
    authority = {
        "schema": "system/schemas/contracts/authority.schema.json",
        "resolver": "contextual",
        "query": {
            "required": [
                "subject",
                "predicate",
                "scope",
                "plane",
                "validity",
                "context",
            ],
            "unknown_verdict": "block",
        },
        "currentness": {
            "requires": [
                "integrity",
                "declared_authority",
                "binding_match",
                "validity",
                "no_more_specific_active_owner",
            ],
            "history_is_current": False,
            "projection_is_authority": False,
            "adapter_is_authority": False,
        },
        "carrier_roles": [
            {"name": "native", "may_be_authoritative": True},
            {"name": "projection", "may_be_authoritative": False},
            {"name": "adapter", "may_be_authoritative": False},
            {"name": "fact", "may_be_authoritative": True, "requires_validity": True},
            {"name": "history", "may_be_authoritative": False},
        ],
        "resolution": {
            "conflict": "block",
            "novel_semantics": "model_gap",
            "more_specific_owner": "wins_only_within_same_query",
        },
    }
    validation = validate_schema_instance("../contracts/authority.schema.json", authority | invalid)

    assert validation["ok"] is False


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


def test_schema_validation_uses_product_schemas_for_adopter_without_local_schemas(
    tmp_path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "project.toml").write_text("[meta]\nname = 'sample'\n", encoding="utf-8")
    (tmp_path / "docs" / "current").mkdir(parents=True)
    (tmp_path / "docs" / "current" / "README.md").write_text(
        "---\nsubject: docs:governance\nrole: reference\nstate: canonical\nrelations: test\n---\n"
        "# Governance Docs\n",
        encoding="utf-8",
    )

    report = schema_validation_report(tmp_path)

    assert report["ok"] is True
    assert report["mode"] == "adopter"
    assert report["schema_count"] >= 19
    assert report["instances"]["docs-registry"]["ok"] is True
