from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import ethos.repository.release.configuration as release_core
from ethos.repository.policy.coupling.release import release_report
from ethos.repository.release.attestation import release_attestation
from ethos.repository.release.attestation import sbom_projection
from ethos.repository.release.configuration import release_policy_report
from ethos.repository.release.configuration import version_manifest
from ethos.repository.release.publication import publication_branch_admission
from ethos.repository.release.publication import publication_topology

_LOCAL = {
    "id": "local",
    "role": "local_verification_install",
    "mode": "offline",
    "verification_command": "tools/ci/scripts/run-local-ci.sh",
    "installation_command": "tools/ci/scripts/run-local-install-smoke.sh",
}


def _assert_fields(actual: dict[str, object], **expected: object) -> None:
    assert {key: actual[key] for key in expected} == expected


def test_release_coupling_requires_an_explicit_release_owner(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "profile.toml").write_text(
        'profile_id = "runtime-files-adopter"\n', encoding="utf-8"
    )
    (tmp_path / ".ethos" / "release.toml").write_text(
        '[protected_refs]\nbranches = ["main"]\ntags = ["v*"]\n', encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[tool.sample]\ndistribution = "runtime-files"\nversion-source = "VERSION"\n',
        encoding="utf-8",
    )

    report = release_report(tmp_path)

    assert report["required_gaps"] == []
    assert "version" not in report


def test_adopter_gate_registry_is_not_a_product_release_owner(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "profile.toml").write_text(
        'profile_id = "runtime-files-adopter"\n\n[proof]\ngate_registry = "gates.toml"\n',
        encoding="utf-8",
    )
    (tmp_path / ".ethos" / "release.toml").write_text(
        '[protected_refs]\nbranches = ["main"]\ntags = ["v*"]\n', encoding="utf-8"
    )
    (tmp_path / "gates.toml").write_text("adopter-owned\n", encoding="utf-8")

    report = release_report(tmp_path)

    assert report["required_gaps"] == []
    assert "version" not in report


def test_release_inspection_reads_one_runtime_files_identity(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.sample]\ndistribution = "runtime-files"\nversion-source = "VERSION"\n',
        encoding="utf-8",
    )
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")

    manifest = version_manifest(tmp_path)

    _assert_fields(
        manifest,
        name="sample",
        version="1.2.3",
        tag="v1.2.3",
        packages={},
        required_gaps=[],
    )


@pytest.mark.parametrize(
    ("workspace", "version"),
    [
        ("not-tool = true\n", None),
        ('[tool.sample]\ndistribution = "runtime-files"\nversion-source = 1\n', None),
        ('[tool.sample]\ndistribution = "runtime-files"\nversion-source = "../VERSION"\n', "1"),
        ('[tool.sample]\ndistribution = "runtime-files"\nversion-source = "VERSION"\n', None),
        ('[tool.sample]\ndistribution = "runtime-files"\nversion-source = "VERSION"\n', "\n"),
        ('[tool.sample]\ndistribution = "runtime-files"\nversion-source = "VERSION"\n', b"\xff"),
        (
            (
                '[tool.first]\ndistribution = "runtime-files"\nversion-source = "VERSION"\n\n'
                '[tool.second]\ndistribution = "runtime-files"\nversion-source = "VERSION"\n'
            ),
            "1",
        ),
    ],
)
def test_release_inspection_rejects_unproved_identity(
    tmp_path: Path, workspace: str, version: str | bytes | None
) -> None:
    (tmp_path / "pyproject.toml").write_text(workspace, encoding="utf-8")
    if isinstance(version, bytes):
        (tmp_path / "VERSION").write_bytes(version)
    elif version is not None:
        (tmp_path / "VERSION").write_text(version, encoding="utf-8")

    assert version_manifest(tmp_path)["required_gaps"] == ["release_version_manifest_invalid"]


def test_release_policy_reports_invalid_toml_without_traceback(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "release.toml").write_text("invalid\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "sample"\nversion = "1.0.0"\n', encoding="utf-8"
    )

    assert (
        "release_config_invalid:.ethos/release.toml"
        in release_policy_report(tmp_path)["required_gaps"]
    )


def _minimal_release_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sample"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    return root


