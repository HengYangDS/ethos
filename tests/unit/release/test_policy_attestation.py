from __future__ import annotations

from pathlib import Path

import pytest

import ethos.repository.release.configuration as release_core
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.publication import PublicationEffect
from ethos.contracts.publication import PublicationTarget
from ethos.repository.release.configuration import release_policy_report
from ethos.repository.release.configuration import version_manifest
from ethos.repository.release.publication import publication_ref_admission
from ethos.repository.release.publication import publication_topology
from ethos.repository.release.publication import topology_remotes
from tests.support.literal_cases import literal_case

_LOCAL = literal_case("release.test_policy_attestation:assign:_LOCAL:0")
_PUBLICATION = {
    "local_verification_command": "uv run --frozen --offline python -m nox -s local_ci",
    "local_installation_command": "uv run --frozen --offline python -m nox -s install_smoke",
    "peers": [
        {
            "id": "gitlab",
            "provider": "gitlab",
            "role": "organization_collaboration",
            "git_remote": "origin",
            "capabilities": ["repository", "ci_cd", "publication"],
            "ci_surface": ".gitlab-ci.yml",
        },
        {
            "id": "github",
            "provider": "github",
            "role": "public_distribution",
            "git_remote": "github",
            "capabilities": ["repository", "ci_cd", "publication"],
            "ci_surface": ".github/workflows/verify.yml",
        },
    ],
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
_MISSING_LOCAL = literal_case("release.test_policy_attestation:assign:_MISSING_LOCAL:1")
_DECLARATIONS = [
    ({"publication": {"remote": []}}, ["publication_topology_declaration_invalid"]),
    ({"publication": {"remotes": ["origin"]}}, ["publication_topology_declaration_invalid"]),
    ({}, ["publication_topology_declaration_invalid"]),
    ({"publication": "invalid"}, ["publication_topology_declaration_invalid"]),
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


def _declared_publication(*peers: dict[str, object]) -> dict[str, object]:
    return {
        "publication": {
            "local_verification_command": "dev/verify",
            "local_installation_command": "dev/install",
            "peers": list(peers),
        }
    }


def _peer(
    peer_id: str,
    provider: str,
    remote: str,
    *,
    capabilities: tuple[str, ...] = ("repository", "publication"),
    ci_surface: str | None = None,
) -> dict[str, object]:
    peer: dict[str, object] = {
        "id": peer_id,
        "provider": provider,
        "role": "organization_collaboration",
        "git_remote": remote,
        "capabilities": list(capabilities),
    }
    if ci_surface is not None:
        peer["ci_surface"] = ci_surface
    return peer


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
    peers = {peer["id"]: peer for peer in topology["remotes"]}
    assert {peer["git_remote"] for peer in peers.values()} == {"origin", "github"}
    assert all(
        peer["capabilities"] == ["repository", "ci_cd", "publication"] for peer in peers.values()
    )
    assert not ({"gitlab", "github"} & set(topology))


def test_release_policy_ignores_malformed_publication_gap_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        release_core,
        "publication_topology",
        lambda _root, _config: {"local": _LOCAL, "required_gaps": "malformed"},
    )
    _fields(release_policy_report(Path.cwd()), verdict="pass", required_gaps=[])


def test_release_policy_rejects_duplicate_remote_declaration(tmp_path: Path) -> None:
    root = Path.cwd()
    scratch = _root(
        tmp_path,
        (root / ".ethos/release.toml")
        .read_text()
        .replace('git_remote = "github"', 'git_remote = "origin"', 1),
    )
    for path in (*_REQUIRED_FILES, "pyproject.toml", ".ethos/workspace.toml"):
        _write(scratch, path, (root / path).read_text())
    assert release_policy_report(root)["publication_topology"]["state"] == "ready"
    assert (
        "publication_topology_peer_git_remote_duplicate:origin"
        in release_policy_report(scratch)["required_gaps"]
    )


@pytest.mark.parametrize(("declaration", "gaps"), _DECLARATIONS)
def test_release_topology_rejects_invalid_declarations(
    declaration: dict[str, object], gaps: list[str]
) -> None:
    _fields(publication_topology(Path.cwd(), declaration), state="invalid", required_gaps=gaps)


def test_release_topology_enforces_invalid_declaration_without_bypass() -> None:
    topology = publication_topology(Path.cwd(), {"publication": {"remotes": ["origin", "github"]}})
    admission = publication_ref_admission(
        topology,
        policy=BranchRolePolicy(),
        target_ref="refs/heads/dev",
        release_tags=("v*",),
        remote_name="origin",
    )
    assert admission["enforcement_gaps"] == ["publication_topology_declaration_invalid"]


@pytest.mark.parametrize(
    ("target_ref", "ref_kind", "role", "state"),
    [
        ("refs/heads/dev", "branch", "accepted_root", "eligible"),
        ("refs/heads/main", "branch", "release_root", "eligible"),
        ("refs/heads/proposal/topic", "branch", "proposal_lane", "eligible"),
        ("refs/tags/v1.2.3", "tag", "release_publication", "eligible"),
        ("refs/heads/candidate/dev", "branch", "candidate", "unavailable"),
        ("refs/heads/work/topic", "branch", "work_lane", "unavailable"),
        ("refs/tags/nightly", "tag", "other", "unavailable"),
    ],
)
def test_release_topology_admits_only_positive_full_ref_roles(
    tmp_path: Path,
    target_ref: str,
    ref_kind: str,
    role: str,
    state: str,
) -> None:
    for path in ("dev/verify", "dev/install"):
        _write(tmp_path, path, "#!/bin/sh\n", executable=True)
    topology = publication_topology(
        tmp_path,
        _declared_publication(_peer("gitlab", "gitlab", "origin")),
    )

    admission = publication_ref_admission(
        topology,
        policy=BranchRolePolicy(),
        target_ref=target_ref,
        release_tags=("v*",),
        remote_name="origin",
    )

    assert admission["target_ref"] == target_ref
    assert admission["ref_kind"] == ref_kind
    assert admission["role"] == role
    assert admission["allowed_effect"] == (
        "git.ref.compare-and-swap" if state == "eligible" else ""
    )
    assert admission["state"] == state
    assert admission["remote_mutation_allowed"] is (state == "eligible")
    assert admission["enforcement_gaps"] == (
        []
        if state == "eligible"
        else [f"publication_ref_unavailable:{ref_kind}:{role}:{target_ref}"]
    )


def test_publication_effect_owns_exact_full_ref_cas() -> None:
    target = PublicationTarget(
        id="gitlab",
        remote="origin",
        target_ref="refs/tags/v1.2.3",
        expected="0" * 40,
        desired="1" * 40,
    )

    effect = PublicationEffect.compile(
        repository_common_dir="/repo/.git",
        source_object="1" * 40,
        targets=(target,),
    )

    assert effect.operation == "git.ref.compare-and-swap"
    assert effect.source_object == "1" * 40
    assert effect.targets == (target,)


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
    assert {peer["id"]: peer["ci_surface"] for peer in topology["remotes"]} == {
        "gitlab": ".gitlab-ci.yml",
        "github": ".github/workflows/verify.yml",
    }


@pytest.mark.parametrize(
    ("peers", "expected"),
    [
        ((), {}),
        ((_peer("gitlab", "gitlab", "origin"),), {"gitlab": "origin"}),
        ((_peer("github", "github", "github"),), {"github": "github"}),
        (
            (
                _peer("gitlab", "gitlab", "origin"),
                _peer("github", "github", "github"),
            ),
            {"gitlab": "origin", "github": "github"},
        ),
    ],
    ids=("local-only", "local-gitlab", "local-github", "local-dual-remote"),
)
def test_release_topology_supports_every_declared_peer_cardinality(
    tmp_path: Path,
    peers: tuple[dict[str, object], ...],
    expected: dict[str, str],
) -> None:
    for path in ("dev/verify", "dev/install"):
        _write(tmp_path, path, "#!/bin/sh\n", executable=True)

    topology = publication_topology(tmp_path, _declared_publication(*peers))

    _fields(topology, state="ready", required_gaps=[])
    assert topology_remotes(topology) == expected
    assert [peer["id"] for peer in topology["remotes"]] == list(expected)
    assert not ({"gitlab", "github"} & set(topology))


@pytest.mark.parametrize("field", ["id", "git_remote"])
def test_release_topology_rejects_duplicate_peer_identity(tmp_path: Path, field: str) -> None:
    for path in ("dev/verify", "dev/install"):
        _write(tmp_path, path, "#!/bin/sh\n", executable=True)
    left = _peer("gitlab", "gitlab", "origin")
    right = _peer("github", "github", "github")
    right[field] = left[field]

    topology = publication_topology(tmp_path, _declared_publication(left, right))

    assert topology["state"] == "invalid"
    assert f"publication_topology_peer_{field}_duplicate:{left[field]}" in topology["required_gaps"]


def test_release_topology_allows_multiple_peers_from_one_provider(tmp_path: Path) -> None:
    for path in ("dev/verify", "dev/install"):
        _write(tmp_path, path, "#!/bin/sh\n", executable=True)

    topology = publication_topology(
        tmp_path,
        _declared_publication(
            _peer("gitlab-internal", "gitlab", "origin"),
            _peer("gitlab-public", "gitlab", "public"),
        ),
    )

    _fields(topology, state="ready", required_gaps=[])
    assert topology_remotes(topology) == {
        "gitlab-internal": "origin",
        "gitlab-public": "public",
    }


def test_release_topology_rejects_legacy_scalar_with_declared_peers(tmp_path: Path) -> None:
    for path in ("dev/verify", "dev/install"):
        _write(tmp_path, path, "#!/bin/sh\n", executable=True)
    declaration = _declared_publication(_peer("gitlab", "gitlab", "origin"))
    declaration["publication"]["github_remote"] = "github"

    assert publication_topology(tmp_path, declaration)["required_gaps"] == [
        "publication_topology_declaration_invalid"
    ]


def test_release_topology_requires_ci_surface_only_for_ci_capability(tmp_path: Path) -> None:
    for path in ("dev/verify", "dev/install"):
        _write(tmp_path, path, "#!/bin/sh\n", executable=True)
    repository_only = publication_topology(
        tmp_path,
        _declared_publication(_peer("gitlab", "gitlab", "origin")),
    )
    ci_peer = publication_topology(
        tmp_path,
        _declared_publication(
            _peer(
                "gitlab",
                "gitlab",
                "origin",
                capabilities=("repository", "ci_cd", "publication"),
            )
        ),
    )

    assert repository_only["state"] == "ready"
    assert ci_peer["required_gaps"] == ["publication_topology_peer_ci_surface_missing:gitlab"]


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
    ],
)
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
    literal_case(
        "release.test_policy_attestation:parametrize:test_release_policy_separates_host_profile_from_product_files:derived"
    ),
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
