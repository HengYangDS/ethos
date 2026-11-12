"""Name private peer identity once: its occurrence forms, keyed markers, numbers and occurrences.

The redaction verb, the push-time check, the keyless verifier and the history rebuild read peer
identity through these definitions alone, with one left-to-right scan: at each position it takes
the longest declared entry and resumes after it, never reading inside what it took. A marker is one
HMAC-SHA-256 of a canonical pre-image, written as a valid host under `.invalid`; a number in a named
closed context takes a keyed replacement in its range. A rebuild counts the scan's results as
occurrences of its entries, each entry keyed by its own pre-image. Nothing here returns a value for
printing: callers report forms and positions.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from collections import Counter
from dataclasses import dataclass
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.contracts.outcome import refusal
from ethos.contracts.outcome import refuse

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Collection
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Mapping

VERSION = "ethos.private-peer.v1"
REBUILD = "ethos.rebuild.v1"
MARKER = re.compile(r"[0-9a-f]{32}\.[0-9a-f]{32}\.private-peer\.invalid")
_KEY = re.compile(r"[0-9a-f]{64}")
_RANGES = {"id": (100_000_000, 999_999_999), "port": (1024, 65535)}
_PROBES = 4096
_WELL_KNOWN_PORTS = frozenset({22, 80, 443})
# A token ends at whitespace, a quote or a delimiter; hosts are bounded as the paradigm pattern is.
_TOKEN_END = re.compile(r"""[\s"'<>()\[\]{},;|`]""")
_SEGMENT = re.compile(r"[A-Za-z0-9._~%-]+")
_PATH_BEFORE = re.compile(r"[A-Za-z0-9._~%-]")
_PATH_AFTER = re.compile(r"[A-Za-z0-9_~%-]")
_HOST_BEFORE = re.compile(r"[0-9a-z._]", re.IGNORECASE)
_HOST_AFTER = re.compile(r"[0-9a-z.]", re.IGNORECASE)
_PORT = re.compile(r":(\d+)")
_DIGEST = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
_HEX = re.compile(r"[0-9a-f]")
_SEPARATOR = re.compile(r"%2f", re.IGNORECASE)
_CITATION = re.compile(r"!(\d+)")
_CITED = re.compile(r"[^!]+/[^!]+!\d+")
# Candidates for discovery: host-like tokens, the segments after them, path-like tokens written
# or encoded, and bounded digit runs.
_HOSTLIKE = re.compile(
    r"(?<![A-Za-z0-9._-])(?:[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+|\[[0-9A-Fa-f:]+\])"
)
_SEGMENTS = re.compile(r"(?:/[A-Za-z0-9._~%-]+)+")
_PATHLIKE = re.compile(r"(?<![A-Za-z0-9._~%-])[A-Za-z0-9._~-]+(?:(?:/|%2[Ff])[A-Za-z0-9._~-]+)+")
_DIGITS = re.compile(r"(?<![0-9])[0-9]{1,9}(?![0-9])")
# Closed contexts, by stable name: a digit run counts only where one of these forms frames it and
# no hexadecimal digit follows it, so digits inside a digest stay. A rebuild record names its ID
# contexts from this set, and a context an adopter needs joins it here, with its own test.
CONTEXTS = {
    "id.api-projects": re.compile(r"projects/(\d+)"),
    "id.api-projects-encoded": re.compile(r"projects%2F(\d+)"),
    "id.ci-project-id": re.compile(r"CI_PROJECT_ID[=:] ?(\d+)"),
    "id.project-word": re.compile(r"\bproject (\d+)"),
    "id.id-word": re.compile(r"\bID (\d+)"),
    "id.project-id-option": re.compile(r"--project-id[= \n]+(\d+)"),
    "id.ids-pair": re.compile(r"\bIDs \d+ and (\d+)"),
    "id.project-dash": re.compile(r"project-(\d+)"),
    "id.mise-mirror": re.compile(r"-mise-mirror-(\d+)"),
    "id.go-project-id": re.compile(r'projectID = "(\d+)"'),
    "id.project-id-key": re.compile(r"project_id\"?[=:] ?(\d+)"),
    "id.aigw-ci-cache": re.compile(r"\.aigw-ci-cache/(\d+)"),
    "port.word": re.compile(r"\bport (\d+)"),
    "port.equals": re.compile(r"\bport=(\d+)"),
    "port.colon": re.compile(r"\bport: (\d+)"),
    "port.json": re.compile(r'"port": (\d+)'),
    "port.key": re.compile(r"\w_port[=:] ?(\d+)"),
    "port.option": re.compile(r"--port[= ](\d+)"),
    "port.short-option": re.compile(r"(?<![\w-])-p (\d+)"),
}


