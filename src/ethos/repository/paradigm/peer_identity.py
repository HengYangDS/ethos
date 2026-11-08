"""Name private peer identity once: its occurrence forms, keyed markers and numbers.

The redaction verb, the push-time check, the keyless verifier and the history rebuild read peer
identity through these definitions alone. A marker is one HMAC-SHA-256 of a canonical pre-image,
written as a valid host under `.invalid`; a number in a closed context takes a keyed replacement in
its range. Nothing here returns a value for printing: callers report forms and positions.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Collection
    from collections.abc import Iterable
    from collections.abc import Mapping

VERSION = "ethos.private-peer.v1"
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
# Closed contexts: a digit run counts only where one of these forms frames it.
_CONTEXTS = {
    "id": tuple(
        re.compile(pattern)
        for pattern in (
            r"projects/(\d+)",
            r"projects%2F(\d+)",
            r"CI_PROJECT_ID[=:] ?(\d+)",
            r"\bproject (\d+)",
            r"\bID (\d+)",
            r"--project-id[= \n]+(\d+)",
            r"\bIDs \d+ and (\d+)",
            r"project-(\d+)",
            r"-mise-mirror-(\d+)",
            r'projectID = "(\d+)"',
            r"project_id\"?[=:] ?(\d+)",
        )
    ),
    "port": tuple(
        re.compile(pattern)
        for pattern in (
            r"\bport (\d+)",
            r"\bport=(\d+)",
            r"\bport: (\d+)",
            r'"port": (\d+)',
            r"\w_port[=:] ?(\d+)",
            r"--port[= ](\d+)",
            r"(?<![\w-])-p (\d+)",
        )
    ),
}


def _fail(reason: str) -> NoReturn:
    raise ValueError(reason)


def normalized_path(path: str) -> str:
    """Return a namespace path without edge slashes, `.git`, query or fragment, in lower case."""
    return path.partition("?")[0].partition("#")[0].strip("/").removesuffix(".git").lower()


@dataclass(frozen=True, slots=True)
class Feed:
    """The identity that one repository's protected peers declare, current and former."""

    hosts: frozenset[str]
    ports: frozenset[int]
    paths: tuple[str, ...]
    ids: frozenset[int]

    @classmethod
    def of(
        cls,
        *,
        hosts: Iterable[str] = (),
        ports: Iterable[int] = (),
        paths: Iterable[str] = (),
        ids: Iterable[int] = (),
    ) -> Feed:
        """Normalize declared values; a path of one segment never counts alone."""
        whole = {path for path in map(normalized_path, paths) if "/" in path}
        return cls(
            hosts=frozenset(host.lower().strip("[]") for host in hosts if host),
            ports=frozenset(ports),
            paths=tuple(sorted(whole, key=len, reverse=True)),
            ids=frozenset(ids),
        )

    def __bool__(self) -> bool:
        return bool(self.hosts or self.ports or self.paths or self.ids)

    def fed_number(self, role: str, value: int) -> bool:
        """Return whether a closed-context number is a fed project ID or a fed, uncommon port."""
        if role == "id":
            return value in self.ids
        return value in self.ports and value not in _WELL_KNOWN_PORTS


@dataclass(frozen=True, slots=True)
class Span:
    """One occurrence: where it lies, its form and the parts that its marker or number keys."""

    start: int
    end: int
    form: str
    kind: str = ""
    host: str = ""
    port: str = ""
    path: str = ""


def read_key(data: bytes | str) -> bytes:
    """Return the 32-byte key from 64 lowercase hex and at most one trailing newline."""
    text = data.decode("ascii", errors="replace") if isinstance(data, bytes) else data
    text = text.removesuffix("\n")
    if not _KEY.fullmatch(text) or not text.strip("0"):
        _fail("redaction_key_invalid")
    return bytes.fromhex(text)


def generation(key: bytes) -> str:
    """Name a key without revealing it, so that a verifier can tell two keys apart."""
    return hmac.new(key, b"ethos.redaction.generation.v1", hashlib.sha256).hexdigest()[:16]


def marker(key: bytes, kind: str, host: str = "", port: str = "", path: str = "") -> str:
    """Return the marker of one canonical pre-image; scheme and userinfo are never hashed."""
    image = "\0".join((VERSION, kind, host.lower().strip("[]"), port, normalized_path(path)))
    digest = hmac.new(key, image.encode(), hashlib.sha256).hexdigest()
    return f"{digest[:32]}.{digest[32:]}.private-peer.invalid"


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
    _fail("numeric_replacement_exhausted")


