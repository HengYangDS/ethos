from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from ethos.repository.audit import REQUIRED_SCHEMAS
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.policy.schema import validate_ethos_result
from ethos.repository.policy.schema import validate_schema_instance
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.result import EthosResult
from tests.support.literal_cases import literal_case

ROLE_POLICY_SAMPLE = literal_case("governance.validation.test_schemas:assign:ROLE_POLICY_SAMPLE:0")


def test_schema_validation_report_covers_all_ethos_schemas() -> None:
    report = schema_validation_report()

    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["mode"] == "product"
    assert set(REQUIRED_SCHEMAS) <= set(report["schemas"])
    assert report["required_gaps"] == []
    assert all(item["verdict"] == "pass" for item in report["schemas"].values())
    assert all("ok" not in item for item in report["schemas"].values())
    assert all(item["verdict"] == "pass" for item in report["instances"].values())
    assert all("ok" not in item for item in report["instances"].values())


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
    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["schema_count"] >= 24
    assert report["required_gaps"] == []
    assert report["instances"]["docs-registry"]["verdict"] == "pass"


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
    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["schema_count"] >= 24
    assert report["instances"]["docs-registry"]["verdict"] == "pass"


def test_schema_validation_rejects_retired_capability_profile_schema(tmp_path) -> None:
    schema_dir = tmp_path / "system" / "schemas" / "kernel"
    schema_dir.mkdir(parents=True)
    (schema_dir / "capability-profile.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["required_gaps"] == ["schema_retired:capability-profile.schema.json"]
    assert report["schemas"]["capability-profile.schema.json"]["verdict"] == "block"


def test_result_payload_validates_against_schema() -> None:
    result = EthosResult(command="status", verdict="pass", state="ready").to_dict()

    validation = validate_ethos_result(result)

    assert validation["verdict"] == "pass"
    assert "ok" not in validation
    json.dumps(validation)


def test_result_payload_accepts_governed_repository_context() -> None:
    result = EthosResult(
        command="status",
        verdict="pass",
        state="ready",
        governance_context={
            "contract": "governed_repository",
            "profile": "generic",
            "repository": "/workspace/repo",
            "reader_projection_commands": ["ethos status"],
            "truth_boundary": "repository",
            "profile_boundary": "profile_or_adapter",
        },
    ).to_dict()

    validation = validate_ethos_result(result)

    assert validation["verdict"] == "pass"
    assert "ok" not in validation
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

    assert validation["verdict"] == "pass"


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

    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["mode"] == "adopter"
    assert report["schema_count"] >= 19
    assert report["instances"]["docs-registry"]["verdict"] == "pass"
