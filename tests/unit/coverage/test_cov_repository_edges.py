# ruff: noqa: ARG005, TC002
"""Coverage-closure edge tests for the repository cluster (100% no-exemption campaign)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.repository.evidence.parity.validation import command_matches_identity
from ethos.repository.evidence.parity.validation import semantic_tree_digest
from ethos.repository.evidence.parity.validation import validate_parity_evidence
from ethos.repository.openspec.metadata import read_openspec_metadata
from ethos.repository.policy import schema as policy_schema
from tests.unit.product.parity.snapshots import complete_parity_evidence


def test_read_openspec_metadata_skips_blank_and_comment_lines(tmp_path: Path) -> None:
    path = tmp_path / ".openspec.yaml"
    path.write_text(
        "# a comment line\n\n   \nschema: spec-driven\n  # indented comment\nstatus: active\n",
        encoding="utf-8",
    )

    metadata = read_openspec_metadata(path)

    assert metadata == {"schema": "spec-driven", "status": "active"}


def test_semantic_tree_digest_returns_empty_for_blank_head(tmp_path: Path) -> None:
    # Blank head short-circuits before any git subprocess is run (line 43).
    assert semantic_tree_digest(tmp_path, head="", relevant_paths=("a.py",)) == ""


def test_validate_verified_capabilities_rejects_non_list_and_returns_early() -> None:
    payload = complete_parity_evidence("generic")
    payload["verified_capabilities"] = None

    gaps = validate_parity_evidence(payload, "generic")

    assert "parity_evidence_invalid:generic:verified_capabilities" in gaps
    assert "parity_evidence_invalid:generic:unknown_capability" not in gaps
    assert "parity_evidence_invalid:generic:capability_basis" not in gaps


def test_command_identity_rejects_command_without_target_flag_when_target_unspecified() -> None:
    # target is None -> the `isinstance(target, str) and target` branch is skipped, so the
    # `elif "--target " not in command` guard (328) fires and returns False (329).
    assert (
        command_matches_identity(
            "ethos parity shadow --adopter generic --execute --json",
            adopter="generic",
            target=None,
        )
        is False
    )


def test_validate_freshness_flags_missing_required_field() -> None:
    payload = complete_parity_evidence("generic")
    freshness = payload["freshness"]
    assert isinstance(freshness, dict)
    del freshness["product_head"]

    gaps = validate_parity_evidence(payload, "generic")

    assert "parity_evidence_invalid:generic:product_head" in gaps


def test_product_schema_dir_falls_back_to_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy_schema, "_schema_dir_has_contracts", lambda path: False)
    result = policy_schema._product_schema_dir()
    assert result == Path.cwd() / "system" / "schemas" / "kernel"


def test_schema_validation_report_records_malformed_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    kernel = tmp_path / "system" / "schemas" / "kernel"
    kernel.mkdir(parents=True)
    (kernel / "broken.schema.json").write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(policy_schema, "_effective_schema_dir", lambda root: kernel)
    monkeypatch.setattr(policy_schema, "_instance_validation_report", lambda root, *, mode: {})
    report = policy_schema.schema_validation_report(tmp_path)
    assert report["ok"] is False
    assert any(gap.startswith("broken.schema.json:") for gap in report["required_gaps"])
    assert report["schemas"]["broken.schema.json"]["ok"] is False
    assert "error" in report["schemas"]["broken.schema.json"]


def test_live_skill_package_manifest_malformed_toml(tmp_path: Path) -> None:
    skills = tmp_path / ".agents" / "skills"
    skills.mkdir(parents=True)
    (skills / "activation.toml").write_text("", encoding="utf-8")
    package = skills / "demo"
    package.mkdir()
    (package / "package.toml").write_text("[bad\n", encoding="utf-8")
    result = policy_schema._live_skill_contract_instances(tmp_path)
    manifests = result["live-skill-package-manifests"]
    assert manifests["ok"] is False
    assert any(
        gap.startswith(".agents/skills/demo/package.toml:") for gap in manifests["required_gaps"]
    )
