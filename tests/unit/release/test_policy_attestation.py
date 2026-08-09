from __future__ import annotations

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
    "local_verification_command": _LOCAL["verification_command"],
    "local_installation_command": _LOCAL["installation_command"],
    "gitlab_remote": "origin",
    "gitlab_ci_surface": ".gitlab-ci.yml",
    "github_remote": "github",
    "github_ci_surface": ".github/workflows/verify.yml",
}
_REQUIRED_FILES = ("README.md", "LICENSE", "CONTRIBUTING.md", "CHANGELOG.md")
_RUNTIME = '[tool.sample]\ndistribution = "runtime-files"\nversion-source = "VERSION"\n'
_INVALID_IDENTITIES = [
    ("not-tool = true\n", None),
    (_RUNTIME.replace('"VERSION"', "1"), None),
    (_RUNTIME.replace("VERSION", "../VERSION"), "1"),
    (_RUNTIME, None),
    (_RUNTIME, "\n"),
    (_RUNTIME, b"\xff"),
    (_RUNTIME.replace("sample", "first") + "\n" + _RUNTIME.replace("sample", "second"), "1"),
]
_MISSING_LOCAL = [
    "publication_topology_local_verification_command_missing",
    "publication_topology_local_installation_command_missing",
    "publication_topology_gitlab_ci_surface_missing",
    "publication_topology_github_ci_surface_missing",
]
_DECLARATIONS = [
    ({"publication": {"remote": []}}, ["publication_topology_declaration_invalid"]),
    (
        {"publication": {"remotes": ["origin", "github"]}},
        ["publication_topology_declaration_invalid"],
    ),
    ({}, ["publication_topology_declaration_invalid"]),
    ({"publication": "invalid"}, ["publication_topology_declaration_invalid"]),
    (
        {"publication": {"gitlab_remote": "origin"}},
        ["publication_topology_github_remote_missing", *_MISSING_LOCAL],
    ),
    (
        {"publication": {}},
        [
            "publication_topology_gitlab_remote_missing",
            "publication_topology_github_remote_missing",
            *_MISSING_LOCAL,
        ],
    ),
    (
        {"publication": {"gitlab_remote": "origin", "github_remote": "origin"}},
        ["publication_topology_git_remotes_duplicate", *_MISSING_LOCAL],
    ),
]
_INVALID_PATHS = [
    ({"local_verification_command": ""}, "publication_topology_local_verification_command_missing"),
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
]
_HOST_SURFACES = """[host_profile]
provider = "gitlab"

[host_profile.surfaces]
ci = ".gitlab-ci.yml"
"""
_PROTECTED_REFS = """[protected_refs]
branches = ["main", "dev"]
tags = ["v*"]
"""


def _write(
    root: Path, path: str, content: str | bytes = "x\n", *, executable: bool = False
) -> Path:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content if isinstance(content, bytes) else content.encode())
    if executable:
        target.chmod(493)
    return target


def _root(tmp_path: Path, release: str = "", workspace: str = "", *surfaces: str) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root, "pyproject.toml", '[project]\nname = "sample"\nversion = "1.0.0"\n')
    if release:
        _write(root, ".ethos/release.toml", release)
        for path in (*_REQUIRED_FILES, *surfaces):
            _write(root, path)
    if workspace:
        _write(root, ".ethos/workspace.toml", workspace)
    return root


def _config(**updates: object) -> dict[str, object]:
    return {"publication": {**_PUBLICATION, **updates}}


def _fields(actual: dict[str, object], **expected: object) -> None:
    assert {key: actual[key] for key in expected} == expected


def test_release_inspection_reads_one_runtime_files_identity(tmp_path: Path) -> None:
    _write(tmp_path, "pyproject.toml", _RUNTIME)
    _write(tmp_path, "VERSION", "1.2.3\n")
    _fields(
        version_manifest(tmp_path),
        name="sample",
        version="1.2.3",
        tag="v1.2.3",
        packages={},
        required_gaps=[],
    )


@pytest.mark.parametrize(("workspace", "version"), _INVALID_IDENTITIES)
def test_release_inspection_rejects_unproved_identity(
    tmp_path: Path, workspace: str, version: str | bytes | None
) -> None:
    _write(tmp_path, "pyproject.toml", workspace)
    if version is not None:
        _write(tmp_path, "VERSION", version)
    assert version_manifest(tmp_path)["required_gaps"] == ["release_version_manifest_invalid"]


