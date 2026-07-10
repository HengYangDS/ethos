# ruff: noqa: ARG005
"""Coverage-closure: generated-artifact topology edge branches (100% no-exemption).

The generated-artifact-topology contract and its repository policy landed with a
few branches the existing tests did not exercise. These close them so the
whole-repo 100% floor holds:

- path_policy_for adopter-specific product-root denial (topology line 159).
- generated_artifact_topology_report review/deny arms where a policy carries no
  required_gap (artifacts.py branches 46->35, 49->35).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy import artifacts as artifacts_mod
from ethos_core.contracts.artifacts import topology

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_path_policy_denies_adopter_specific_product_root() -> None:
    # An adopter-specific root under a product repo is denied (topology line 159).
    policy = topology.path_policy_for("adopters/acme/config.yaml")

    assert policy["decision"] == "deny"
    assert "adopter_specific_product_root" in str(policy["required_gap"])


def test_report_collects_review_and_deny_gaps_across_iterations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A review/deny policy WITH a gap appends and then continues the loop; one
    # WITHOUT a gap takes the guard's false arm. An allow and an ignore policy
    # exercise the remaining decision arms (artifacts.py line 40 and 46->35).
    for name in (
        "allow.txt",
        "review_gap.txt",
        "review_none.txt",
        "deny_gap.txt",
        "deny_none.txt",
        "ignore.txt",
    ):
        (tmp_path / name).write_text("x", encoding="utf-8")

    def _fake_policy(rel: str, declaration: object) -> dict[str, object]:
        if rel.endswith("allow.txt"):
            return {"decision": "allow"}
        if rel.endswith("review_gap.txt"):
            return {"decision": "review", "required_gap": "review_gap_here"}
        if rel.endswith("review_none.txt"):
            return {"decision": "review", "required_gap": ""}
        if rel.endswith("deny_gap.txt"):
            return {"decision": "deny", "required_gap": "deny_gap_here"}
        if rel.endswith("deny_none.txt"):
            return {"decision": "deny", "required_gap": ""}
        return {"decision": "ignore"}

    monkeypatch.setattr(artifacts_mod, "path_policy_from_declaration", _fake_policy)
    monkeypatch.setattr(
        artifacts_mod,
        "_candidate_paths",
        lambda root, declaration: [
            tmp_path / "allow.txt",
            tmp_path / "review_gap.txt",
            tmp_path / "review_none.txt",
            tmp_path / "deny_gap.txt",
            tmp_path / "deny_none.txt",
            tmp_path / "ignore.txt",
        ],
    )

    report = artifacts_mod.generated_artifact_topology_report(tmp_path)

    # Only the gap-carrying policies contribute; the empty ones are tolerated.
    assert report["review_gaps"] == ["review_gap_here"]
    assert report["required_gaps"] == ["deny_gap_here"]
    assert "allow.txt" in report["allowed_paths"]


def test_explicit_denied_roots_ignores_empty_contract_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    declaration = topology.GeneratedArtifactTopologyDeclaration.model_validate(
        {
            "id": "generated-artifact-topology-test",
            "declarative_boundary": "declarative",
            "product_adopter_boundary": "adopter",
            "product_adopter_required_gap_prefix": "adopter_gap",
            "cache_flat_boundary": "cache",
            "cache_flat_required_gap_prefix": "cache_gap",
            "cache_flat_root_prefix": ".cache",
            "cache_allowed_prefixes": [".cache/local-state"],
            "runtime_flat_boundary": "runtime",
            "runtime_flat_required_gap_prefix": "runtime_gap",
            "runtime_flat_root_prefix": "build/runtime",
            "runtime_allowed_prefixes": ["build/runtime/tool-cache"],
            "generated_denial_boundary": "generated",
            "repo_root_generated_boundary": "root",
            "repo_root_generated_required_gap_prefix": "root_gap",
            "ignore_boundary": "ignore",
            "source_schema_suffix": ".schema.json",
            "generated_suffixes": [".json"],
            "generated_filenames": ["report.json"],
            "generated_filename_prefixes": [".coverage."],
            "source_metadata_filenames": ["package.json"],
            "product_adopter_root_prefixes": ["adopters"],
            "declarative_prefix": [],
            "allowed_prefix": [],
            "review_prefix": [],
            "denied_prefix": [],
            "denied_root_cache_prefix": [{"prefix": ""}],
            "denied_legacy_generated_prefix": [{"prefix": "dist"}],
            "denied_generated_prefix": [],
            "lifecycle_class": [],
        }
    )

    assert artifacts_mod._explicit_denied_roots(declaration) == ["dist"]


def test_default_declaration_path_falls_back_when_no_source_tree_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(topology.Path, "exists", lambda self: False)

    assert topology._default_declaration_path() == topology.DECLARATION_PATH


def test_declaration_text_falls_back_to_packaged_resource(tmp_path: Path) -> None:
    missing = tmp_path / "missing-generated-artifact-topology.toml"

    text = topology._declaration_text(missing)

    assert 'id = "generated-artifact-topology"' in text