def numbering(key: bytes, feed: Feed, domain: str) -> dict[tuple[str, int], int]:
    """Assign each fed project ID, then each fed port, its replacement, in ascending order."""
    assigned: dict[tuple[str, int], int] = {}
    fed = {*feed.ids, *feed.ports}
    for role, values in (("id", feed.ids), ("port", feed.ports - _WELL_KNOWN_PORTS)):
        for value in sorted(values):
            taken = fed | set(assigned.values())
            assigned[(role, value)] = number(key, role, value, taken=taken, domain=domain)
    return assigned


def replacement_spans(line: str, feed: Feed) -> list[Span]:
    """Return every occurrence of fed identity in one line, in order; `manual` blocks an apply."""
    found: list[Span] = []
    lowered = line.lower()
    for host in feed.hosts:
        for match in re.finditer(re.escape(host), lowered):
            start, end = match.span()
            if _host_bounded(line, start, end):
                found.extend(_host_spans(line, start, end, host, feed))
    taken = [(span.start, span.end) for span in found]
    for path in feed.paths:
        for match in re.finditer(re.escape(path), lowered):
            start = match.start()
            if any(low <= start < high for low, high in taken) or (
                start and _PATH_BEFORE.match(line[start - 1])
            ):
                continue
            fed = _fed_path(line, start, feed)
            if fed is not None and fed[1] == path:
                found.append(Span(start, fed[0], "path", "path", path=path))
    found.extend(_numbers(line, feed.fed_number))
    return sorted(found, key=lambda span: span.start)


def redact_line(
    line: str, found: Iterable[Span], key: bytes, numbers: Mapping[tuple[str, int], int]
) -> str:
    """Replace every span of one line; a `manual` span refuses."""
    out: list[str] = []
    last = 0
    for span in sorted(found, key=lambda item: item.start):
        if span.form == "manual":
            _fail("peer_occurrence_unclassified")
        out.append(line[last : span.start])
        if span.kind in _RANGES:
            out.append(str(numbers[(span.kind, int(span.port))]))
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
    """Return the end and value of the longest fed path whose whole segments start at `start`."""
    lowered = line.lower()
    for path in feed.paths:
        if not lowered.startswith(path, start):
            continue
        end = start + len(path)
        if lowered.startswith(".git", end) and not _PATH_AFTER.match(line[end + 4 : end + 5]):
            return end + 4, path
        following = line[end : end + 1]
        if _PATH_AFTER.match(following) or (
            following == "." and _PATH_AFTER.match(line[end + 1 : end + 2])
        ):
            continue
        return end, path
    return None


def _host_spans(line: str, start: int, end: int, host: str, feed: Feed) -> list[Span]:
    """Classify one bounded host occurrence by its neighbours and the declared ports."""
    token = start
    while token and not _TOKEN_END.match(line[token - 1]):
        token -= 1
    before = line[token:start]
    url = before.endswith("//") or bool(re.search(r"//[^/@]*@$", before))
    rest = line[end:]
    port, after = "", end
    colon = _PORT.match(rest)
    if colon and (url or int(colon.group(1)) in feed.ports):
        port, after = colon.group(1), end + colon.end()
        form = "url" if url else "authority"
    elif rest.startswith(":") and not url:
        # `scp`: the host alone, then a standalone path after the colon; a bare colon is manual.
        path = _fed_path(line, end + 1, feed)
        if path is None:
            return [Span(start, end + 1, "manual")]
        return [
            Span(start, end, "scp", "host", host=host),
            Span(end + 1, path[0], "path", "path", path=path[1]),
        ]
    else:
        form = "url" if url else "host"
    if line[after : after + 1] == "/" and _SEGMENT.match(line, after + 1):
        path = _fed_path(line, after + 1, feed)
        if path is None:
            return [Span(start, after, "manual")]
        return [Span(start, path[0], form, "prefix", host=host, port=port, path=path[1])]
    return [Span(start, after, form, "host", host=host, port=port)]


def _numbers(line: str, counts: Callable[[str, int], bool]) -> list[Span]:
    """Return each closed-context digit run of one line that `counts` admits for its role."""
    found: list[Span] = []
    for role, patterns in _CONTEXTS.items():
        for pattern in patterns:
            for match in pattern.finditer(line):
                digits, end = match.group(1), match.end(1)
                if counts(role, int(digits)) and not line[end : end + 1].isdigit():
                    found.append(Span(match.start(1), end, role, role, port=digits))
    return found