def normalized_path(path: str) -> str:
    """Return a namespace path without edge slashes, `.git`, query or fragment, in lower case."""
    return path.partition("?")[0].partition("#")[0].strip("/").removesuffix(".git").lower()


@dataclass(frozen=True, slots=True)
class Feed:
    """The identity that the scan matches.

    What one repository's protected peers declare, current and former, and, from a rebuild
    record, the merge-request citations that are spans of their own.
    """

    hosts: frozenset[str]
    ports: frozenset[int]
    paths: tuple[str, ...]
    ids: frozenset[int]
    citations: frozenset[str] = frozenset()
    retain: tuple[str, ...] = ()
    trailers: frozenset[str] = frozenset()
    paragraphs: frozenset[str] = frozenset()

    @classmethod
    def of(
        cls,
        *,
        hosts: Iterable[str] = (),
        ports: Iterable[int] = (),
        paths: Iterable[str] = (),
        ids: Iterable[int] = (),
        citations: Iterable[str] = (),
        retain: Iterable[str] = (),
        trailers: Iterable[str] = (),
        paragraphs: Iterable[str] = (),
    ) -> Feed:
        """Normalize declared values; a path of one segment never counts alone.

        A citation is `<path>!<n>`, and its path is declared with it. A retained prefix is public
        text that stays after a declared host; trailers and closing paragraphs are exact text.
        """
        cited = frozenset(
            item for item in map(normalized_path, citations) if _CITED.fullmatch(item)
        )
        named = (*paths, *(item.partition("!")[0] for item in cited))
        whole = {path for path in map(normalized_path, named) if "/" in path}
        return cls(
            hosts=frozenset(host.lower().strip("[]") for host in hosts if host),
            ports=frozenset(ports),
            paths=tuple(sorted(whole, key=len, reverse=True)),
            ids=frozenset(ids),
            citations=cited,
            retain=tuple(
                sorted({item.strip("/").lower() for item in retain} - {""}, key=len, reverse=True)
            ),
            trailers=frozenset(trailers),
            paragraphs=frozenset(paragraphs),
        )

    def __bool__(self) -> bool:
        """Whether the scan matches anything: an identity, a trailer or a closing paragraph."""
        return bool(
            self.hosts or self.ports or self.paths or self.ids or self.trailers or self.paragraphs
        )

    def fed_number(self, role: str, value: int) -> bool:
        """Return whether a closed-context number is a fed project ID or a fed, uncommon port."""
        if role == "id":
            return value in self.ids
        return value in self.ports and value not in _WELL_KNOWN_PORTS


@dataclass(frozen=True, slots=True)
class Span:
    """One scan result: where it lies, its form and the parts that its marker or number keys."""

    start: int
    end: int
    form: str
    kind: str = ""
    host: str = ""
    port: str = ""
    path: str = ""
    context: str = ""


def read_key(data: bytes | str) -> bytes:
    """Return the 32-byte key from 64 lowercase hex and at most one trailing newline."""
    text = data.decode("ascii", errors="replace") if isinstance(data, bytes) else data
    text = text.removesuffix("\n")
    if not _KEY.fullmatch(text) or not text.strip("0"):
        refuse("redaction_key_invalid")
    return bytes.fromhex(text)


def generation(key: bytes) -> str:
    """Name a key without revealing it, so that a verifier can tell two keys apart."""
    return hmac.new(key, b"ethos.redaction.generation.v1", hashlib.sha256).hexdigest()[:16]


