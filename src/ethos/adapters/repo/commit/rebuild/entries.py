"""Resolve a rebuild record's entries through their witnesses and judge each entry.

Each entry's digest is found among the candidates that the shared grammar discovers in its
witnessed message or blob, so the key binds every digest to one result. The resolved values never
leave the process: they form the feed whose scan over the originals gives each entry's count and
witness, and the checks below name an entry by its list and index, never by its value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import Sighting
from ethos.repository.paradigm.peer_identity import Span
from ethos.repository.paradigm.peer_identity import attributed
from ethos.repository.paradigm.peer_identity import discovered
from ethos.repository.paradigm.peer_identity import entry_digest
from ethos.repository.paradigm.peer_identity import marker_image
from ethos.repository.paradigm.peer_identity import normalized_path
from ethos.repository.paradigm.peer_identity import occurrences
from ethos.repository.paradigm.peer_identity import rebuild_image
from ethos.repository.paradigm.peer_identity import replacement_spans
from ethos.repository.rebuild_record import ENTRY_KINDS
from ethos.repository.rebuild_record import IdEntry

# A project ID is tied by one `CI_PROJECT_ID=<ID>` occurrence, which its witness names (G.4).
_TIE = "id.ci-project-id"

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Iterable
    from collections.abc import Iterator
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.repository.rebuild_record import Entry
    from ethos.repository.rebuild_record import Original
    from ethos.repository.rebuild_record import Transform


@dataclass(frozen=True, slots=True)
class Resolved:
    """One entry, by list and index, with its value's scan result and the images it counts."""

    kind: str
    index: int
    entry: Entry | IdEntry
    witness: Sighting
    value: Span | str
    images: tuple[bytes, ...] = field(default=())


def named(name: Original, candidates: Collection[str], key: bytes) -> str:
    """Return the object a record names: a clear ID among the candidates, or its keyed digest's."""
    if isinstance(name, str):
        return name if name in candidates else ""
    image = (
        oid for oid in candidates if entry_digest(key, rebuild_image("oid", oid)) == name.digest
    )
    return next(image, "")


def resolve_entries(
    root: Path, transform: Transform, key: bytes, messages: Mapping[str, Sighting]
) -> tuple[list[Resolved], list[str]]:
    """Resolve every entry through its witness; an unresolved one is a misplaced witness."""
    resolved: list[Resolved] = []
    gaps: list[str] = []
    for kind in ENTRY_KINDS:
        for index, entry in enumerate(getattr(transform, kind)):
            witness = _witnessed(root, entry, key, messages)
            found = _resolved(kind, index, entry, witness, key) if witness else None
            if found is None:
                gaps.append(f"rebuild_witness_misplaced:{kind}:{index}")
            elif found.images:
                resolved.append(found)
            else:
                gaps.append(f"rebuild_id_digest_mismatch:{index}")
    return resolved, gaps


def resolved_feed(resolved: list[Resolved], retain: tuple[str, ...]) -> Feed:
    """Gather the resolved values into the feed that the rebuild scans its originals with."""
    spans = [item.value for item in resolved if isinstance(item.value, Span)]
    texts = {
        kind: [str(item.value) for item in resolved if item.kind == kind] for kind in ENTRY_KINDS
    }
    return Feed.of(
        hosts=(span.host for span in spans if span.host),
        ports=(int(span.port) for span in spans if span.port and span.kind != "id"),
        paths=(
            span.path
            for span in spans
            if span.kind in {"path", "prefix"} and span.form != "citation"
        ),
        ids=(int(span.port) for span in spans if span.kind == "id"),
        citations=(span.path for span in spans if span.form == "citation"),
        retain=retain,
        trailers=texts["trailers"],
        paragraphs=texts["paragraphs"],
    )


