"""Admit a marker edit under a record root only when it reproduces the line it replaces.

A redaction replaces a protected peer's identity with keyed markers and numbers. Without the key, a
reader can still check the edit's shape: each line that introduces a marker pairs, one to one, with
a removed line of the same hunk whose literal pieces it keeps in order. A marker line with nothing
to pair, a token that ends like a marker but is none, and a marker that is the plain or empty-key
digest of what it replaced all refuse. Gaps name the revision and path, never a value.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.repository.paradigm.peer_identity import MARKER
from ethos.repository.paradigm.peer_identity import alignment
from ethos.repository.paradigm.peer_identity import malformed_markers
from ethos.repository.paradigm.peer_identity import unkeyed
from ethos.repository.profile import effective_record_roots

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_FILE = re.compile(r"^\+\+\+ (?:b/)?(.*)$")


def record_marker_gaps(root: Path, revisions: tuple[str, ...]) -> list[str]:
    """Return the marker refusals of one sequence of revisions, in order, without repeats."""
    if not revisions:
        return []
    roots = _roots(root, (f"{revisions[0]}^", revisions[-1], *revisions))
    if roots is None:
        return ["record_roots_unread"]
    gaps: dict[str, None] = {}
    for revision in revisions:
        for path, removed, added in _hunks(root, revision):
            if path.startswith(roots):
                for gap in _hunk_gaps(removed, added):
                    gaps.setdefault(f"{gap}:{revision}:{path}")
    return list(gaps)


def _hunk_gaps(removed: list[str], added: list[str]) -> Iterator[str]:
    pool = list(removed)
    for line in added:
        if malformed_markers(line):
            yield "record_marker_malformed"
        if not MARKER.search(line):
            continue
        paired = next(
            ((index, spans) for index, old in enumerate(pool) if (spans := alignment(old, line))),
            None,
        )
        if paired is None:
            yield "record_marker_unpaired"
            continue
        index, spans = paired
        pool.pop(index)
        if any(
            unkeyed(token, span) for token, span in zip(MARKER.findall(line), spans, strict=False)
        ):
            yield "record_marker_unkeyed"


def _roots(root: Path, revisions: tuple[str, ...]) -> tuple[str, ...] | None:
    """Return the union of the record roots that the revisions declare, or None when none reads."""
    found: dict[str, None] = {}
    read = False
    for revision in dict.fromkeys(revisions):
        try:
            profile = load_committed_repository_profile(root, revision)
            found.update(dict.fromkeys(effective_record_roots(profile)))
        except ValueError:
            continue
        read = True
    return tuple(found) if read else None


def _hunks(root: Path, revision: str) -> Iterator[tuple[str, list[str], list[str]]]:
    """Yield each hunk of a revision's first-parent diff, or its combined diff for a merge."""
    shown = run_git(
        root, "show", "--format=", "--unified=0", "--no-color", "--no-ext-diff", "--cc", revision
    )
    path, removed, added = "", [], []
    for row in shown.stdout.splitlines():
        if (file := _FILE.match(row)) or row.startswith("@@"):
            if removed or added:
                yield path, removed, added
            removed, added = [], []
            path = file.group(1) if file else path
        elif row.startswith("-") and not row.startswith("---"):
            removed.append(row[1:])
        elif row.startswith("+"):
            added.append(row[1:])
    if removed or added:
        yield path, removed, added
