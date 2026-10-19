"""Repository paradigm process and document conventions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.paradigm import CONFORMING
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path


_WORKSPACE = ".ethos/workspace.toml"
_RELEASE = (
    '[[publication.peers]]\nid = "gitlab"\nprovider = "gitlab"\ngit_remote = "{gitlab}"\n'
    '[[publication.peers]]\nid = "github"\nprovider = "github"\ngit_remote = "github"\n'
)


@pytest.mark.parametrize(
    ("remote", "gaps"),
    [
        ("gitlab", []),
        (
            "origin",
            ["repository_paradigm_peer_remote:.ethos/release.toml:publication.peers.gitlab"],
        ),
    ],
    ids=["peer-named", "implicit-origin"],
)
def test_each_publication_peer_names_its_git_remote(
    tmp_path: Path, remote: str, gaps: list[str]
) -> None:
    """A peer's Git remote carries the peer's own id, never the implicit origin."""
    release = _RELEASE.format(gitlab=remote)
    report = paradigm_report(tmp_path, {**CONFORMING, ".ethos/release.toml": release})
    assert report["required_gaps"] == gaps
    if gaps:
        assert "git remote rename origin gitlab" in report["next_action"]


_ROLE_GAP = f"repository_paradigm_branch_roles:{_WORKSPACE}:branch_roles."
_MIRROR_GAP = f"{_ROLE_GAP}release_mirror"
_ACCEPTED_MIRROR = {_WORKSPACE: '[branch_roles]\nrelease_mirror = "accepted_ff"\n'}
_BRANCH_ROLES = {
    "defaults": ({_WORKSPACE: ""}, [], ""),
    "mirror-to-move": (
        _ACCEPTED_MIRROR,
        [_MIRROR_GAP, "repository_paradigm_release_mirror:.ethos/release.toml:release.mirror"],
        'move release_mirror to .ethos/release.toml as [release] mirror = "accepted_ff"',
    ),
    "mirror-already-declared": (
        {**_ACCEPTED_MIRROR, ".ethos/release.toml": '[release]\nmirror = "accepted_ff"\n'},
        [_MIRROR_GAP],
        "remove release_mirror; .ethos/release.toml declares the release mirror",
    ),
    "independent-mirror": (
        {_WORKSPACE: '[branch_roles]\nrelease_mirror = "independent"\n'},
        [_MIRROR_GAP],
        (
            "remove release_mirror; the release mirror is independent unless "
            ".ethos/release.toml declares [release] mirror"
        ),
    ),
    "sibling-declared": (
        {_WORKSPACE: "[branch_roles]\ncanonical_sibling_worktrees = true\n"},
        [f"{_ROLE_GAP}canonical_sibling_worktrees"],
        (
            "remove canonical_sibling_worktrees; "
            "the repository paradigm places Work Lanes in sibling worktrees"
        ),
    ),
    "standard-declared": (
        {_WORKSPACE: '[branch_roles]\nrelease_branch = "main"\n'},
        [f"{_ROLE_GAP}release_branch"],
        "remove release_branch; the repository paradigm fixes it as main",
    ),
    "review-prefix": (
        {_WORKSPACE: '[branch_roles]\nproposal_branch_prefix = "submit/"\n'},
        [f"{_ROLE_GAP}proposal_branch_prefix"],
        (
            "remove proposal_branch_prefix after closeout renames the ref; "
            "the repository paradigm fixes it as proposal/"
        ),
    ),
}


@pytest.mark.parametrize(("changes", "gaps", "repair"), _BRANCH_ROLES.values(), ids=_BRANCH_ROLES)
def test_every_branch_role_field_is_retired(
    tmp_path: Path, changes: dict[str, str], gaps: list[str], repair: str
) -> None:
    """Every field is reported; an accepted mirror moves and a legacy name waits for closeout."""
    report = paradigm_report(tmp_path, {**CONFORMING, **changes})
    assert report["required_gaps"] == gaps
    assert report["next_action"] == repair


_BINDING_GAP = f"repository_paradigm_workspace_binding:{_WORKSPACE}:"


@pytest.mark.parametrize(
    ("workspace", "gaps"),
    [
        ('[commit_policy]\nscopes = ["cli"]\n', []),
        ('[[package]]\nname = "root"\npath = "."\n', [f"{_BINDING_GAP}package"]),
        (
            '[workspace]\nmode = "monorepo"\n\n[packages.root]\npath = "."\n',
            [f"{_BINDING_GAP}workspace", f"{_BINDING_GAP}packages"],
        ),
        ("[branch_roles]\n", [f"{_BINDING_GAP}branch_roles"]),
    ],
    ids=["commit-policy", "package", "legacy-schema", "empty-roles"],
)
def test_a_workspace_binding_declares_only_the_commit_policy(
    tmp_path: Path, workspace: str, gaps: list[str]
) -> None:
    """Every other workspace table is a declaration no reader consults."""
    report = paradigm_report(tmp_path, {**CONFORMING, _WORKSPACE: workspace})
    assert report["required_gaps"] == gaps
    if gaps:
        assert report["next_action"].startswith(f"remove {gaps[0].rpartition(':')[2]};")


@pytest.mark.parametrize(
    ("policy", "gaps"),
    [
        ("", []),
        ('scopes = ["cli"]\n', []),
        (
            'subject_pattern = "^(fix|spec): .+"\n',
            [f"repository_paradigm_commit_grammar:{_WORKSPACE}:commit_policy.subject_pattern"],
        ),
    ],
    ids=["derived", "declared-scopes", "restated"],
)
def test_the_commit_grammar_is_not_restated(tmp_path: Path, policy: str, gaps: list[str]) -> None:
    """A binding may restrict scopes, but never declares its own subject grammar."""
    workspace = f"[commit_policy]\n{policy}"
    report = paradigm_report(tmp_path, {**CONFORMING, _WORKSPACE: workspace})
    assert report["required_gaps"] == gaps
    if gaps:
        assert "scopes = [...] restricts its scopes" in report["next_action"]


@pytest.mark.parametrize("value", ["true", "false"])
def test_the_signature_is_not_restated(tmp_path: Path, value: str) -> None:
    """The paradigm fixes the SSH signature, so either signing field restates it."""
    workspace = f'[commit_policy]\nsigning_required = {value}\nsigning_format = "ssh"\n'
    report = paradigm_report(tmp_path, {**CONFORMING, _WORKSPACE: workspace})
    assert report["required_gaps"] == [
        f"repository_paradigm_commit_signature:{_WORKSPACE}:commit_policy.{field}"
        for field in ("signing_required", "signing_format")
    ]
    assert report["next_action"] == (
        "remove signing_required; the repository paradigm requires an SSH signature on every commit"
    )


_RELEASING = {
    ".ethos/release.toml": '[protected_refs]\ntags = ["v*"]\n',
    "VERSION": "1.2.0\n",
    "CHANGELOG.md": (
        "# Changelog\n\n## [Unreleased]\n\n## [1.2.0] - 2026-10-15\n\n"
        "### Fixed\n\n- Correct the release result.\n"
    ),
}
# Release tags require VERSION alone, v-tags and a bracketed Keep a Changelog history; literal
# manifest versions, an unreadable manifest and a missing history are each reported.
_RELEASES = {
    "conforming": ({}, []),
    "unbracketed": (
        {"CHANGELOG.md": "# Changelog\n\n## Unreleased\n\n## 1.2.0 - 2026-10-15\n"},
        ["repository_paradigm_changelog:CHANGELOG.md"],
    ),
    "no-version": ({"VERSION": None}, ["repository_paradigm_version_source:VERSION"]),
    "package-version": (
        {"package.json": '{"version": "1.2.0", "scripts": {}}\n'},
        ["repository_paradigm_version_source:package.json:version"],
    ),
    "tag-pattern": (
        {".ethos/release.toml": '[protected_refs]\ntags = ["release-*"]\n'},
        ["repository_paradigm_release_tags:.ethos/release.toml:protected_refs.tags"],
    ),
    "not-released": ({".ethos/release.toml": "", "VERSION": None, "CHANGELOG.md": None}, []),
    "pyproject-version": (
        {
            "pyproject.toml": (
                '[project]\nname = "sample"\nversion = "1.2.0"\nrequires-python = ">=3.12"\n'
            )
        },
        ["repository_paradigm_version_source:pyproject.toml:project.version"],
    ),
    "package-unreadable": (
        {"package.json": "{broken\n"},
        ["repository_paradigm_module_lock:package.json"],
    ),
    "pyproject-unreadable": (
        {"pyproject.toml": "[broken\n"},
        ["repository_paradigm_module_floor:pyproject.toml"],
    ),
    "no-changelog": ({"CHANGELOG.md": None}, ["repository_paradigm_changelog:CHANGELOG.md"]),
    "no-unreleased": (
        {"CHANGELOG.md": "# Changelog\n\n## [1.2.0] - 2026-10-15\n"},
        ["repository_paradigm_changelog:CHANGELOG.md"],
    ),
}


@pytest.mark.parametrize(("changes", "gaps"), _RELEASES.values(), ids=_RELEASES)
def test_a_releasing_repository_keeps_one_version_source_and_changelog(
    tmp_path: Path, changes: dict[str, str | None], gaps: list[str]
) -> None:
    """Release tags need VERSION alone, v-tags, readable manifests and a bracketed changelog."""
    merged = {**CONFORMING, **_RELEASING, **changes}
    files = {key: value for key, value in merged.items() if value is not None}
    report = paradigm_report(tmp_path, files)
    assert report["required_gaps"] == gaps


_MALFORMED = {
    "release-unreadable": ({".ethos/release.toml": "[broken\n"}, []),
    "workspace-unreadable": ({_WORKSPACE: "[broken\n"}, []),
    "roles-not-table": ({_WORKSPACE: 'branch_roles = "main"\n'}, []),
    "commit-policy-not-table": ({_WORKSPACE: 'commit_policy = "signed"\n'}, []),
    "rules-unreadable": ({".ethos/rules.toml": "[broken\n"}, []),
    "formatter-unreadable": (
        {".config/checks/ruff/ruff.toml": "[broken\n"},
        [
            "repository_paradigm_formatter_setting:.config/checks/ruff/ruff.toml:line-length",
            "repository_paradigm_formatter_setting:.config/checks/ruff/ruff.toml:target-version",
        ],
    ),
    "peers-malformed": (
        {".ethos/release.toml": '[publication]\npeers = ["gitlab", {git_remote = "x"}]\n'},
        [],
    ),
    "publication-not-table": ({".ethos/release.toml": "publication = 1\n"}, []),
}


@pytest.mark.parametrize(("changes", "gaps"), _MALFORMED.values(), ids=_MALFORMED)
def test_malformed_bindings_leave_their_owner_to_report_them(
    tmp_path: Path, changes: dict[str, str], gaps: list[str]
) -> None:
    """A binding the paradigm cannot parse is its native owner's gap, not a guessed one."""
    report = paradigm_report(tmp_path, {**CONFORMING, **changes})
    assert report["required_gaps"] == gaps


