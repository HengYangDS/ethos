"""Find, in a rebuild's originals, what its record must declare and the quotes it must map.

The record's resolved feed scans every message and blob once, as the occurrence model does: a
result whose pre-image no entry keys, a declared host followed by an undeclared port or path, and
a declared path cited as `<path>!<n>` without a declared citation each refuse, and so does a local
feed value, current or former, that no record result covers. Headers and tree entry names are never
rewritten, so a declared item in one refuses. A quoted original ID is a bounded hex token that
prefixes exactly one rewritten commit or tag; it is counted by where it stands and what it quotes,
never by value, and a token that prefixes two refuses. Every count is keyed by its gap's name.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from collections import Counter
from typing import TYPE_CHECKING

from ethos.contracts.outcome import OutcomeError
from ethos.repository.paradigm.peer_identity import attributed
from ethos.repository.paradigm.peer_identity import numbering
from ethos.repository.paradigm.peer_identity import redact_text
from ethos.repository.paradigm.peer_identity import replacement_spans
from ethos.repository.paradigm.peer_identity import scanned_lines

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Mapping

    from ethos.adapters.repo.commit.rebuild.originals import History
    from ethos.repository.paradigm.peer_identity import Feed
    from ethos.repository.paradigm.peer_identity import Sighting
    from ethos.repository.paradigm.peer_identity import Span

_CITED = re.compile(r"!\d+")
# A quoted ID: 7 to 40 hex characters bounded by non-hex ones; a 64-character digest is followed.
_QUOTE = re.compile(r"(?<![0-9A-Fa-f])[0-9a-f]{7,40}(?![0-9A-Fa-f])")


def discovered_gaps(
    history: History, feed: Feed, declared: Collection[bytes], local: Feed
) -> Counter[str]:
    """Count, by gap name, every result that the record does not declare or cover."""
    found: Counter[str] = Counter()
    for sighting in history.sightings:
        for line in scanned_lines(sighting, feed):
            found.update(_line_gaps(line, feed, declared, local))
    headers = (header.splitlines() for header in history.headers.values())
    found["rebuild_header_item"] += sum(map(bool, (_items(lines, feed) for lines in headers)))
    names = [name for listed in history.names.values() for name in listed]
    found["rebuild_tree_name_item"] += sum(bool(_items((name,), feed)) for name in names)
    del found[""]
    return +found


def _items(lines: Iterable[str], feed: Feed) -> list[Span]:
    return [span for line in lines for span in replacement_spans(line, feed)]


def _line_gaps(line: str, feed: Feed, declared: Collection[bytes], local: Feed) -> Iterator[str]:
    """Judge one scanned line's record results, then the local feed's results it leaves bare."""
    spans = replacement_spans(line, feed)
    yield from (_judged(line, span, declared) for span in spans)
    taken = [span for span in spans if span.form != "manual"]
    for span in replacement_spans(line, local):
        if not any(item.start < span.end and span.start < item.end for item in taken):
            yield f"rebuild_feed_uncovered:{span.form}"


def _judged(line: str, span: Span, declared: Collection[bytes]) -> str:
    """Name the gap of one record result, or nothing when an entry declares it."""
    if span.form == "manual":
        return "rebuild_undeclared_after_host"
    kind, image = attributed(span)
    if image not in declared:
        return f"rebuild_undeclared:{kind}"
    return (
        "rebuild_undeclared:citation"
        if span.form == "path" and _CITED.match(line, span.end)
        else ""
    )


def quoted_ids(
    history: History, rewritten: Mapping[str, str], record_path: str
) -> tuple[dict[str, dict[str, int]], int]:
    """Count the quotes of rewritten objects by where they stand and what they quote.

    The record blob states the old history and keeps its IDs, so it is not read.
    """
    ordered = sorted(rewritten)
    commits = set(history.commits)
    found: dict[str, Counter[str]] = {}
    ambiguous = 0
    for sighting in history.sightings:
        if sighting.path == record_path:
            continue
        holder = "blob" if sighting.path else "commit" if sighting.oid in commits else "tag"
        for token in _QUOTE.findall(sighting.text):
            hits = list(_prefixed(ordered, token))
            if len(hits) == 1:
                found.setdefault(holder, Counter())[rewritten[hits[0]]] += 1
            ambiguous += len(hits) > 1
    return {
        holder: dict(sorted(kinds.items())) for holder, kinds in sorted(found.items())
    }, ambiguous


def _prefixed(ordered: list[str], token: str) -> Iterator[str]:
    """Yield at most two IDs that start with the token."""
    start = bisect_left(ordered, token)
    yield from (oid for oid in ordered[start : start + 2] if oid.startswith(token))


def transformed(sighting: Sighting, feed: Feed, key: bytes) -> str | None:
    """Return a message as the rebuild writes it, or None when the scan cannot classify it."""
    text = "".join(scanned_lines(sighting, feed))
    try:
        return redact_text(text, feed, key, numbering(key, feed, text))
    except OutcomeError:
        return None
