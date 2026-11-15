"""The releases that a release upgrades from: the carrier that records them and their derivation.

A subject is a governed repository that the releasing host can read and that takes releases: it has
selected a runtime of the product, with or without a tracked pin. A subject is inside the support
window while its last landed bump is at most `WINDOW_SECONDS` older than the newest landed bump
read, so the window moves with the bumps and never with the calendar; a subject without a pin has
no bump to date and is inside. A release upgrades from the previous release and from every release
that a subject inside the window pins or has selected.

`[release.upgrade_from]` in the release binding records each of those releases with its class. It
names no repository and holds no count of them. Pure functions; the adapter reads the facts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import NamedTuple

import ethos.repository.release.pin as pin
from ethos.contracts.branch.roles import RELEASE_UPGRADE_FROM_KEY

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence

# Two weekly release periods, counted back from the newest landed bump among the subjects read.
WINDOW_SECONDS = 14 * 24 * 60 * 60
# The form of a declared pin that cannot be read: it names no release and dates no bump.
UNREADABLE = "unreadable"


class Subject(NamedTuple):
    """What one governed repository's accepted branch and selection say; it carries no name."""

    # The accepted branch's head, which is the evidence for the three readings below.
    accepted: str
    # The form and the release of the accepted pin: both empty where the branch declares none,
    # and `UNREADABLE` with no release where its declaration cannot be read.
    form: str
    pinned: str
    # The build that `CURRENT` selects; empty where nothing is selected.
    current: str
    # The committer time, in seconds, of the accepted commit that last changed the pin; None
    # where no pin dates it.
    bumped: int | None


def recorded(config: Mapping[str, object]) -> dict[str, str] | None:
    """Read the carrier from a compiled release binding; None where the binding declares none."""
    release = config.get("release")
    table = release.get(RELEASE_UPGRADE_FROM_KEY) if isinstance(release, dict) else None
    if table is None:
        return None
    if not isinstance(table, dict) or any(
        not pin.exact(name) or kind != pin.release_class(name) for name, kind in table.items()
    ):
        message = "release_upgrade_from_invalid"
        raise ValueError(message)
    return dict(table)


def supported(subjects: Sequence[Subject]) -> tuple[Subject, ...]:
    """Keep the subjects inside the support window, measured from the newest landed bump.

    A subject whose bump has no time is inside it.
    """
    times = [subject.bumped for subject in subjects if subject.bumped is not None]
    oldest = max(times, default=0) - WINDOW_SECONDS
    return tuple(item for item in subjects if item.bumped is None or item.bumped >= oldest)


def named_by(subjects: Sequence[Subject]) -> dict[str, dict[str, int]]:
    """Count, for each version a subject inside the window names, who names it and how.

    A subject counts once for a version: by its pin, or by its selection where that is another
    version or it declares no pin.
    """
    counts: dict[str, dict[str, int]] = {}
    for subject in supported(subjects):
        for kind, name in (("pin", subject.pinned), ("selection", subject.current)):
            if name and (kind == "pin" or name != subject.pinned):
                counts.setdefault(name, {"pin": 0, "selection": 0})[kind] += 1
    return counts


def derive(version: str, history: Sequence[str], subjects: Sequence[Subject]) -> dict[str, str]:
    """Name each release that `version` upgrades from, newest first, with its class.

    `history` is the releasing repository's changelog, newest first. A version that a subject
    names and the changelog does not list is no published release: it is no predecessor, and it
    refuses nothing.
    """
    if version not in history:
        message = f"release_changelog_target_missing:{version}"
        raise ValueError(message)
    earlier = history[history.index(version) + 1 :]
    named = {*earlier[:1], *named_by(subjects)}
    return {name: pin.release_class(name) for name in earlier if name in named}
