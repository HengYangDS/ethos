from __future__ import annotations

from pathlib import Path

from ethos_repository.attestation import release_attestation, sbom_projection
from ethos_repository.release import release_policy_report, version_manifest


def test_version_manifest_keeps_workspace_packages_aligned() -> None:
    manifest = version_manifest(Path.cwd())

    assert manifest["version"] == "0.1.0a1"
    assert manifest["tag"] == "v0.1.0a1"
    assert manifest["all_package_versions_match"] is True
    assert set(manifest["packages"]) == {
        "ethos",
        "ethos-adapters",
        "ethos-assistants",
        "ethos-contracts",
        "ethos-core",
        "ethos-repository",
        "ethos-test",
    }


def test_release_policy_reports_required_gitlab_and_tag_contracts() -> None:
    report = release_policy_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["version"]["tag"] == "v0.1.0a1"
    assert report["required_files"] == [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
        ".ethos/release.toml",
    ]
    assert report["gitlab"]["ci"] == ".gitlab-ci.yml"
    assert report["protected_refs"]["branches"] == ["dev", "main"]
    assert report["protected_refs"]["tags"] == ["v*"]


def test_release_attestation_is_in_toto_and_slsa_shaped() -> None:
    attestation = release_attestation(
        root=Path.cwd(),
        head="abc123",
        evidence_digest="deadbeef",
    )

    assert attestation["_type"] == "https://in-toto.io/Statement/v1"
    assert attestation["predicateType"].endswith("/ethos-release/v1")
    assert attestation["predicate"]["slsa"]["builder"]["id"] == "ethos"
    assert attestation["subject"][0]["name"] == "ethos@0.1.0a1"


def test_sbom_projection_lists_workspace_packages_without_owning_truth() -> None:
    sbom = sbom_projection(Path.cwd())

    assert sbom["format"] == "SPDX-lite"
    assert sbom["truth"] == "pyproject-and-lockfile"
    assert {package["name"] for package in sbom["packages"]} >= {"ethos", "ethos-core"}