def marker_image(kind: str, host: str = "", port: str = "", path: str = "") -> bytes:
    """Return the canonical pre-image that a marker keys; scheme and userinfo are never in it."""
    return "\0".join(
        (VERSION, kind, host.lower().strip("[]"), port, normalized_path(path))
    ).encode()


def rebuild_image(kind: str, *fields: str | bytes) -> bytes:
    """Return the domain-separated pre-image of a rebuild entry that no marker keys.

    `port` takes its digits; `id` its context name and digits; `trailer` its `<canonical key>:
    <value>`; `paragraph` its exact bytes; and an original's name its `oid`. Text keeps its exact
    bytes through `surrogateescape`.
    """
    parts = (REBUILD, kind, *fields)
    return b"\0".join(
        part if isinstance(part, bytes) else part.encode("utf-8", "surrogateescape")
        for part in parts
    )


def entry_digest(key: bytes, image: bytes) -> str:
    """Return an entry's keyed 64-hex digest: the HMAC-SHA-256 of its pre-image."""
    return hmac.new(key, image, hashlib.sha256).hexdigest()


def marker(key: bytes, kind: str, host: str = "", port: str = "", path: str = "") -> str:
    """Return the marker of one canonical pre-image, written from that image's entry digest."""
    return _marked(entry_digest(key, marker_image(kind, host, port, path)))


def number(key: bytes, role: str, value: int, *, taken: Collection[int], domain: str) -> int:
    """Return the keyed replacement of one project ID or port, absent from the domain."""
    low, high = _RANGES[role]
    for counter in range(_PROBES):
        image = "\0".join((VERSION, role, str(value), str(counter))).encode()
        draw = int.from_bytes(hmac.new(key, image, hashlib.sha256).digest()[:8], "big")
        candidate = low + draw % (high - low + 1)
        if (
            candidate != value
            and candidate not in taken
            and not re.search(rf"(?<!\d){candidate}(?!\d)", domain)
        ):
            return candidate
    gap = "numeric_replacement_exhausted"
    raise refusal(gap)


def numbering(key: bytes, feed: Feed, domain: str) -> dict[tuple[str, int], int]:
    """Assign each fed project ID, then each fed port, its replacement, in ascending order."""
    assigned: dict[tuple[str, int], int] = {}
    fed = {*feed.ids, *feed.ports}
    for role, values in (("id", feed.ids), ("port", feed.ports - _WELL_KNOWN_PORTS)):
        for value in sorted(values):
            taken = fed | set(assigned.values())
            assigned[role, value] = number(key, role, value, taken=taken, domain=domain)
    return assigned


def replacement_spans(line: str, feed: Feed) -> list[Span]:
    """Return the one scan's results over one line, in order; `manual` blocks an apply.

    At each position the longest declared entry wins and the scan resumes after it, so crossing
    entries give one result and a span wins over its own host, port, path and numbers.
    """
    return _scan([*_hosts(line, feed), *_paths(line, feed), *_numbers(line, feed.fed_number)])


def redact_line(
    line: str, found: Iterable[Span], key: bytes, numbers: Mapping[tuple[str, int], int]
) -> str:
    """Replace every span of one line; a `manual` span refuses."""
    out: list[str] = []
    last = 0
    for span in sorted(found, key=lambda item: item.start):
        if span.form == "manual":
            refuse("peer_occurrence_unclassified")
        out.append(line[last : span.start])
        if span.kind in _RANGES:
            out.append(str(numbers[span.kind, int(span.port)]))
        else:
            out.append(marker(key, span.kind, span.host, span.port, span.path))
        last = span.end
    out.append(line[last:])
    return "".join(out)


def redact_text(text: str, feed: Feed, key: bytes, numbers: Mapping[tuple[str, int], int]) -> str:
    """Redact every line of one text; the bytes outside the spans stay identical."""
    return "".join(
        redact_line(line, replacement_spans(line, feed), key, numbers)
        for line in text.splitlines(keepends=True)
    )


def follow_digests(text: str, renamed: Mapping[str, str]) -> str:
    """Rewrite each SHA-256 that a record holds for a file whose bytes a redaction changed."""
    return _DIGEST.sub(lambda match: renamed.get(match.group(0), match.group(0)), text)


