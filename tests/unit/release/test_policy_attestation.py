from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import ethos.repository.release.configuration as release_core
from ethos.repository.release.configuration import release_policy_report
from ethos.repository.release.configuration import version_manifest
from ethos.repository.release.publication import publication_branch_admission
from ethos.repository.release.publication import publication_topology

_LOCAL = {
    "id": "local",
    "role": "local_verification_install",
    "mode": "offline",
    "verification_command": "uv run --frozen --offline python -m nox -s local_ci",
    "installation_command": "uv run --frozen --offline python -m nox -s install_smoke",
}

_PUBLICATION = {
    "local_verification_command": "uv run --frozen --offline python -m nox -s local_ci",
    "local_installation_command": "uv run --frozen --offline python -m nox -s install_smoke",
    "gitlab_remote": "origin",
    "gitlab_ci_surface": ".gitlab-ci.yml",
    "github_remote": "github",
    "github_ci_surface": ".github/workflows/verify.yml",
}


def _publication_config(**updates: object) -> dict[str, object]:
    return {"publication": {**_PUBLICATION, **updates}}


def _assert_fields(actual: dict[str, object], **expected: object) -> None:
    assert {key: actual[key] for key in expected} == expected


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
        lambda _root, _config: {"local": {"installation_command": command}, "required_gaps": gaps},
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
    assert release_policy_report(Path.cwd())["version"] == manifest
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
        lambda _root, _config: {"local": _LOCAL, "required_gaps": "malformed"},
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
                'github_remote = "github"',
                'github_remote = "origin"',
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
            [
                "publication_topology_github_remote_missing",
                "publication_topology_local_verification_command_missing",
                "publication_topology_local_installation_command_missing",
                "publication_topology_gitlab_ci_surface_missing",
                "publication_topology_github_ci_surface_missing",
            ],
        ),
        (
            {"publication": {}},
            [
                "publication_topology_gitlab_remote_missing",
                "publication_topology_github_remote_missing",
                "publication_topology_local_verification_command_missing",
                "publication_topology_local_installation_command_missing",
                "publication_topology_gitlab_ci_surface_missing",
                "publication_topology_github_ci_surface_missing",
            ],
        ),
        (
            {"publication": {"gitlab_remote": "origin", "github_remote": "origin"}},
            [
                "publication_topology_git_remotes_duplicate",
                "publication_topology_local_verification_command_missing",
                "publication_topology_local_installation_command_missing",
                "publication_topology_gitlab_ci_surface_missing",
                "publication_topology_github_ci_surface_missing",
            ],
        ),
    ],
)
def test_release_topology_rejects_invalid_declarations(
    declaration: dict[str, object], gaps: list[str]
) -> None:
    topology = publication_topology(Path.cwd(), declaration)
    assert topology["state"] == "invalid"
    assert topology["required_gaps"] == gaps


def test_release_topology_enforces_invalid_declaration_without_bypass() -> None:
    admission = publication_branch_admission(
        publication_topology(Path.cwd(), {"publication": {"remotes": ["origin", "github"]}}),
        branch="dev",
        candidate_branch="candidate/dev",
        remote_name="origin",
        enforce=False,
    )
    assert admission["enforcement_gaps"] == ["publication_topology_declaration_invalid"]


def test_release_topology_uses_declared_repository_native_commands_and_ci_surfaces(
    tmp_path: Path,
) -> None:
    verification = tmp_path / "dev" / "verify"
    installation = tmp_path / "dev" / "install"
    gitlab = tmp_path / ".gitlab-ci.yml"
    github = tmp_path / ".github" / "workflows" / "verify.yml"
    for command in (verification, installation):
        command.parent.mkdir(parents=True, exist_ok=True)
        command.write_text("#!/bin/sh\n", encoding="utf-8")
        command.chmod(0o755)
    for surface in (gitlab, github):
        surface.parent.mkdir(parents=True, exist_ok=True)
        surface.write_text("jobs: {}\n", encoding="utf-8")

    topology = publication_topology(
        tmp_path,
        _publication_config(
            local_verification_command="dev/verify",
            local_installation_command="dev/install",
        ),
    )

    assert topology["state"] == "ready"
    assert topology["local"]["verification_command"] == "dev/verify"
    assert topology["local"]["installation_command"] == "dev/install"
    assert topology["gitlab"]["ci_surface"] == ".gitlab-ci.yml"
    assert topology["github"]["ci_surface"] == ".github/workflows/verify.yml"


@pytest.mark.parametrize(
    ("updates", "gap"),
    [
        (
            {"local_verification_command": ""},
            "publication_topology_local_verification_command_missing",
        ),
        (
            {"local_installation_command": "../install"},
            "publication_topology_local_installation_command_path_escape:../install",
        ),
        (
            {"local_verification_command": "missing"},
            "publication_topology_local_verification_command_missing:missing",
        ),
        (
            {"github_ci_surface": "/tmp/verify.yml"},
            "publication_topology_github_ci_surface_path_escape:/tmp/verify.yml",
        ),
        (
            {"gitlab_ci_surface": "missing.yml"},
            "publication_topology_gitlab_ci_surface_missing:missing.yml",
        ),
    ],
)
def test_release_topology_rejects_invalid_declared_paths(
    tmp_path: Path, updates: dict[str, object], gap: str
) -> None:
    topology = publication_topology(tmp_path, _publication_config(**updates))

    assert gap in topology["required_gaps"]


def test_release_policy_uses_configured_branch_roles_for_protected_refs(tmp_path: Path) -> None:
    release = (
        '[release]\nversion_source = "pyproject.toml"\ntag_pattern = "v{version}"\n'
        'artifact_glob = "dist/*"\n\n[protected_refs]\nbranches = ["release", "integration"]\n'
        'tags = ["v*"]\n\n[host_profile]\nprovider = "gitlab"\n\n[host_profile.surfaces]\n'
        'ci = ".gitlab-ci.yml"\nmerge_request_template = ".gitlab/merge_request_templates/default.md"\n'
        'issue_template = ".gitlab/issue_templates/task.md"\n\n[attestation]\n'
        'formats = ["spdx-2.3-json"]\nsigning = "provider-native"\n'
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
            '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n[gitlab]\nci = ".gitlab-ci.yml"\n\n[attestation]\nformats = ["spdx-2.3-json"]\n',
            {"provider": "", "layer": "profile_config", "surfaces": {}},
            "",
        ),
        (
            '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n[host_profile]\nprovider = "gitlab"\n\n[host_profile.surfaces]\nci = ".gitlab-ci.yml"\n\n[attestation]\nformats = ["spdx-2.3-json"]\n',
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
