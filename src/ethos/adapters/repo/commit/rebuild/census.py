"""Count a repository's trailers and peer identity forms by ref class, with no record and no key.

The census is keyless readiness: it walks every local ref's history with the local peer feed and
the shared grammar, as the keyless redaction preview reads the feed, and counts today's attribution
trailers. Each class of refs counts every object its refs reach once, by form only, and nothing is
written; a feed the clone cannot know leaves the counts `unknown`, with the feed's own gaps.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from ethos.adapters.repo.commit.rebuild.originals import original_sightings
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import object_types
from ethos.adapters.repo.peer_feed import local_feed
from ethos.repository.paradigm.peer_identity import replacement_spans

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.paradigm.peer_identity import Feed

_CLASSES = (("refs/heads/", "heads"), ("refs/tags/", "tags"), ("refs/remotes/", "remotes"))
# Today's attribution trailer (`adapters/repo/commit/history.py`), its key compared as Git does.
_ATTRIBUTION = "co-authored-by:"


def rebuild_census(root: Path) -> dict[str, object]:
    """Count, per ref class, each form the scan finds and each attribution trailer."""
    known = local_feed(root)
    counted: dict[str, dict[str, int]] = {}
    unwalked: dict[str, int] = {}
    for name, refs in sorted(_classes(root).items()):
        peeled = object_types(root, tuple(f"{ref}^{{}}" for ref in refs))
        walked = tuple(ref for ref in refs if peeled[f"{ref}^{{}}"] == "commit")
        unwalked[name] = len(refs) - len(walked)
        counted[name] = _forms(root, walked, known.feed)
    report: dict[str, object] = {"counts": counted, "unwalked": unwalked, "next_action": ""}
    if known.gaps:
        gaps = [*known.gaps]
        return report | {"verdict": "unknown", "state": "feed_unknown", "required_gaps": gaps}
    return report | {"verdict": "pass", "state": "counted", "required_gaps": []}


def _classes(root: Path) -> dict[str, list[str]]:
    """Group every local ref by class: branches, tags, remote-tracking refs and all others."""
    classes: dict[str, list[str]] = {}
    for ref in run_git(root, "for-each-ref", "--format=%(refname)").stdout.split():
        name = next((label for prefix, label in _CLASSES if ref.startswith(prefix)), "other")
        classes.setdefault(name, []).append(ref)
    return classes


def _forms(root: Path, revisions: tuple[str, ...], feed: Feed) -> dict[str, int]:
    """Count the scan's results by form, and the attribution trailers, over what the refs reach."""
    forms: Counter[str] = Counter()
    for sighting in original_sightings(root, revisions) if revisions else ():
        lines = sighting.text.splitlines()
        forms.update(span.form for line in lines for span in replacement_spans(line, feed))
        forms["trailer"] += sum(item.lower().startswith(_ATTRIBUTION) for item in sighting.trailers)
    return dict(sorted((+forms).items()))