def _scan(candidates: Iterable[tuple[Span, ...]]) -> list[Span]:
    """Take, from the left, the longest candidate at each position; never read inside it again.

    Candidates of one extent keep their given order: hosts, paths, then the named contexts.
    """
    found: list[Span] = []
    for group in sorted(candidates, key=lambda group: (group[0].start, -group[-1].end)):
        if not found or group[0].start >= found[-1].end:
            found.extend(group)
    return found


def _hosts(line: str, feed: Feed) -> list[tuple[Span, ...]]:
    """Return each bounded fed host occurrence, classified with what follows it."""
    lowered = line.lower()
    return [
        _host_spans(line, match.start(), match.end(), host, feed)
        for host in feed.hosts
        for match in re.finditer(re.escape(host), lowered)
        if _host_bounded(line, match.start(), match.end())
    ]


def _paths(line: str, feed: Feed) -> list[tuple[Span, ...]]:
    """Return the longest fed path at each segment-bounded start, written or percent-encoded."""
    lowered = line.lower()
    starts = {
        match.start()
        for path in feed.paths
        for spelled in (path, path.replace("/", "%2f"))
        for match in re.finditer(re.escape(spelled), lowered)
    }
    found: list[tuple[Span, ...]] = []
    for start in sorted(starts):
        fed = _fed_path(line, start, feed)
        if fed is not None and _path_starts(line, start, encoded="/" not in line[start : fed[0]]):
            found.append((_path_span(line, start, *fed, feed),))
    return found


def _path_starts(line: str, start: int, *, encoded: bool) -> bool:
    """Return whether a path may start here: after no path byte, or encoded after a `%2F`."""
    if not start or not _PATH_BEFORE.match(line[start - 1]):
        return True
    return encoded and start >= len("%2F") and bool(_SEPARATOR.match(line, start - len("%2F")))


def _path_span(line: str, start: int, end: int, path: str, feed: Feed) -> Span:
    """Name a lone path's form; a declared citation's `!<n>` belongs to its span."""
    if "/" not in line[start:end]:
        return Span(start, end, "encoded", "path", path=path)
    cited = _CITATION.match(line, end)
    if cited and f"{path}!{cited.group(1)}" in feed.citations:
        return Span(start, cited.end(), "citation", "path", path=f"{path}!{cited.group(1)}")
    return Span(start, end, "path", "path", path=path)


def _host_bounded(line: str, start: int, end: int) -> bool:
    before = line[start - 1] if start else ""
    after = line[end : end + 2]
    head = not before or not _HOST_BEFORE.match(before)
    tail = (
        not after
        or not _HOST_AFTER.match(after[0])
        or (after[0] == "." and (len(after) == 1 or not after[1].isalnum()))
    )
    return head and tail


def _fed_path(line: str, start: int, feed: Feed) -> tuple[int, str] | None:
    """Return the end and value of the longest fed path whose whole segments start at `start`.

    The path may be written or percent-encoded; its value is the decoded, normalized path.
    """
    lowered = line.lower()
    for path in feed.paths:
        for spelled in (path, path.replace("/", "%2f")):
            if lowered.startswith(spelled, start) and (
                (end := _path_end(line, start + len(spelled), encoded=spelled != path)) is not None
            ):
                return end, path
    return None


def _path_end(line: str, end: int, *, encoded: bool) -> int | None:
    """Return where a path ending at `end` stops: past a `.git`, or at a segment boundary."""
    if line[end : end + 4].lower() == ".git" and not _PATH_AFTER.match(line[end + 4 : end + 5]):
        return end + 4
    following = line[end : end + 1]
    if encoded and _SEPARATOR.match(line, end):
        return end
    if _PATH_AFTER.match(following) or (
        following == "." and _PATH_AFTER.match(line[end + 1 : end + 2])
    ):
        return None
    return end


