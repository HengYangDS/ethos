from __future__ import annotations

from pathlib import Path

from ethos_repository.attestation import release_attestation
from ethos_repository.attestation import sbom_projection
from ethos_repository.release import release_policy_report
from ethos_repository.release import version_manifest


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
        "ethos-quality",
        "ethos-repository",
        "ethos-test",
    }


def test_release_policy_reports_host_profile_separately_from_product_files() -> None:
    report = release_policy_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["version"]["tag"] == "v0.1.0a1"
    assert report["required_files"] == [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        ".ethos/release.toml",
    ]
    assert "gitlab" not in report
    assert report["host_profile"] == {
        "provider": "gitlab",
        "layer": "profile_config",
        "surfaces": {
            "ci": ".gitlab-ci.yml",
            "merge_request_template": ".gitlab/merge_request_templates/default.md",
            "issue_template": ".gitlab/issue_templates/task.md",
        },
    }
    assert report["protected_refs"]["branches"] == ["main", "dev"]
    assert report["protected_refs"]["tags"] == ["v*"]


def test_release_policy_uses_configured_branch_roles_for_protected_refs(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / ".ethos").mkdir(parents=True)
    (root / ".gitlab" / "merge_request_templates").mkdir(parents=True)
    (root / ".gitlab" / "issue_templates").mkdir(parents=True)
    for path in (
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
    ):
        (root / path).write_text("x\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sample"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (root / ".ethos" / "workspace.toml").write_text(
        '[branch_roles]\nrelease_branch = "release"\naccepted_branch = "integration"\ncandidate_branch = "stage/integration"\nwork_branch_prefix = "lane/"\nsubmit_branch_prefix = "review/"\n',
        encoding="utf-8",
    )
    (root / ".ethos" / "release.toml").write_text(
        '[release]\nversion_source = "pyproject.toml"\ntag_pattern = "v{version}"\nartifact_glob = "dist/*"\n\n[protected_refs]\nbranches = ["release", "integration"]\ntags = ["v*"]\n\n[host_profile]\nprovider = "gitlab"\n\n[host_profile.surfaces]\nci = ".gitlab-ci.yml"\nmerge_request_template = ".gitlab/merge_request_templates/default.md"\nissue_template = ".gitlab/issue_templates/task.md"\n\n[attestation]\nformats = ["in-toto", "slsa", "spdx-lite"]\nsigning = "git-ssh"\n',
        encoding="utf-8",
    )

    report = release_policy_report(root)

    assert "protected_branches_policy_missing" not in report["required_gaps"]
    assert report["protected_refs"]["branches"] == ["release", "integration"]
    assert report["host_profile"]["provider"] == "gitlab"


def test_release_policy_does_not_accept_retired_provider_section(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / ".ethos").mkdir(parents=True)
    for path in ("README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md"):
        (root / path).write_text("x\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sample"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (root / ".ethos" / "release.toml").write_text(
        '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n[gitlab]\nci = ".gitlab-ci.yml"\n\n[attestation]\nformats = ["in-toto", "slsa", "spdx-lite"]\n',
        encoding="utf-8",
    )

    report = release_policy_report(root)

    assert report["host_profile"] == {
        "provider": "",
        "layer": "profile_config",
        "surfaces": {},
    }


def test_release_policy_reports_host_surface_gaps_without_product_file_coupling(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / ".ethos").mkdir(parents=True)
    for path in ("README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md"):
        (root / path).write_text("x\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sample"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (root / ".ethos" / "release.toml").write_text(
        '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n[host_profile]\nprovider = "gitlab"\n\n[host_profile.surfaces]\nci = ".gitlab-ci.yml"\n\n[attestation]\nformats = ["in-toto", "slsa", "spdx-lite"]\n',
        encoding="utf-8",
    )

    report = release_policy_report(root)

    assert "release_file_missing:.gitlab-ci.yml" not in report["required_gaps"]
    assert "host_surface_missing:gitlab:ci:.gitlab-ci.yml" in report["required_gaps"]


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
