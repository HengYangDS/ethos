"""Repository paradigm process and document conventions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.support.paradigm import CONFORMING
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path


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


@pytest.mark.parametrize(
    ("roles", "gaps"),
    [
        ("", []),
        ('release_branch = "main"\nproposal_branch_prefix = "proposal/"\n', []),
        (
            'proposal_branch_prefix = "submit/"\n',
            [
                "repository_paradigm_branch_roles:.ethos/workspace.toml:branch_roles.proposal_branch_prefix"
            ],
        ),
    ],
    ids=["defaults", "standard-declared", "review-prefix"],
)
def test_branch_roles_keep_the_standard_names(tmp_path: Path, roles: str, gaps: list[str]) -> None:
    """A declared branch role must use the name the branch-role contract defaults to."""
    workspace = f"[branch_roles]\n{roles}" if roles else ""
    report = paradigm_report(tmp_path, {**CONFORMING, ".ethos/workspace.toml": workspace})
    assert report["required_gaps"] == gaps
    if gaps:
        assert 'proposal_branch_prefix = "proposal/"' in report["next_action"]


@pytest.mark.parametrize(
    ("policy", "gaps"),
    [
        ('signing_required = true\nsigning_format = "ssh"\n', []),
        ('scopes = ["cli"]\nsigning_required = true\nsigning_format = "ssh"\n', []),
        (
            'subject_pattern = "^(fix|spec): .+"\nsigning_required = true\n',
            [
                "repository_paradigm_commit_grammar:.ethos/workspace.toml:commit_policy.subject_pattern"
            ],
        ),
    ],
    ids=["derived", "declared-scopes", "restated"],
)
def test_the_commit_grammar_is_not_restated(tmp_path: Path, policy: str, gaps: list[str]) -> None:
    """A binding declares signing and may restrict scopes, but never its own subject grammar."""
    workspace = f"[commit_policy]\n{policy}"
    report = paradigm_report(tmp_path, {**CONFORMING, ".ethos/workspace.toml": workspace})
    assert report["required_gaps"] == gaps
    if gaps:
        assert "scopes = [...] restricts its scopes" in report["next_action"]


_RELEASING = {
    ".ethos/release.toml": '[protected_refs]\ntags = ["v*"]\n',
    "VERSION": "1.2.0\n",
    "CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n## [1.2.0] - 2026-10-15\n",
}


@pytest.mark.parametrize(
    ("changes", "gaps"),
    [
        ({}, []),
        (
            {"CHANGELOG.md": "# Changelog\n\n## Unreleased\n\n## 1.2.0 - 2026-10-15\n"},
            ["repository_paradigm_changelog:CHANGELOG.md"],
        ),
        ({"VERSION": None}, ["repository_paradigm_version_source:VERSION"]),
        (
            {"package.json": '{"version": "1.2.0", "scripts": {}}\n'},
            ["repository_paradigm_version_source:package.json:version"],
        ),
        (
            {".ethos/release.toml": '[protected_refs]\ntags = ["release-*"]\n'},
            ["repository_paradigm_release_tags:.ethos/release.toml:protected_refs.tags"],
        ),
        ({".ethos/release.toml": "", "VERSION": None, "CHANGELOG.md": None}, []),
    ],
    ids=[
        "conforming",
        "unbracketed",
        "no-version",
        "package-version",
        "tag-pattern",
        "not-released",
    ],
)
def test_a_releasing_repository_keeps_one_version_source_and_changelog(
    tmp_path: Path, changes: dict[str, str | None], gaps: list[str]
) -> None:
    """Release tags require VERSION alone, v-tags and a bracketed Keep a Changelog history."""
    merged = {**CONFORMING, **_RELEASING, **changes}
    files = {key: value for key, value in merged.items() if value is not None}
    report = paradigm_report(tmp_path, files)
    assert report["required_gaps"] == gaps


@pytest.mark.parametrize(
    ("changes", "gaps"),
    [
        ({".ethos/release.toml": "[broken\n"}, []),
        ({".ethos/workspace.toml": "[broken\n"}, []),
        ({".ethos/workspace.toml": 'branch_roles = "main"\n'}, []),
        ({".ethos/rules.toml": "[broken\n"}, []),
        (
            {".config/checks/ruff/ruff.toml": "[broken\n"},
            [
                "repository_paradigm_formatter_setting:.config/checks/ruff/ruff.toml:line-length",
                "repository_paradigm_formatter_setting:.config/checks/ruff/ruff.toml:target-version",
            ],
        ),
        ({".ethos/release.toml": '[publication]\npeers = ["gitlab", {git_remote = "x"}]\n'}, []),
        ({".ethos/release.toml": "publication = 1\n"}, []),
    ],
    ids=[
        "release-unreadable",
        "workspace-unreadable",
        "roles-not-table",
        "rules-unreadable",
        "formatter-unreadable",
        "peers-malformed",
        "publication-not-table",
    ],
)
def test_malformed_bindings_leave_their_owner_to_report_them(
    tmp_path: Path, changes: dict[str, str], gaps: list[str]
) -> None:
    """A binding the paradigm cannot parse is its native owner's gap, not a guessed one."""
    report = paradigm_report(tmp_path, {**CONFORMING, **changes})
    assert report["required_gaps"] == gaps


@pytest.mark.parametrize(
    ("changes", "gaps"),
    [
        (
            {
                "pyproject.toml": (
                    '[project]\nname = "sample"\nversion = "1.2.0"\nrequires-python = ">=3.12"\n'
                )
            },
            ["repository_paradigm_version_source:pyproject.toml:project.version"],
        ),
        ({"package.json": "{broken\n"}, ["repository_paradigm_module_lock:package.json"]),
        ({"pyproject.toml": "[broken\n"}, ["repository_paradigm_module_floor:pyproject.toml"]),
        ({"CHANGELOG.md": None}, ["repository_paradigm_changelog:CHANGELOG.md"]),
        (
            {"CHANGELOG.md": "# Changelog\n\n## [1.2.0] - 2026-10-15\n"},
            ["repository_paradigm_changelog:CHANGELOG.md"],
        ),
    ],
    ids=[
        "pyproject-version",
        "package-unreadable",
        "pyproject-unreadable",
        "no-changelog",
        "no-unreleased",
    ],
)
def test_releasing_repository_version_and_changelog_edges(
    tmp_path: Path, changes: dict[str, str | None], gaps: list[str]
) -> None:
    """Literal manifest versions, an unreadable manifest and a missing history are each reported."""
    merged = {**CONFORMING, **_RELEASING, **changes}
    files = {key: value for key, value in merged.items() if value is not None}
    report = paradigm_report(tmp_path, files)
    assert report["required_gaps"] == gaps


@pytest.mark.parametrize(
    ("changes", "gap", "repair"),
    [
        (
            {"docs/guide.md": "<!--\n---\nsubject: sample:guide\n---\n-->\n# Guide\n"},
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