def test_release_policy_reports_invalid_toml_without_traceback(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _write(root, ".ethos/release.toml", "invalid\n")
    assert (
        "release_config_invalid:.ethos/release.toml" in release_policy_report(root)["required_gaps"]
    )


def test_version_manifest_and_release_policy_project_product_and_host_truth() -> None:
    root = Path.cwd()
    manifest, report, config = (
        version_manifest(root),
        release_policy_report(root),
        release_core.release_config(root),
    )
    _fields(
        manifest,
        version="0.1.0a2",
        tag="v0.1.0a2",
        all_package_versions_match=True,
        packages={"ethos": "0.1.0a2"},
    )
    _fields(
        report,
        verdict="pass",
        required_gaps=[],
        version=manifest,
        protected_refs={"branches": ["main", "dev"], "tags": ["v*"]},
    )
    assert "release" not in config
    assert "gitlab" not in report
    assert report["required_files"] == [*_REQUIRED_FILES, ".ethos/release.toml"]
    _fields(
        report["host_profile"],
        provider="gitlab",
        layer="profile_config",
        surfaces={
            "ci": ".gitlab-ci.yml",
            "merge_request_template": ".gitlab/merge_request_templates/default.md",
            "issue_template": ".gitlab/issue_templates/task.md",
        },
    )
    topology = report["publication_topology"]
    _fields(topology, state="ready", local=_LOCAL)
    assert "legacy" not in topology
    assert (
        topology["gitlab"]["capabilities"]
        == topology["github"]["capabilities"]
        == ["repository", "ci_cd", "publication"]
    )
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
    root = _root(tmp_path)
    if kind == "not_executable":
        _write(root, command, "#!/bin/sh\n")
    elif kind == "not_regular":
        (root / command).mkdir()
    elif kind == "escape":
        _write(tmp_path, "outside.sh", "#!/bin/sh\n", executable=True)
    monkeypatch.setattr(
        release_core,
        "publication_topology",
        lambda _root, _config: {"local": {"installation_command": command}, "required_gaps": ()},
    )
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
    _fields(release_policy_report(Path.cwd()), verdict="pass", required_gaps=[])


def test_release_policy_rejects_unequal_remote_capability_declaration(tmp_path: Path) -> None:
    root = Path.cwd()
    scratch = _root(
        tmp_path,
        (root / ".ethos/release.toml")
        .read_text()
        .replace('github_remote = "github"', 'github_remote = "origin"', 1),
    )
    for path in (*_REQUIRED_FILES, "pyproject.toml", ".ethos/workspace.toml"):
        _write(scratch, path, (root / path).read_text())
    assert release_policy_report(root)["publication_topology"]["state"] == "ready"
    assert (
        "publication_topology_git_remotes_duplicate"
        in release_policy_report(scratch)["required_gaps"]
    )


@pytest.mark.parametrize(("declaration", "gaps"), _DECLARATIONS)
def test_release_topology_rejects_invalid_declarations(
    declaration: dict[str, object], gaps: list[str]
) -> None:
    _fields(publication_topology(Path.cwd(), declaration), state="invalid", required_gaps=gaps)


def test_release_topology_enforces_invalid_declaration_without_bypass() -> None:
    topology = publication_topology(Path.cwd(), {"publication": {"remotes": ["origin", "github"]}})
    admission = publication_branch_admission(
        topology,
        branch="dev",
        candidate_branch="candidate/dev",
        remote_name="origin",
        enforce=False,
    )
    assert admission["enforcement_gaps"] == ["publication_topology_declaration_invalid"]


def test_release_topology_uses_declared_repository_native_commands_and_ci_surfaces(
    tmp_path: Path,
) -> None:
    for path in ("dev/verify", "dev/install"):
        _write(tmp_path, path, "#!/bin/sh\n", executable=True)
    for path in (".gitlab-ci.yml", ".github/workflows/verify.yml"):
        _write(tmp_path, path, "jobs: {}\n")
    topology = publication_topology(
        tmp_path,
        _config(local_verification_command="dev/verify", local_installation_command="dev/install"),
    )
    _fields(topology, state="ready")
    _fields(
        topology["local"], verification_command="dev/verify", installation_command="dev/install"
    )
    assert topology["gitlab"]["ci_surface"] == ".gitlab-ci.yml"
    assert topology["github"]["ci_surface"] == ".github/workflows/verify.yml"


@pytest.mark.parametrize(("updates", "gap"), _INVALID_PATHS)
def test_release_topology_rejects_invalid_declared_paths(
    tmp_path: Path, updates: dict[str, object], gap: str
) -> None:
    assert gap in publication_topology(tmp_path, _config(**updates))["required_gaps"]


def test_release_policy_uses_configured_branch_roles_for_protected_refs(tmp_path: Path) -> None:
    release = """[release]
version_source = "pyproject.toml"
tag_pattern = "v{version}"
artifact_glob = "dist/*"

[protected_refs]
branches = ["release", "integration"]
tags = ["v*"]

[host_profile]
provider = "gitlab"

[host_profile.surfaces]
ci = ".gitlab-ci.yml"
merge_request_template = ".gitlab/merge_request_templates/default.md"
issue_template = ".gitlab/issue_templates/task.md"

[attestation]
formats = ["spdx-2.3-json"]
signing = "provider-native"
"""
    workspace = """[branch_roles]
release_branch = "release"
accepted_branch = "integration"
candidate_branch = "stage/integration"
work_branch_prefix = "lane/"
proposal_branch_prefix = "review/"
"""
    root = _root(
        tmp_path,
        release,
        workspace,
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
    )
    report = release_policy_report(root)
    assert "protected_branches_policy_missing" not in report["required_gaps"]
    assert report["protected_refs"]["branches"] == ["release", "integration"]
    assert report["host_profile"]["provider"] == "gitlab"


@pytest.mark.parametrize(
    ("release", "expected", "gap"),
    [
        (
            _PROTECTED_REFS
            + """\n[gitlab]
ci = ".gitlab-ci.yml"

[attestation]
formats = ["spdx-2.3-json"]
""",
            {"provider": "", "layer": "profile_config", "surfaces": {}},
            "",
        ),
        (
            _PROTECTED_REFS
            + _HOST_SURFACES
            + """\n[attestation]
formats = ["spdx-2.3-json"]
""",
            None,
            "host_surface_missing:gitlab:ci:.gitlab-ci.yml",
        ),
    ],
)
def test_release_policy_separates_host_profile_from_product_files(
    tmp_path: Path, release: str, expected: dict[str, object] | None, gap: str
) -> None:
    report = release_policy_report(_root(tmp_path, release))
    if expected is not None:
        assert report["host_profile"] == expected
    else:
        assert "release_file_missing:.gitlab-ci.yml" not in report["required_gaps"]
        assert gap in report["required_gaps"]