def entry_gaps(
    resolved: list[Resolved], feed: Feed, discovered_counts: Mapping[bytes, int]
) -> Iterator[str]:
    """Each entry's count is the model's, its witness names its result and its value is admitted.

    A project ID is tied by at least one `CI_PROJECT_ID=<ID>` occurrence in the originals (G.4).
    """
    for item in resolved:
        label = f"{item.kind}:{item.index}"
        if sum(discovered_counts.get(image, 0) for image in item.images) != item.entry.count:
            yield f"rebuild_count_mismatch:{label}"
        results = occurrences((item.witness,), feed)
        if sum(found.image in item.images for found in results) < item.entry.witness.n:
            yield f"rebuild_witness_misplaced:{label}"
        yield from _value_gaps(item, discovered_counts)


def _value_gaps(item: Resolved, discovered_counts: Mapping[bytes, int]) -> Iterator[str]:
    """A path holds two or more segments; an ID occurs at least once as `CI_PROJECT_ID=<ID>`."""
    value = item.value if isinstance(item.value, Span) else None
    if value and item.kind == "paths" and "/" not in value.path:
        yield f"rebuild_path_segment:{item.index}"
    if value and item.kind == "ids" and not discovered_counts.get(_tie(value.port)):
        yield f"rebuild_id_untied:{item.index}"


def _tie(digits: str) -> bytes:
    return rebuild_image("id", _TIE, digits)


def host_gaps(resolved: list[Resolved], admitted: Mapping[str, bool]) -> Iterator[str]:
    """A declared host must be private-class after `//`, protected by the feed, or a Go module's."""
    for item in resolved:
        host = item.value.host if isinstance(item.value, Span) else ""
        if host and not admitted.get(host, False):
            yield f"rebuild_host_outside_pattern:{item.kind}:{item.index}"


def admitted_hosts(
    resolved: list[Resolved], protected: frozenset[str], sightings: list[Sighting]
) -> dict[str, bool]:
    """Decide each resolved host once; a former Go module host is tied by an import path."""
    paradigm = load_repository_paradigm()
    hosts = {
        item.value.host for item in resolved if isinstance(item.value, Span) and item.value.host
    }
    modules = [item.text for item in sightings if item.path.endswith((".go", "go.mod"))]
    return {
        host: paradigm.names_private_address(f"//{host}")
        or host in protected
        or any(_first_element(host).search(text) for text in modules)
        for host in hosts
    }


def tie_gaps(
    resolved: list[Resolved], discovered_counts: Mapping[bytes, int], texts: list[str]
) -> Iterator[str]:
    """A declared path must follow a declared host, port or scp colon, or be a citation's path."""
    spans = _spans(resolved)
    led = {
        normalized_path(span.path.partition("!")[0])
        for item, span in spans
        if item.kind == "spans" and any(discovered_counts.get(image) for image in item.images)
    }
    hosts = [span.host for _item, span in spans if span.host]
    for item, span in spans:
        path = span.path if item.kind == "paths" else ""
        if path and normalized_path(path) not in led and not _following(hosts, path, texts):
            yield f"rebuild_path_untied:{item.index}"


def public_gaps(resolved: list[Resolved], key: bytes, public: str) -> Iterator[str]:
    """A declared path may not be the public peer's path or one of its segment-boundary prefixes."""
    parts = public.split("/")
    images = {
        marker_image("path", path="/".join(parts[:count])) for count in range(1, len(parts) + 1)
    }
    digests = {entry_digest(key, image) for image in images}
    for item in resolved:
        if item.kind == "paths" and any(
            entry_digest(key, image) in digests for image in item.images
        ):
            yield f"rebuild_path_public:{item.index}"


def retain_gaps(
    retain: tuple[str, ...], feed: Feed, key: bytes, path_digests: set[str], texts: list[str]
) -> Iterator[str]:
    """A retained prefix is public: two or more segments, no declared item, no private address."""
    declared = Feed.of(hosts=feed.hosts, ports=feed.ports, paths=feed.paths, ids=feed.ids)
    for index, prefix in enumerate(retain):
        yield from _retain_shape_gaps(index, prefix)
        parts = prefix.strip("/").split("/")
        whole = ("/".join(parts[:count]) for count in range(1, len(parts) + 1))
        keyed = {entry_digest(key, marker_image("path", path=path)) for path in whole}
        if replacement_spans(prefix, declared) or keyed & path_digests:
            yield f"rebuild_retain_declared:{index}"
        if not _following(feed.hosts, prefix.strip("/"), texts, separators="/:"):
            yield f"rebuild_retain_unused:{index}"


