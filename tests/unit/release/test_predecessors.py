"""A release records what it upgrades from; the set is derived from the subjects in the window."""

from __future__ import annotations

import pytest

import ethos.repository.release.predecessors as predecessors
from ethos.repository.release.changelog import released_versions
from ethos.repository.release.predecessors import Subject

DAY = 24 * 60 * 60
HISTORY = ("0.2.0-beta.12", "0.2.0-beta.11", "0.2.0-beta.10", "0.2.0-beta.3", "0.2.0-alpha.28")
CHANGELOG = "# Changelog\n\n## [Unreleased]\n\n" + "".join(
    f"## [{version}] - 2026-11-01\n\n### Fixed\n\n- Correct the result.\n\n" for version in HISTORY
)
PREVIOUS = {"0.2.0-beta.11": "attested-main"}
TENTH = {"0.2.0-beta.10": "attested-main"}
CHECKSUM = {"0.2.0-beta.3": "checksum"}
# A subject by its selection alone: it declares no pin, so no bump dates it.
ALONE = Subject("b" * 40, "", "", "0.2.0-beta.3", None)


def _subject(pinned: str, current: str = "", *, day: int = 30) -> Subject:
    """One subject whose last bump landed on `day`; it selects what it pins unless told."""
    return Subject("a" * 40, "github", pinned, current or pinned, day * DAY)


def test_the_changelog_names_its_releases_newest_first() -> None:
    """The entries are read as the changelog's own parser reads them, without `Unreleased`."""
    assert released_versions(CHANGELOG) == HISTORY


@pytest.mark.parametrize(
    ("subjects", "expected"),
    [
        ((), PREVIOUS),
        ((_subject("0.2.0-beta.10"),), PREVIOUS | TENTH),
        ((_subject("0.2.0-beta.11", "0.2.0-beta.3"),), PREVIOUS | CHECKSUM),
        ((_subject("0.2.0-beta.11"), _subject("0.2.0-beta.10", day=16)), PREVIOUS | TENTH),
        ((_subject("0.2.0-beta.11"), _subject("0.2.0-beta.10", day=15)), PREVIOUS),
        ((_subject("0.2.0-beta.12"), _subject("0.2.0-beta.10", "0.2.0-beta.12")), PREVIOUS | TENTH),
        ((_subject("0.2.0-beta.11"), ALONE), PREVIOUS | CHECKSUM),
        ((_subject("0.2.0-beta.11", "9.9.9"),), PREVIOUS),
    ],
    ids=[
        "previous",
        "pinned",
        "selected",
        "window-edge",
        "outside-window",
        "target-itself",
        "selection-alone",
        "unlisted-selection",
    ],
)
def test_a_release_upgrades_from_the_previous_release_and_what_subjects_in_the_window_name(
    subjects: tuple[Subject, ...], expected: dict[str, str]
) -> None:
    """Each release carries its class; a subject two periods behind the newest bump names none."""
    derived = predecessors.derive(HISTORY[0], HISTORY, subjects)
    assert derived == expected
    assert list(derived) == [version for version in HISTORY if version in expected]


def test_each_named_version_counts_its_subjects_by_pin_and_by_selection() -> None:
    """A subject counts once for a version; one outside the window is not counted at all.

    A version that the changelog does not list is counted like any other.
    """
    both = _subject("0.2.0-beta.11", "9.9.9")
    subjects = (both, ALONE, _subject("0.2.0-beta.10", day=15), _subject("0.2.0-beta.12"))
    assert predecessors.named_by(subjects) == {
        "0.2.0-beta.12": {"pin": 1, "selection": 0},
        "0.2.0-beta.11": {"pin": 1, "selection": 0},
        "9.9.9": {"pin": 0, "selection": 1},
        "0.2.0-beta.3": {"pin": 0, "selection": 1},
    }


def test_a_release_without_its_own_changelog_entry_refuses() -> None:
    """The releasing repository's version must be listed; a subject's version need not be."""
    with pytest.raises(ValueError, match=r"^release_changelog_target_missing:0[.]2[.]0-beta[.]13$"):
        predecessors.derive("0.2.0-beta.13", HISTORY, (_subject("0.2.0-beta.11"),))


@pytest.mark.parametrize(
    ("release", "expected"),
    [
        ({"upgrade_from": PREVIOUS | CHECKSUM}, PREVIOUS | CHECKSUM),
        ({"upgrade_from": {}}, {}),
        ({"mirror": "accepted_ff"}, None),
        (None, None),
    ],
    ids=["recorded", "empty", "undeclared", "no-table"],
)
def test_the_release_binding_records_each_release_with_its_class(
    release: dict[str, object] | None, expected: dict[str, str] | None
) -> None:
    """An undeclared carrier reads as None, which is not an empty one."""
    assert predecessors.recorded({} if release is None else {"release": release}) == expected


@pytest.mark.parametrize(
    "table",
    [["0.2.0-beta.11"], {"0.2.0b11": "attested-main"}, {"0.2.0-beta.3": "attested-main"}],
    ids=["not-a-table", "inexact-version", "another-class"],
)
def test_a_carrier_that_misnames_a_release_or_its_class_refuses(table: object) -> None:
    """A recorded class is the one the pin module's data gives that release."""
    with pytest.raises(ValueError, match=r"^release_upgrade_from_invalid$"):
        predecessors.recorded({"release": {"upgrade_from": table}})