def _topology(monkeypatch: pytest.MonkeyPatch, command: str, gaps: object = ()) -> None:
    monkeypatch.setattr(
        release_core,
        "publication_topology",
        lambda _config: {"local": {"installation_command": command}, "required_gaps": gaps},
    )


def _policy_root(
    tmp_path: Path, release: str, *, workspace: str = "", surfaces: tuple[str, ...] = ()
) -> Path:
    root = _minimal_release_root(tmp_path)
    (root / ".ethos").mkdir()
    for path in ("README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md", *surfaces):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    (root / ".ethos" / "release.toml").write_text(release, encoding="utf-8")
    if workspace:
        (root / ".ethos" / "workspace.toml").write_text(workspace, encoding="utf-8")
    return root


def test_version_manifest_and_release_policy_project_product_and_host_truth() -> None:
    manifest, report, config = (
        version_manifest(Path.cwd()),
        release_policy_report(Path.cwd()),
        release_core.release_config(Path.cwd()),
    )
    _assert_fields(
        manifest,
        version="0.1.0a2",
        tag="v0.1.0a2",
        all_package_versions_match=True,
        packages={"ethos": "0.1.0a2"},
    )
    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert release_report(Path.cwd())["version"] == manifest
    assert "release" not in config
    assert "gitlab" not in report
    assert report["version"]["tag"] == manifest["tag"]
    assert report["required_files"] == [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        ".ethos/release.toml",
    ]
    assert report["host_profile"] == {
        "provider": "gitlab",
        "layer": "profile_config",
        "surfaces": {
            "ci": ".gitlab-ci.yml",
            "merge_request_template": ".gitlab/merge_request_templates/default.md",
            "issue_template": ".gitlab/issue_templates/task.md",
        },
    }
    assert report["protected_refs"] == {"branches": ["main", "dev"], "tags": ["v*"]}
    topology = report["publication_topology"]
    assert topology["state"] == "ready"
    assert "legacy" not in topology
    assert topology["local"] == _LOCAL
    assert topology["gitlab"]["capabilities"] == topology["github"]["capabilities"]
    assert topology["gitlab"]["capabilities"] == ["repository", "ci_cd", "publication"]
    assert topology["gitlab"]["git_remote"] != topology["github"]["git_remote"]


@pytest.mark.parametrize(
    ("kind", "command", "gap"),
    [
        (
            "missing",
            "tools/ci/scripts/missing.sh",
            "release_local_command_missing:installation_command:tools/ci/scripts/missing.sh",
        ),
        (
            "not_executable",
            "owner.sh",
            "release_local_command_not_executable:installation_command:owner.sh",
        ),
        ("not_regular", "owner", "release_local_command_not_regular:installation_command:owner"),
        (
            "escape",
            "../outside.sh",
            "release_local_command_path_escape:installation_command:../outside.sh",
        ),
    ],
)
def test_release_policy_rejects_invalid_local_install_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, command: str, gap: str
) -> None:
    root = _minimal_release_root(tmp_path)
    if kind == "not_executable":
        (root / command).write_text("#!/bin/sh\n", encoding="utf-8")
        (root / command).chmod(0o644)
    elif kind == "not_regular":
        (root / command).mkdir()
    elif kind == "escape":
        outside = tmp_path / "outside.sh"
        outside.write_text("#!/bin/sh\n", encoding="utf-8")
        outside.chmod(0o755)
    _topology(monkeypatch, command)
    report = release_policy_report(root)
    assert report["verdict"] == "block"
    assert gap in report["required_gaps"]


def test_release_policy_ignores_malformed_publication_gap_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        release_core,
        "publication_topology",
        lambda _config: {"local": _LOCAL, "required_gaps": "malformed"},
    )
    report = release_policy_report(Path.cwd())
    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []


