"""The shared release floor validates parsed entries, not heading-shaped text."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.release import committed_release_version
from ethos.adapters.repo.release import release_tag_policy
from ethos.repository.release.changelog import changelog_errors
from ethos.repository.release.publication import publication_source_version_gaps
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _release(version: str, day: str = "2026-10-16", category: str = "Fixed") -> str:
    return f"## [{version}] - {day}\n\n### {category}\n\n- Correct the result.\n"


def _gaps(entries: str) -> list[str]:
    source = "# Changelog\n\n## [Unreleased]\n\n" + entries
    return list(changelog_errors(source))


@pytest.mark.parametrize(
    "entry",
    [
        "## [1.2.3] - 2026-02-30\n\n### Fixed\n\n- Correct the result.\n",
        "## [1.2.3] - 2026-10-16\n\n### Fixed\n",
        "## [1.2.3] - 2026-10-16\n\n### Improvements\n\n- Correct the result.\n",
    ],
    ids=["impossible-date", "empty-category", "unknown-category"],
)
def test_shared_floor_rejects_invalid_release_entries(entry: str) -> None:
    """An entry needs a real date and meaningful standard categories."""
    assert _gaps(entry)


def test_shared_floor_uses_semver_precedence_not_wheel_spelling() -> None:
    """Generic prereleases and build metadata are not ETHOS wheel versions."""
    entries = _release("1.2.3+build.09") + _release("1.2.3-preview-1")
    assert _gaps(entries) == []


@pytest.mark.parametrize(
    "entries",
    [
        _release("1.2.3") + _release("1.2.3"),
        _release("1.2.3") + _release("1.2.4"),
        _release("1.2.4", "2026-10-15") + _release("1.2.3"),
        _release("1.2.3-preview.01"),
        _release("1.2.3") + "\n### Fixed\n\n- Correct another result.\n",
        "## [Unreleased]\n",
        "## [Unreleased] - 2026-10-16\n",
        "## [1.2.3]\n\n### Fixed\n\n- Correct the result.\n",
        "## [1.2.3] - 2026-10-16\n\n- Uncategorized change.\n",
        "## 1.2.3 - 2026-10-16\n",
    ],
    ids=[
        "duplicate-version",
        "version-order",
        "date-order",
        "invalid-prerelease",
        "duplicate-category",
        "duplicate-unreleased",
        "dated-unreleased",
        "missing-date",
        "missing-category",
        "unbracketed-heading",
    ],
)
def test_shared_floor_rejects_conflicting_history(entries: str) -> None:
    """Release identity, chronology and category ownership are unambiguous."""
    assert _gaps(entries)


def test_only_document_level_headings_declare_releases() -> None:
    """Fenced, quoted and list-contained examples cannot impersonate entries."""
    examples = (
        "### Changed\n\n- Preserve the example scope.\n\n"
        "```md\n## [invalid]\n```\n\n> ## [invalid]\n\n- Example\n\n  ## [invalid]\n"
    )
    assert _gaps(examples + "\n" + _release("1.2.3")) == []


def test_explicit_links_preserve_version_headings_not_history_claims() -> None:
    """Inline version links are valid syntax, not proof of their destinations."""
    entry = _release("1.2.3").replace("[1.2.3]", "[1.2.3](https://example.com/v1.2.3)")
    assert _gaps(entry) == []


@pytest.mark.parametrize(
    "entry",
    [
        "## [1.2.3] - 2026-10-16\n\n### Fixed\n\n# Appendix\n\nUnrelated prose.\n",
        _release("1.2.3").replace(
            "### Fixed", "Breaking change outside its category.\n\n### Fixed"
        ),
    ],
    ids=["appendix-is-not-a-note", "uncategorized-note"],
)
def test_note_ownership_does_not_leak_across_sections(entry: str) -> None:
    """Only the applicable change category may supply release-note content."""
    assert _gaps(entry)


def test_history_link_metadata_does_not_require_a_fixed_peer_count() -> None:
    """A link index is metadata; its source still needs independent verification."""
    metadata = "History: [Source](https://example.com/v1.2.3)\n\n"
    assert _gaps(_release("1.2.3").replace("### Fixed", metadata + "### Fixed")) == []


def test_generic_tag_publication_does_not_reapply_the_product_wheel_profile() -> None:
    """A valid adopter SemVer remains valid at the next publication boundary."""
    version = "1.2.3-preview-1+build.09"
    assert (
        publication_source_version_gaps(
            source_ref=f"refs/tags/v{version}", annotated_tag=True, version_text=version + "\n"
        )
        == ()
    )


def test_unreleased_source_is_not_forced_to_have_a_release() -> None:
    """An ordinary source checkout may declare its future release honestly."""
    assert _gaps("") == []


def test_build_metadata_does_not_invent_release_precedence() -> None:
    """Distinct build identities remain tied in precedence, not sorted lexically."""
    entries = _release("1.2.3+build.1") + _release("1.2.3+build.2")
    assert _gaps(entries) == []


def test_missing_source_and_late_unreleased_are_not_valid_history() -> None:
    """Unknown bytes and a future section below releases remain distinguishable."""
    assert changelog_errors(None) == ("release_changelog_source_missing",)
    assert changelog_errors(_release("1.2.3") + "\n## [Unreleased]\n") == (
        "release_changelog_unreleased_order",
    )


@pytest.mark.parametrize("version", ["1.2.3", "1.2.3-preview-1+build.09"])
def test_release_tag_requires_exact_committed_notes(tmp_path: Path, version: str) -> None:
    """Uncommitted notes and an existing target tag cannot mint release readiness."""
    repo = init_git_repo(tmp_path / "release")
    declaration = repo / ".ethos/release.toml"
    declaration.parent.mkdir()
    declaration.write_text('[protected_refs]\ntags = ["v*"]\n', encoding="utf-8")
    (repo / "VERSION").write_text(version + "\n", encoding="utf-8")
    notes = repo / "CHANGELOG.md"
    notes.write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
    head = commit_fixture(repo, "chore: declare a future release")
    notes.write_text("# Changelog\n\n## [Unreleased]\n\n" + _release(version), encoding="utf-8")
    with pytest.raises(ValueError, match="release_changelog_target_missing"):
        release_tag_policy(repo, head, f"v{version}")
    head = commit_fixture(repo, "docs: curate the release notes")
    assert git(repo, "tag", "--list", f"v{version}") == ""
    assert release_tag_policy(repo, head, f"v{version}")["version"] == version


@pytest.mark.parametrize("source", ["1.2.3-preview.01\n", "1.2.3+build..1\n", "1.2.3 \n"])
def test_native_release_version_rejects_malformed_source(tmp_path: Path, source: str) -> None:
    """Adopter SemVer supports the standard without relaxing its source carrier."""
    repo = init_git_repo(tmp_path / "malformed")
    (repo / "VERSION").write_text(source, encoding="utf-8")
    head = commit_fixture(repo, "test: record malformed version text")
    with pytest.raises(ValueError, match="release_version_source_invalid:VERSION"):
        committed_release_version(repo, head)