def _host_spans(line: str, start: int, end: int, host: str, feed: Feed) -> tuple[Span, ...]:
    """Classify one bounded host occurrence by its neighbours and the declared ports."""
    token = start
    while token and not _TOKEN_END.match(line[token - 1]):
        token -= 1
    before = line[token:start]
    url = before.endswith("//") or bool(re.search(r"//[^/@]*@$", before))
    colon = _PORT.match(line, end)
    if colon and (url or int(colon.group(1)) in feed.ports):
        form = "url" if url else "authority"
        bare = Span(start, colon.end(), form, "host", host=host, port=colon.group(1))
        return _spanned(line, bare, feed)
    if line[end : end + 1] == ":" and not url:
        return _scp(line, Span(start, end, "scp", "host", host=host), feed)
    return _spanned(line, Span(start, end, "url" if url else "host", "host", host=host), feed)


def _scp(line: str, host: Span, feed: Feed) -> tuple[Span, ...]:
    """`scp`: the host alone, then a standalone path after the colon; a bare colon is manual.

    A retained prefix after the colon stays, so only the host is replaced.
    """
    path = _fed_path(line, host.end + 1, feed)
    if path is not None:
        return (host, Span(host.end + 1, path[0], "path", "path", path=path[1]))
    if _retained(line, host.end + 1, feed):
        return (host,)
    return (Span(host.start, host.end + 1, "manual"),)


def _spanned(line: str, bare: Span, feed: Feed) -> tuple[Span, ...]:
    """Extend a host, with its port, over the fed path after it; an unfed path is manual.

    A retained prefix after the host stays, so only the host and its port are replaced.
    """
    after = bare.end
    if line[after : after + 1] != "/" or not _SEGMENT.match(line, after + 1):
        return (bare,)
    path = _fed_path(line, after + 1, feed)
    if path is not None:
        return (replace(bare, end=path[0], kind="prefix", path=path[1]),)
    if _retained(line, after + 1, feed):
        return (bare,)
    return (Span(bare.start, after, "manual"),)


def _retained(line: str, at: int, feed: Feed) -> bool:
    """Return whether a declared public prefix of whole segments starts at `at`."""
    lowered = line.lower()
    return any(
        lowered.startswith(prefix, at)
        and _path_end(line, at + len(prefix), encoded=False) is not None
        for prefix in feed.retain
    )


def _numbers(line: str, counts: Callable[[str, int], bool]) -> list[tuple[Span, ...]]:
    """Return each named closed-context digit run of one line that `counts` admits for its role.

    A run that another digit or a hexadecimal digit follows is not bounded, so it stays.
    """
    found: list[tuple[Span, ...]] = []
    for name, pattern in CONTEXTS.items():
        role = name.partition(".")[0]
        for match in pattern.finditer(line):
            digits, end = match.group(1), match.end(1)
            bounded = not line[end : end + 1].isdigit() and not _HEX.match(line, end)
            if bounded and counts(role, int(digits)):
                found.append((Span(match.start(1), end, role, role, port=digits, context=name),))
    return found


# The occurrence model of a rebuild record's version 1: the scanned bytes are commit messages,
# annotated tag messages and blob contents, each distinct object once; each result is one entry's
# occurrence, and counts and witnesses both count these results, so they agree by construction.
@dataclass(frozen=True, slots=True)
class Sighting:
    """One object to scan, as a walk meets it: a commit's or a tag's message, or a blob.

    `object` is the commit or tag that a witness names, and `path` the blob's path in that commit's
    tree, empty for a message. A blob or tree is never named by its own ID. A message also carries
    the trailers that Git parses from it and its closing paragraph, the last one before them.
    """

    oid: str
    object: str
    path: str
    text: str
    trailers: tuple[str, ...] = ()
    closing: str = ""


@dataclass(frozen=True, slots=True)
class Witness:
    """The `n`-th result, from 1, attributed to one entry in a message or in the blob at `path`."""

    object: str
    path: str
    n: int


@dataclass(frozen=True, slots=True)
class Occurrence:
    """One scan result, attributed to exactly one entry by its kind and pre-image, in `oid`."""

    kind: str
    image: bytes
    witness: Witness
    oid: str = ""


