from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.repository.audit import REQUIRED_SCHEMAS
from ethos.repository.policy.schema import load_schema
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.policy.schema import validate_ethos_result
from ethos.repository.policy.schema import validate_schema_instance
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.result import EthosResult
from tests.support.literal_cases import literal_case

ROLE_POLICY_SAMPLE = literal_case("governance.validation.test_schemas:assign:ROLE_POLICY_SAMPLE:0")
ROOT = Path(__file__).resolve().parents[4]


def test_schema_loader_uses_active_product_checkout_not_adopter_schema(tmp_path) -> None:
    source = load_schema("workspace-status.schema.json", root=ROOT)
    schema_dir = tmp_path / "system" / "schemas" / "kernel"
    schema_dir.mkdir(parents=True)
    (schema_dir / "workspace-status.schema.json").write_text("{}\n", encoding="utf-8")

    adopter = load_schema("workspace-status.schema.json", root=tmp_path)

    assert source["title"] == "ETHOS Workspace Status"
    assert adopter["title"] == "ETHOS Workspace Status"
    assert adopter != {}


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

    assert report["mode"] == "product"
    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["schema_count"] >= 24
    assert report["required_gaps"] == []
    assert report["instances"]["docs-registry"]["verdict"] == "pass"


def test_schema_validation_adopter_schemas_do_not_replace_product_contracts(
    tmp_path,
) -> None:
    schema_dir = tmp_path / "system" / "schemas" / "kernel"
    schema_dir.mkdir(parents=True)
    (schema_dir / "custom.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
        encoding="utf-8",
    )
    (schema_dir / "result.schema.json").write_text("{", encoding="utf-8")
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["mode"] == "product"
    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["schema_count"] >= 24
    assert "custom.schema.json" not in report["schemas"]
    assert report["schemas"]["result.schema.json"]["verdict"] == "pass"
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
    assert report["mode"] == "product"
    assert report["schema_count"] >= 19
    assert report["instances"]["docs-registry"]["verdict"] == "pass"


@pytest.mark.parametrize(
    "contents",
    [
        "{",
        json.dumps({"type": "not-a-json-schema-type"}),
    ],
)
def test_schema_report_ignores_malformed_adopter_schema(tmp_path, contents: str) -> None:
    target = tmp_path / "system" / "schemas" / "kernel"
    shutil.copytree(ROOT / "system" / "schemas" / "kernel", target)
    (target / "result.schema.json").write_text(contents, encoding="utf-8")
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["schemas"]["result.schema.json"]["verdict"] == "pass"
    assert report["required_gaps"] == []


def test_schema_report_blocks_malformed_live_skill_declarations(tmp_path) -> None:
    activation = tmp_path / ".agents" / "skills" / "activation.toml"
    activation.parent.mkdir(parents=True)
    activation.write_text("[meta", encoding="utf-8")
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["verdict"] == "block"
    for name in (
        "live-skill-activation-contract",
        "live-skill-registry-contract",
        "live-skill-package-manifests",
    ):
        assert report["instances"][name]["verdict"] == "block"
        assert report["instances"][name]["required_gaps"]


def test_schema_report_blocks_malformed_and_invalid_live_skill_packages(tmp_path) -> None:
    skill_root = tmp_path / ".agents" / "skills"
    shutil.copytree(ROOT / ".agents" / "skills", skill_root)
    malformed = skill_root / "malformed" / "package.toml"
    malformed.parent.mkdir()
    malformed.write_text("[package", encoding="utf-8")
    invalid = skill_root / "invalid" / "package.toml"
    invalid.parent.mkdir()
    invalid.write_text("schema_version = 2\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    package = report["instances"]["live-skill-package-manifests"]
    assert package["verdict"] == "block"
    assert len(package["required_gaps"]) >= 2
    assert any(
        gap.startswith(".agents/skills/malformed/package.toml:") for gap in package["required_gaps"]
    )
    assert any(
        gap.startswith(".agents/skills/invalid/package.toml:") for gap in package["required_gaps"]
    )


def test_validate_schema_instance_reports_all_native_instance_gaps() -> None:
    validation = validate_schema_instance("result.schema.json", {"verdict": "invalid"})

    assert validation["verdict"] == "block"
    assert len(validation["required_gaps"]) > 1


def test_schema_report_skips_retired_schema_during_native_iteration(
    tmp_path,
) -> None:
    target = tmp_path / "system" / "schemas" / "kernel"
    shutil.copytree(ROOT / "system" / "schemas" / "kernel", target)
    (target / "capability-profile.schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "docs").mkdir()

    report = schema_validation_report(tmp_path)

    assert report["required_gaps"] == ["schema_retired:capability-profile.schema.json"]
    assert report["schemas"]["capability-profile.schema.json"] == {
        "verdict": "block",
        "error": "retired semantic schema",
    }


def test_validate_schema_instance_rejects_adopter_schema_shadowing(
    tmp_path,
) -> None:
    schema_dir = tmp_path / "system" / "schemas" / "kernel"
    shutil.copytree(ROOT / "system" / "schemas" / "kernel", schema_dir)
    (schema_dir / "cycle.schema.json").write_text(
        json.dumps({"type": "object", "properties": {"child": {"$ref": "cycle.schema.json"}}}),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError):
        validate_schema_instance("cycle.schema.json", {}, root=tmp_path)
