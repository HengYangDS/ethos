from __future__ import annotations

from pathlib import Path

from ethos.repository.release.attestation import release_attestation
from ethos.repository.release.attestation import sbom_projection
from ethos.repository.release.core import release_policy_report
from ethos.repository.release.core import version_manifest


def test_version_manifest_keeps_workspace_packages_aligned() -> None:
    manifest = version_manifest(Path.cwd())

    assert manifest["version"] == "0.1.0a1"
    assert manifest["tag"] == "v0.1.0a1"
    assert manifest["all_package_versions_match"] is True
    assert set(manifest["packages"]) == {
        "ethos",
        "ethos-core",
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


def test_release_policy_reports_equal_gitlab_and_github_publication_topology() -> None:
    report = release_policy_report(Path.cwd())

    topology = report["publication_topology"]
    assert topology["state"] == "ready"
    assert topology["legacy"] is False
    assert topology["local"] == {
        "id": "local",
        "role": "local_verification_install",
        "mode": "offline",
        "verification_command": "tools/ci/scripts/run-local-ci.sh",
        "installation_command": "tools/ci/scripts/run-local-install-smoke.sh",
    }
    assert topology["gitlab"]["capabilities"] == ["repository", "ci_cd", "publication"]
    assert topology["github"]["capabilities"] == ["repository", "ci_cd", "publication"]
    assert topology["gitlab"]["git_remote"] != topology["github"]["git_remote"]


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


def test_release_attestation_is_in_toto_slsa_and_lockfile_material_shaped() -> None:
    attestation = release_attestation(
        root=Path.cwd(),
        head="abc123",
        evidence_digest="deadbeef",
    )

    assert attestation["_type"] == "https://in-toto.io/Statement/v1"
    assert attestation["predicateType"].endswith("/ethos-release/v1")
    assert attestation["predicate"]["slsa"]["builder"]["id"] == "ethos"
    assert attestation["subject"][0]["name"] == "ethos@0.1.0a1"
    materials = attestation["predicate"]["slsa"]["materials"]
    material_uris = {material["uri"] for material in materials}
    assert "git+repository" in material_uris
    assert "ethos+evidence" in material_uris
    assert "file+uv.lock" in material_uris
    assert "ethos+sbom" in material_uris
    assert attestation["predicate"]["sbom"]["lockfile"]["path"] == "uv.lock"
    assert attestation["predicate"]["sbom"]["package_layers"]["lockfile_transitive"] > 0


def test_sbom_projection_lists_workspace_and_lockfile_transitive_packages() -> None:
    sbom = sbom_projection(Path.cwd())

    assert sbom["format"] == "SPDX-lite"
    assert sbom["truth"] == "pyproject-and-lockfile"
    assert sbom["lockfile"]["path"] == "uv.lock"
    assert sbom["lockfile"]["digest"].startswith("sha256:")
    package_names = {package["name"] for package in sbom["packages"]}
    assert package_names >= {"ethos", "ethos-core", "pytest"}
    assert any(
        package["name"] == "pytest" and package["layer"] == "lockfile_transitive"
        for package in sbom["packages"]
    )
    assert sbom["package_layers"]["workspace"] >= 2
    assert sbom["package_layers"]["lockfile_transitive"] > 0


def test_sbom_projection_handles_missing_and_irregular_lockfile_packages(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "packages" / "sample").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sample-root"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (root / "packages" / "sample" / "pyproject.toml").write_text(
        '[project]\nname = "sample"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )

    without_lock = sbom_projection(root)
    assert without_lock["lockfile"]["digest"] == ""
    assert without_lock["package_layers"]["lockfile_transitive"] == 0

    (root / "uv.lock").write_text(
        """
[[package]]
name = "editable"
version = "1.0.0"
source = { editable = "." }

[[package]]
name = ""
version = "1.0.0"

[[package]]
name = "alpha"
version = "2.0.0"
source = { registry = "https://example.test/simple" }
wheels = [
  { url = "alpha.whl", hash = "sha256:wheel" },
  "not-a-wheel"
]
sdist = { hash = "sha256:sdist" }

[[package]]
name = "beta"
version = "3.0.0"
wheels = "not-a-list"
sdist = "not-a-table"

[[package]]
name = "gamma"
version = "4.0.0"
wheels = [
  { url = "gamma.whl" }
]
""".lstrip(),
        encoding="utf-8",
    )

    with_lock = sbom_projection(root)
    transitive = [
        package for package in with_lock["packages"] if package["layer"] == "lockfile_transitive"
    ]

    assert [package["name"] for package in transitive] == ["alpha", "beta", "gamma"]
    assert transitive[0]["source"] == "https://example.test/simple"
    assert transitive[0]["hashes"] == ["sha256:wheel"]
    assert transitive[0]["sdist_hash"] == "sha256:sdist"
    assert "hashes" not in transitive[1]
    assert "sdist_hash" not in transitive[1]
    assert "hashes" not in transitive[2]


def test_sbom_projection_ignores_non_table_lockfile_entries(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sample-root"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (root / "uv.lock").write_text('package = ["not-a-table"]\n', encoding="utf-8")

    sbom = sbom_projection(root)

    assert sbom["package_layers"]["lockfile_transitive"] == 0
