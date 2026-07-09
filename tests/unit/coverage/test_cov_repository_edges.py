# ruff: noqa: ARG005, TC002, FLY002
"""Coverage-closure edge tests for the repository cluster (100% no-exemption campaign)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.repository.adoption.scaffold.core import OPENSPEC_CAPABILITIES
from ethos.repository.adoption.scaffold.core import default_files
from ethos.repository.evidence.parity.validation import command_matches_identity
from ethos.repository.evidence.parity.validation import semantic_tree_digest
from ethos.repository.evidence.parity.validation import validate_parity_evidence
from ethos.repository.openspec.metadata import read_openspec_metadata
from ethos.repository.policy import schema as policy_schema
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import table_version
from tests.unit.product.parity.snapshots import complete_parity_evidence


def test_read_openspec_metadata_skips_blank_and_comment_lines(tmp_path: Path) -> None:
    path = tmp_path / ".openspec.yaml"
    path.write_text(
        "# a comment line\n\n   \nschema: spec-driven\n  # indented comment\nstatus: active\n",
        encoding="utf-8",
    )

    metadata = read_openspec_metadata(path)

    assert metadata == {"schema": "spec-driven", "status": "active"}


def test_default_files_github_profile_emits_workflow(tmp_path: Path) -> None:
    # profile == "github" takes the branch that writes the GitHub Actions workflow.
    files = default_files(tmp_path, "github")
    assert ".github/workflows/ethos.yml" in files
    workflow = files[".github/workflows/ethos.yml"]
    assert workflow.startswith("name: ethos")
    assert "runs-on: ubuntu-latest" in workflow
    # Other profiles do not take the branch, so the workflow file is absent.
    assert ".github/workflows/ethos.yml" not in default_files(tmp_path, "generic")


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


def test_load_repository_profile_reads_previous_projection_mapping(tmp_path: Path) -> None:
    ethos_dir = tmp_path / ".ethos"
    ethos_dir.mkdir()
    (ethos_dir / "profile.toml").write_text(
        "\n".join(
            [
                'profile_id = "sample"',
                "",
                "[previous_projection]",
                'old_rules = "legacy/rules"',
                'blank = ""',
                "numeric = 7",
                "",
            ]
        ),
        encoding="utf-8",
    )

    profile = load_repository_profile(tmp_path)

    # Only the non-empty string entry survives; the blank string and the
    # non-string numeric entry are filtered out by the comprehension guard.
    assert profile.previous_projection == {"old_rules": "legacy/rules"}
    assert profile.exists is True
    assert profile.valid is True


def test_table_version_defaults_when_meta_not_mapping() -> None:
    # `meta` key absent -> payload.get('meta') is None -> not a dict.
    assert table_version({}) == 1
    # `meta` present but not a mapping -> still fails the isinstance guard.
    assert table_version({"meta": "not-a-table"}) == 1


def test_table_version_defaults_when_version_not_integral() -> None:
    # Truthy non-numeric string -> int(...) raises ValueError -> fallback to 1.
    assert table_version({"meta": {"version": "not-an-int"}}) == 1
    # Truthy non-scalar value -> int(...) raises TypeError -> fallback to 1.
    assert table_version({"meta": {"version": [1, 2]}}) == 1
    # Control: a valid integral version is parsed rather than defaulted.
    assert table_version({"meta": {"version": "3"}}) == 3


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


def test_openspec_capabilities_has_no_duplicates() -> None:
    # Invariant formerly guarded by an import-time check: the capability list is a
    # set of distinct families. A duplicate would double-scaffold a spec directory.
    caps = OPENSPEC_CAPABILITIES
    assert len(caps) == len(set(caps))