def retained_totals(retain: tuple[str, ...], feed: Feed, texts: list[str]) -> list[int]:
    """Each retained prefix's occurrences after a declared host, port or scp colon, by index."""
    return [_following(feed.hosts, prefix.strip("/"), texts, separators="/:") for prefix in retain]


def _retain_shape_gaps(index: int, prefix: str) -> Iterator[str]:
    """A prefix of one segment, or `/`, or one that names a private address, could hide identity."""
    parts = prefix.strip("/").split("/")
    if len(parts) < 2 or not all(parts):
        yield f"rebuild_retain_segment:{index}"
    paradigm = load_repository_paradigm()
    if paradigm.names_private_address(prefix) or paradigm.names_private_address(f"//{prefix}"):
        yield f"rebuild_retain_private:{index}"


def _witnessed(
    root: Path, entry: Entry | IdEntry, key: bytes, messages: Mapping[str, Sighting]
) -> Sighting | None:
    """Read the witnessed message, or the blob at the witness's path in a witnessed commit."""
    oid = named(entry.witness.object, set(messages), key)
    if not oid:
        return None
    if not entry.witness.path:
        return messages[oid]
    blob = run_git(root, "cat-file", "blob", f"{oid}:{entry.witness.path}", check=False, text=False)
    if blob.returncode:
        return None
    text = blob.stdout.decode("utf-8", "surrogateescape")
    return Sighting(f"{oid}:{entry.witness.path}", oid, entry.witness.path, text)


def _resolved(
    kind: str, index: int, entry: Entry | IdEntry, witness: Sighting, key: bytes
) -> Resolved | None:
    """Find the candidate whose image the entry's digest keys."""
    if isinstance(entry, IdEntry):
        return _resolved_id(index, entry, witness, key)
    match = next(
        (
            (value, image)
            for value, image in _candidates(kind, witness)
            if entry_digest(key, image) == entry.digest
        ),
        None,
    )
    return Resolved(kind, index, entry, witness, match[0], (match[1],)) if match else None


def _resolved_id(index: int, entry: IdEntry, witness: Sighting, key: bytes) -> Resolved | None:
    """Resolve an ID's digits; its digests must key its named contexts, in order, for them."""
    for value, _image in _candidates("ids", witness):
        if not isinstance(value, Span):
            continue
        images = tuple(rebuild_image("id", name, value.port) for name in entry.contexts)
        keyed = [entry_digest(key, image) for image in images]
        if set(keyed) & set(entry.digests):
            bound = images if keyed == list(entry.digests) else ()
            return Resolved("ids", index, entry, witness, value, bound)
    return None


def _candidates(kind: str, witness: Sighting) -> Iterator[tuple[Span | str, bytes]]:
    """The values that an entry of one kind could name in its witnessed text."""
    if kind == "trailers":
        yield from ((trailer, rebuild_image("trailer", trailer)) for trailer in witness.trailers)
    elif kind == "paragraphs":
        yield from ((text, rebuild_image("paragraph", text)) for text in (witness.closing,) if text)
    else:
        wanted = ENTRY_KINDS[kind]
        for span in discovered(witness.text):
            entry_kind, image = attributed(span)
            if entry_kind == wanted:
                yield span, image


def _spans(resolved: list[Resolved]) -> list[tuple[Resolved, Span]]:
    return [(item, item.value) for item in resolved if isinstance(item.value, Span)]


def _first_element(host: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w.-]){re.escape(host)}/", re.IGNORECASE)


def _following(hosts: Iterable[str], path: str, texts: list[str], separators: str = ":") -> int:
    """Count the texts' occurrences of the path directly after a declared host and a separator."""
    names = list(hosts)
    if not names or not path:
        return 0
    hosts_pattern = "|".join(map(re.escape, names))
    pattern = re.compile(
        rf"(?:{hosts_pattern})(?::\d+)?[{re.escape(separators)}]{re.escape(path)}", re.IGNORECASE
    )
    return sum(len(pattern.findall(text)) for text in texts)