@pytest.mark.parametrize(
    ("changes", "gap", "repair"),
    [
        (
            {"docs/guide.md": "<!--\n---\nsubject: sample:guide\n---\n-->\n\n# Guide\n"},
            "repository_paradigm_front_matter:docs/guide.md",
            "remove the <!-- and --> lines so YAML front matter starts docs/guide.md",
        ),
        (
            {"docs/guide.md": "# Guide\n"},
            "repository_paradigm_front_matter:docs/guide.md",
            "begin docs/guide.md with YAML front matter carrying subject, role, state",
        ),
        (
            {"docs/decisions/DR-0004-storage.md": "---\nsubject: sample:storage\n---\n"},
            "repository_paradigm_decision_record:docs/decisions/DR-0004-storage.md",
            "to docs/decisions/dr-0004-storage.md",
        ),
        (
            {"architecture/adr-4-Storage_Layer.md": "# Storage\n"},
            "repository_paradigm_decision_record:architecture/adr-4-Storage_Layer.md",
            "to architecture/dr-0004-storage-layer.md",
        ),
        (
            {"docs/decisions/DR-12.md": "---\nsubject: sample:twelve\n---\n"},
            "repository_paradigm_decision_record:docs/decisions/DR-12.md",
            "to docs/decisions/dr-0012-<topic>.md",
        ),
    ],
    ids=["front-matter-commented", "front-matter-missing", "uppercase", "prefix", "no-topic"],
)
def test_document_conventions_name_the_carrier_and_repair(
    tmp_path: Path, changes: dict[str, str], gap: str, repair: str
) -> None:
    """Front matter starts each document, and numbered decision records share one grammar."""
    report = paradigm_report(tmp_path, {**CONFORMING, **changes})
    assert report["required_gaps"] == [gap]
    assert repair in report["next_action"]


def test_front_matter_follows_the_declared_docs_root(tmp_path: Path) -> None:
    """Only documents under the profile's docs root need front matter."""
    files = {
        **CONFORMING,
        ".ethos/profile.toml": 'profile_id = "sample"\n\n[roots]\ndocs = "handbook"\n',
        "docs/notes.md": "# Notes\n",
        "handbook/guide.md": "# Guide\n",
    }
    report = paradigm_report(tmp_path, files)
    assert report["required_gaps"] == ["repository_paradigm_front_matter:handbook/guide.md"]


def test_immutable_decision_records_keep_their_names(tmp_path: Path) -> None:
    """An archived record is immutable evidence, so no rename is required of it."""
    archived = "openspec/changes/archive/2026-01-01-sample/decisions/ADR-1.md"
    report = paradigm_report(tmp_path, {**CONFORMING, archived: "# Archived\n"})
    assert report["verdict"] == "pass", report