def test_release_policy_rejects_unequal_remote_capability_declaration() -> None:
    root = Path.cwd()
    config = (root / ".ethos" / "release.toml").read_text(encoding="utf-8")
    scratch = root / "build" / "runtime" / "dual-remote-policy-test"
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        (scratch / ".ethos").mkdir(exist_ok=True)
        (scratch / ".ethos" / "release.toml").write_text(
            config.replace(
                'gitlab_remote = "origin"\ngithub_remote = "github"',
                'gitlab_remote = "origin"\ngithub_remote = "origin"',
                1,
            ),
            encoding="utf-8",
        )
        for path in (
            "README.md",
            "LICENSE",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "pyproject.toml",
            ".ethos/workspace.toml",
        ):
            target = scratch / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((root / path).read_text(encoding="utf-8"), encoding="utf-8")
        invalid = release_policy_report(scratch)
    finally:
        shutil.rmtree(scratch)
    assert release_policy_report(root)["publication_topology"]["state"] == "ready"
    assert "publication_topology_git_remotes_duplicate" in invalid["required_gaps"]


@pytest.mark.parametrize(
    ("declaration", "gaps"),
    [
        ({"publication": {"remote": []}}, ["publication_topology_declaration_invalid"]),
        (
            {"publication": {"remotes": ["origin", "github"]}},
            ["publication_topology_declaration_invalid"],
        ),
        ({}, ["publication_topology_declaration_invalid"]),
        ({"publication": "invalid"}, ["publication_topology_declaration_invalid"]),
        (
            {"publication": {"gitlab_remote": "origin"}},
            ["publication_topology_github_remote_missing"],
        ),
        (
            {"publication": {}},
            [
                "publication_topology_gitlab_remote_missing",
                "publication_topology_github_remote_missing",
            ],
        ),
        (
            {"publication": {"gitlab_remote": "origin", "github_remote": "origin"}},
            ["publication_topology_git_remotes_duplicate"],
        ),
    ],
)
def test_release_topology_rejects_invalid_declarations(
    declaration: dict[str, object], gaps: list[str]
) -> None:
    topology = publication_topology(declaration)
    assert topology["state"] == "invalid"
    assert topology["required_gaps"] == gaps


def test_release_topology_enforces_invalid_declaration_without_bypass() -> None:
    admission = publication_branch_admission(
        publication_topology({"publication": {"remotes": ["origin", "github"]}}),
        branch="dev",
        candidate_branch="candidate/dev",
        remote_name="origin",
        enforce=False,
    )
    assert admission["enforcement_gaps"] == ["publication_topology_declaration_invalid"]


def test_release_policy_uses_configured_branch_roles_for_protected_refs(tmp_path: Path) -> None:
    release = (
        '[release]\nversion_source = "pyproject.toml"\ntag_pattern = "v{version}"\n'
        'artifact_glob = "dist/*"\n\n[protected_refs]\nbranches = ["release", "integration"]\n'
        'tags = ["v*"]\n\n[host_profile]\nprovider = "gitlab"\n\n[host_profile.surfaces]\n'
        'ci = ".gitlab-ci.yml"\nmerge_request_template = ".gitlab/merge_request_templates/default.md"\n'
        'issue_template = ".gitlab/issue_templates/task.md"\n\n[attestation]\n'
        'formats = ["in-toto-shaped", "slsa-shaped", "spdx-lite"]\nsigning = "git-ssh"\n'
    )
    workspace = (
        '[branch_roles]\nrelease_branch = "release"\naccepted_branch = "integration"\n'
        'candidate_branch = "stage/integration"\nwork_branch_prefix = "lane/"\n'
        'proposal_branch_prefix = "review/"\n'
    )
    root = _policy_root(
        tmp_path,
        release,
        workspace=workspace,
        surfaces=(
            ".gitlab-ci.yml",
            ".gitlab/merge_request_templates/default.md",
            ".gitlab/issue_templates/task.md",
        ),
    )
    report = release_policy_report(root)
    assert "protected_branches_policy_missing" not in report["required_gaps"]
    assert report["protected_refs"]["branches"] == ["release", "integration"]
    assert report["host_profile"]["provider"] == "gitlab"