def attributed(span: Span) -> tuple[str, bytes]:
    """Attribute one classified scan result to its entry kind and that entry's pre-image.

    A `span` holds a host with a port or a path, or is a citation; a host or a path alone is its own
    part; a port and an ID key the rebuild's images, an ID with the name of its context.
    """
    if span.kind == "port":
        return "port", rebuild_image("port", span.port)
    if span.kind == "id":
        return "id", rebuild_image("id", span.context, span.port)
    whole = span.kind == "prefix" or bool(span.port) or span.form == "citation"
    return ("span" if whole else span.kind), marker_image(
        span.kind, span.host, span.port, span.path
    )


def occurrences(sightings: Iterable[Sighting], feed: Feed) -> list[Occurrence]:
    """Scan each distinct object once, at its first sighting, numbering each entry within it.

    A declared trailer that Git parsed from a message is one result, and its line is not scanned
    again; an unclassified (`manual`) result is no entry's occurrence.
    """
    seen: set[str] = set()
    found: list[Occurrence] = []
    for sighting in sightings:
        if sighting.oid in seen:
            continue
        seen.add(sighting.oid)
        numbered: Counter[bytes] = Counter()
        for kind, image in _classified(sighting, feed):
            numbered[image] += 1
            witness = Witness(sighting.object, sighting.path, numbered[image])
            found.append(Occurrence(kind, image, witness, sighting.oid))
    return found


def counts(found: Iterable[Occurrence]) -> dict[bytes, int]:
    """Count each entry's results over every distinct object: the `count` that its record holds."""
    return dict(Counter(occurrence.image for occurrence in found))


def discovered(text: str) -> list[Span]:
    """Return every candidate that a record entry could name in one text, declared or not.

    Readiness resolves an entry's digest among them: each host-like token with its port and its
    leading path segments, every run of path segments, written or encoded, with a citation's
    number, every digit run as a port, and every named-context digit run as an ID.
    """
    found: list[Span] = []
    for line in text.splitlines():
        found += _host_candidates(line)
        found += _path_candidates(line)
        found += [Span(0, 0, "port", "port", port=digits) for digits in _DIGITS.findall(line)]
        found += [span for (span,) in _numbers(line, lambda _role, _value: True)]
    return found


def _classified(sighting: Sighting, feed: Feed) -> Iterator[tuple[str, bytes]]:
    """Yield a message's declared trailers and closing paragraph, then the scan of the rest."""
    declared = [trailer for trailer in sighting.trailers if trailer in feed.trailers]
    yield from (("trailer", rebuild_image("trailer", trailer)) for trailer in declared)
    if sighting.closing and sighting.closing in feed.paragraphs:
        yield "paragraph", rebuild_image("paragraph", sighting.closing)
    for line in scanned_lines(sighting, feed):
        for span in replacement_spans(line, feed):
            if span.form != "manual":
                yield attributed(span)


def scanned_lines(sighting: Sighting, feed: Feed) -> list[str]:
    """Return the lines the scan reads: all but a message's declared trailers and paragraph."""
    text = sighting.text
    if sighting.closing and sighting.closing in feed.paragraphs:
        head, _closing, tail = text.rpartition(sighting.closing)
        text = head + tail
    declared = {trailer for trailer in sighting.trailers if trailer in feed.trailers}
    lines = text.splitlines(keepends=True)
    return [line for line in lines if line.rstrip("\r\n") not in declared]


def _host_candidates(line: str) -> list[Span]:
    """Each host-like token alone, with its port, and with each count of leading segments."""
    found: list[Span] = []
    for match in _HOSTLIKE.finditer(line):
        host, after = match.group().rstrip("."), match.end()
        found.append(Span(0, 0, "host", "host", host=host))
        colon = _PORT.match(line, after)
        port = colon.group(1) if colon else ""
        if colon:
            after = colon.end()
            found.append(Span(0, 0, "host", "host", host=host, port=port))
        segments = _SEGMENTS.match(line, after)
        parts = segments.group().strip("/").split("/") if segments else []
        found += [
            Span(0, 0, "url", "prefix", host=host, port=port, path="/".join(parts[:count]))
            for count in range(1, len(parts) + 1)
        ]
    return found


