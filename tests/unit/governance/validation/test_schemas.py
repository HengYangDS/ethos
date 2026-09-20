"""Bind schema validation to product-owned definitions rather than adopter shadows."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.repository.audit import REQUIRED_SCHEMAS
from ethos.repository.policy.gates import resolve_gate_policy
from ethos.repository.policy.schema import load_schema
from ethos.repository.policy.schema import schema_validation_report
from ethos.repository.policy.schema import validate_ethos_result
from ethos.repository.policy.schema import validate_schema_instance
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.result import EthosResult

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
    for section in ("schemas", "instances"):
        for item in report[section].values():
            assert item["verdict"] == "pass"
            assert "ok" not in item
    assert "evidence-boundaries.schema.json" in report["schemas"]
    assert "projection-input.schema.json" in report["schemas"]
    assert "container-contract" not in report["schemas"]
    assert "container-contract" not in report["instances"]
    profile = RepositoryProfileDeclaration.bootstrap("example").model_dump(mode="python")
    profile["container_contract"] = {"schema_version": 1, "manifest": ".ethos/container.toml"}
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate(profile)


@pytest.mark.parametrize(
    "condition",
    [
        "empty",
        "shadow",
        "copied-invalid",
        "copied-malformed",
        "retired",
        "copied-retired",
        "native-doc",
    ],
)
def test_schema_reports_keep_native_ownership_across_adopter_shapes(tmp_path, condition) -> None:
    """Adopter shadows never replace product schemas, while retired owners block."""
    schema_dir = tmp_path / "system/schemas/kernel"
    if condition.startswith("copied"):
        shutil.copytree(ROOT / "system/schemas/kernel", schema_dir)
    else:
        schema_dir.mkdir(parents=True)
    if condition in {"shadow", "copied-invalid", "copied-malformed"}:
        (schema_dir / "custom.schema.json").write_text("{}")
        (schema_dir / "result.schema.json").write_text(
            '{"type":"not-a-json-schema-type"}' if condition == "copied-invalid" else "{"
        )
    retired = condition.endswith("retired")
    if retired:
        (schema_dir / "capability-profile.schema.json").write_text("{}")
    docs = tmp_path / "docs/current"
    docs.mkdir(parents=True)
    if condition == "native-doc":
        (tmp_path / ".ethos").mkdir()
        (tmp_path / ".ethos/project.toml").write_text("[meta]\nname = 'sample'\n")
        (docs / "README.md").write_text(
            "---\nsubject: docs:governance\nrole: reference\nstate: canonical\n"
            "relations: {}\n---\n# Governance Docs\n"
        )
    report = schema_validation_report(tmp_path)
    assert report["mode"] == "product"
    assert "ok" not in report
    assert report["verdict"] == ("block" if retired else "pass")
    assert report["required_gaps"] == (
        ["schema_retired:capability-profile.schema.json"] if retired else []
    )
    expected = {path.name for path in (ROOT / "system/schemas").rglob("*.schema.json")}
    if retired:
        expected.add("capability-profile.schema.json")
    assert set(report["schemas"]) == expected
    assert report["schema_count"] == len(expected)
    assert "custom.schema.json" not in report["schemas"]
    assert report["schemas"]["result.schema.json"]["verdict"] == "pass"
    assert report["instances"]["docs-registry"]["verdict"] == "pass"
    if retired:
        assert report["schemas"]["capability-profile.schema.json"] == {
            "verdict": "block",
            "error": "retired semantic schema",
        }


@pytest.mark.parametrize("with_context", [False, True])
def test_result_payload_validates_native_governance_context(with_context) -> None:
    """The same result schema admits absent and explicit governed-repository context."""
    context = (
        {
            "contract": "governed_repository",
            "profile": "generic",
            "repository": "/workspace/repo",
            "reader_projection_commands": ["ethos status"],
            "truth_boundary": "repository",
            "profile_boundary": "profile_or_adapter",
        }
        if with_context
        else {}
    )
    result = EthosResult(
        command="status", verdict="pass", state="ready", governance_context=context
    )
    validation = validate_ethos_result(result.to_dict())
    assert validation["verdict"] == "pass"
    assert "ok" not in validation
    json.dumps(validation)


def test_gate_schema_accepts_quality_descriptor_fields() -> None:
    """Validate the real descriptor plus the supported command-adapter variation."""
    payload = resolve_gate_policy().registry["markdown-links"].to_dict()
    payload.pop("providers")
    payload.update(
        command=["lychee", "--offline", "docs"],
        execution_mode="adapter",
        evidence_class="diagnostic",
        trust_bearing=False,
    )
    validation = validate_schema_instance("gate.schema.json", payload)
    assert validation["verdict"] == "pass"


@pytest.mark.parametrize("scope", ["activation", "packages"])
def test_schema_report_rejects_malformed_live_skill_inputs(tmp_path, scope) -> None:
    """Actual native declarations and package metadata fail at the same report boundary."""
    skills = tmp_path / ".agents/skills"
    shutil.copytree(ROOT / ".agents/skills", skills)
    if scope == "activation":
        (skills / "activation.toml").write_text("[meta")
        expected = (
            "live-skill-activation-contract",
            "live-skill-registry-contract",
            "live-skill-package-manifests",
        )
    else:
        for name, text in (("malformed", "[package"), ("invalid", "schema_version = 2\n")):
            path = skills / name / "package.toml"
            path.parent.mkdir()
            path.write_text(text)
        expected = ("live-skill-package-manifests",)
    (tmp_path / "docs").mkdir()
    report = schema_validation_report(tmp_path)
    assert report["verdict"] == "block"
    for name in expected:
        assert report["instances"][name]["verdict"] == "block"
        assert report["instances"][name]["required_gaps"]
    if scope == "packages":
        gaps = report["instances"]["live-skill-package-manifests"]["required_gaps"]
        assert len(gaps) >= 2
        for name in ("malformed", "invalid"):
            assert any(gap.startswith(f".agents/skills/{name}/package.toml:") for gap in gaps)


def test_validate_schema_instance_reports_all_native_instance_gaps() -> None:
    validation = validate_schema_instance("result.schema.json", {"verdict": "invalid"})

    assert validation["verdict"] == "block"
    assert len(validation["required_gaps"]) > 1


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