@pytest.mark.parametrize(
    ("release", "expected", "gap"),
    [
        (
            '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n[gitlab]\nci = ".gitlab-ci.yml"\n\n[attestation]\nformats = ["in-toto-shaped", "slsa-shaped", "spdx-lite"]\n',
            {"provider": "", "layer": "profile_config", "surfaces": {}},
            "",
        ),
        (
            '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n[host_profile]\nprovider = "gitlab"\n\n[host_profile.surfaces]\nci = ".gitlab-ci.yml"\n\n[attestation]\nformats = ["in-toto-shaped", "slsa-shaped", "spdx-lite"]\n',
            None,
            "host_surface_missing:gitlab:ci:.gitlab-ci.yml",
        ),
    ],
)
def test_release_policy_separates_host_profile_from_product_files(
    tmp_path: Path, release: str, expected: dict[str, object] | None, gap: str
) -> None:
    report = release_policy_report(_policy_root(tmp_path, release))
    if expected is not None:
        assert report["host_profile"] == expected
    else:
        assert "release_file_missing:.gitlab-ci.yml" not in report["required_gaps"]
        assert gap in report["required_gaps"]


def test_release_attestation_and_sbom_project_workspace_truth() -> None:
    attestation, sbom = (
        release_attestation(root=Path.cwd(), head="abc123", evidence_digest="deadbeef"),
        sbom_projection(Path.cwd()),
    )
    assert attestation["_type"] == "https://in-toto.io/Statement/v1"
    assert attestation["predicateType"].endswith("/ethos-release/v1")
    assert attestation["predicate"]["slsa"]["builder"]["id"] == "ethos"
    assert attestation["subject"][0]["name"] == "ethos@0.1.0a2"
    materials = {material["uri"] for material in attestation["predicate"]["slsa"]["materials"]}
    assert {"git+repository", "ethos+evidence", "file+uv.lock", "ethos+sbom"} <= materials
    assert attestation["predicate"]["sbom"]["lockfile"]["path"] == "uv.lock"
    assert attestation["predicate"]["sbom"]["package_layers"]["lockfile_transitive"] > 0
    assert sbom["format"] == "SPDX-lite"
    assert sbom["truth"] == "pyproject-and-lockfile"
    assert sbom["lockfile"]["path"] == "uv.lock"
    assert sbom["lockfile"]["digest"].startswith("sha256:")
    assert {"ethos", "pytest"} <= {package["name"] for package in sbom["packages"]}
    assert any(
        package["name"] == "pytest" and package["layer"] == "lockfile_transitive"
        for package in sbom["packages"]
    )
    assert sbom["package_layers"]["workspace"] == 1
    assert sbom["package_layers"]["lockfile_transitive"] > 0


def test_sbom_projection_handles_missing_irregular_and_non_table_lockfile_packages(
    tmp_path: Path,
) -> None:
    root = _minimal_release_root(tmp_path)
    without_lock = sbom_projection(root)
    assert without_lock["lockfile"]["digest"] == ""
    assert without_lock["package_layers"]["lockfile_transitive"] == 0
    (root / "uv.lock").write_text(
        '[[package]]\nname = "editable"\nversion = "1.0.0"\nsource = { editable = "." }\n\n'
        '[[package]]\nname = ""\nversion = "1.0.0"\n\n[[package]]\nname = "alpha"\n'
        'version = "2.0.0"\nsource = { registry = "https://example.test/simple" }\n'
        'wheels = [{ url = "alpha.whl", hash = "sha256:wheel" }, "not-a-wheel"]\n'
        'sdist = { hash = "sha256:sdist" }\n\n[[package]]\nname = "beta"\nversion = "3.0.0"\n'
        'wheels = "not-a-list"\nsdist = "not-a-table"\n\n[[package]]\nname = "gamma"\n'
        'version = "4.0.0"\nwheels = [{ url = "gamma.whl" }]\n',
        encoding="utf-8",
    )
    packages = [
        package
        for package in sbom_projection(root)["packages"]
        if package["layer"] == "lockfile_transitive"
    ]
    assert [package["name"] for package in packages] == ["alpha", "beta", "gamma"]
    _assert_fields(
        packages[0],
        name="alpha",
        version="2.0.0",
        layer="lockfile_transitive",
        source="https://example.test/simple",
        hashes=["sha256:wheel"],
        sdist_hash="sha256:sdist",
    )
    assert "hashes" not in packages[1]
    assert "sdist_hash" not in packages[1]
    assert "hashes" not in packages[2]
    (root / "uv.lock").write_text('package = ["not-a-table"]\n', encoding="utf-8")
    assert sbom_projection(root)["package_layers"]["lockfile_transitive"] == 0