def _path_candidates(line: str) -> list[Span]:
    """Every run of whole segments of a path-like token, and a citation of its tail."""
    found: list[Span] = []
    for match in _PATHLIKE.finditer(line):
        parts = _SEPARATOR.sub("/", match.group()).split("/")
        found += [
            Span(0, 0, "path", "path", path="/".join(parts[first:last]))
            for first in range(len(parts))
            for last in range(first + 1, len(parts) + 1)
        ]
        cited = _CITATION.match(line, match.end())
        found += [
            Span(0, 0, "citation", "path", path=f"{'/'.join(parts[first:])}!{cited.group(1)}")
            for first in range(len(parts) - 1)
            if cited
        ]
    return found


# Keyless verification: the shapes a marker may replace, and the hexadecimal runs that try to be
# markers; a placeholder or the bare suffix only describes one.
_SPAN = re.compile(
    r"(?:[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+|\[[0-9A-Fa-f:]+\]|[A-Za-z0-9-]+(?=:\d))(?::\d+)?"
    r"(?:/[A-Za-z0-9._~%-]+)*|[A-Za-z0-9._~%-]+(?:/[A-Za-z0-9._~%-]+)+(?:!\d+)?"
    r"|[A-Za-z0-9._~-]+(?:%2[Ff][A-Za-z0-9._~-]+)+"
)
_MARKER_LIKE = re.compile(r"[0-9A-Fa-f.]+\.private-peer\.invalid")
_SPAN_PARTS = re.compile(r"(\[[^\]]+\]|[^:/]+)(?::(\d+))?(/.*)?")


def malformed_markers(line: str) -> int:
    """Count the runs of hexadecimal labels that end like a marker but are not one."""
    return sum(1 for match in _MARKER_LIKE.finditer(line) if not MARKER.fullmatch(match.group()))


def alignment(removed: str, added: str) -> tuple[str, ...] | None:
    """Return the runs of a removed line that an added line's markers replace, or None.

    The added line's literal pieces must appear in order in the removed line; each marker stands
    over one run of an admitted span shape, and each closed-context digit run over a digit run,
    which may differ only by a number in its range. The one scan finds both, so neither may stand
    inside the other. No key and no identity is needed.
    """
    markers = [(Span(match.start(), match.end(), "marker"),) for match in MARKER.finditer(added)]
    if not markers:
        return None
    gaps = _scan([*markers, *_numbers(added, _keyless_number)])
    pattern, cursor = ["^"], 0
    for gap in gaps:
        shape = r"(\S+?)" if gap.form == "marker" else r"(\d+)"
        pattern += [re.escape(added[cursor : gap.start]), shape]
        cursor = gap.end
    match = re.match("".join([*pattern, re.escape(added[cursor:]), "$"]), removed)
    if match is None:
        return None
    spans: list[str] = []
    for gap, original in zip(gaps, match.groups(), strict=True):
        if gap.form == "marker":
            if not _SPAN.fullmatch(original):
                return None
            spans.append(original)
        elif original != gap.port and not _in_range(gap.kind, int(gap.port)):
            return None
    return tuple(spans)


def unkeyed(token: str, span: str) -> bool:
    """Return whether a marker is the plain or empty-key digest of the span it replaced."""
    parts = _SPAN_PARTS.fullmatch(span)
    host, port, path = (
        (parts.group(1), parts.group(2) or "", parts.group(3) or "") if parts else ("", "", "")
    )
    images = (
        marker_image("prefix", host, port, path),
        marker_image("host", host, port),
        marker_image("path", path=_SEPARATOR.sub("/", span)),
    )
    return any(
        token == _marked(digest)
        for image in images
        for digest in (
            hashlib.sha256(image).hexdigest(),
            hmac.new(b"", image, hashlib.sha256).hexdigest(),
        )
    )


def _marked(digest: str) -> str:
    return f"{digest[:32]}.{digest[32:]}.private-peer.invalid"


def _in_range(role: str, value: int) -> bool:
    low, high = _RANGES[role]
    return low <= value <= high


def _keyless_number(role: str, value: int) -> bool:
    """Whether a keyless reader counts a number; redaction keeps the ports 22, 80 and 443."""
    return role == "id" or value not in _WELL_KNOWN_PORTS
