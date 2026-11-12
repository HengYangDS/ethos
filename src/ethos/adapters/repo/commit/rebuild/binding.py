"""Bind version 1 of a history rebuild's record to its repository, its key and its originals.

The record binds only when its blob at its path in the accepted head `old` holds no declared item,
so the rebuilt image keeps it byte for byte, `base..old` touches only its Change, and the refs to
move are its own. The key binds when its generation is the record's and the one the repository
recorded last. An original is named in clear only when today's trust anchor verifies its
signature. Each entry's count and witness are the occurrence model's over every object that the
declared old values reach, and a `rebuild` or `retag` must reach an affected object. Every refusal
is a fixed gap that names a ref, a field or an index, never a value, and nothing is written.
Readiness reads the whole binding, gaps included; an apply needs a binding without gaps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal
from urllib.parse import urlsplit

from ethos.adapters.mutation.publication.forge import forge_web_repository
from ethos.adapters.repo.commit.rebuild.entries import admitted_hosts
from ethos.adapters.repo.commit.rebuild.entries import entry_gaps
from ethos.adapters.repo.commit.rebuild.entries import host_gaps
from ethos.adapters.repo.commit.rebuild.entries import named
from ethos.adapters.repo.commit.rebuild.entries import public_gaps
from ethos.adapters.repo.commit.rebuild.entries import resolve_entries
from ethos.adapters.repo.commit.rebuild.entries import resolved_feed
from ethos.adapters.repo.commit.rebuild.entries import retain_gaps
from ethos.adapters.repo.commit.rebuild.entries import tie_gaps
from ethos.adapters.repo.commit.rebuild.originals import History
from ethos.adapters.repo.commit.rebuild.originals import original_history
from ethos.adapters.repo.commit.rebuild.originals import reaching
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import object_types
from ethos.adapters.repo.key_generation import require_generation
from ethos.adapters.repo.peer_feed import local_feed
from ethos.adapters.repo.trust_anchor.verification import verify_git_object_trust
from ethos.contracts.outcome import refuse
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.peer_identity import MARKER
from ethos.repository.paradigm.peer_identity import Sighting
from ethos.repository.paradigm.peer_identity import counts
from ethos.repository.paradigm.peer_identity import generation
from ethos.repository.paradigm.peer_identity import normalized_path
from ethos.repository.paradigm.peer_identity import occurrences
from ethos.repository.rebuild_record import parse_record
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.adapters.repo.commit.rebuild.entries import Resolved
    from ethos.repository.paradigm.peer_identity import Feed
    from ethos.repository.paradigm.peer_identity import Occurrence
    from ethos.repository.rebuild_record import RebuildRecord

_PUBLIC = "public_distribution"
_REWRITTEN = frozenset({"rebuild", "retag"})


@dataclass(frozen=True, slots=True)
class Binding:
    """A record read against its originals: what it resolves and finds, and every gap.

    `affected` holds each walked commit and tag that reaches a declared item or trailer.
    """

    record: RebuildRecord
    olds: dict[str, str]
    history: History
    resolved: list[Resolved]
    feed: Feed
    found: list[Occurrence]
    affected: frozenset[str]
    gaps: tuple[str, ...]


def bind_record(
    root: Path, *, path: str, old: str, key: bytes, refs: Collection[str] | None = None
) -> RebuildRecord:
    """Return the record at `path` in `old` once it binds; else refuse by every gap it finds."""
    bound = bind(root, path=path, old=old, key=key, refs=refs)
    if bound.gaps:
        refuse(*bound.gaps)
    return bound.record


def bind(
    root: Path, *, path: str, old: str, key: bytes, refs: Collection[str] | None = None
) -> Binding:
    """Read the record at `path` in `old` against its originals, gathering every gap.

    A path outside a Change, an unread or invalid record and a key of another generation refuse
    at once, the key alone.
    """
    parts = path.split("/")
    record_name = load_repository_paradigm().openspec.change_record
    if len(parts) != 4 or parts[:2] != ["openspec", "changes"] or parts[3] != record_name:
        refuse("rebuild_record_path_invalid")
    text = _blob(root, f"{old}:{path}")
    record = parse_record(text)
    if generation(key) != record.key.generation:
        refuse("rebuild_key_generation_mismatch")
    require_generation(root, key)
    olds, gaps = _old_values(root, record, old, key)
    history = original_history(root, tuple(dict.fromkeys(olds.values())))
    sightings = history.sightings
    messages = {sighting.oid: sighting for sighting in sightings if not sighting.path}
    resolved, misplaced = resolve_entries(root, record.transform, key, messages)
    feed = resolved_feed(resolved, record.transform.retain)
    found = occurrences(sightings, feed)
    discovered_counts = counts(found)
    texts = [sighting.text for sighting in sightings]
    paths = {item.digest for item in record.transform.paths}
    admitted = admitted_hosts(resolved, local_feed(root).feed.hosts, sightings)
    public = _public_path(root)
    affected = reaching(history, {item.oid for item in found})
    gaps += [
        *_scope_gaps(root, record, path, old, key),
        *_ref_set_gaps(record, refs),
        *_unsigned_gaps(root, record),
        *(["rebuild_original_marker"] if any(MARKER.search(item) for item in texts) else []),
        *misplaced,
        *entry_gaps(resolved, feed, discovered_counts),
        *host_gaps(resolved, admitted),
        *tie_gaps(resolved, discovered_counts, texts),
        *(public_gaps(resolved, key, public) if public else ["rebuild_public_peer_unresolved"]),
        *retain_gaps(record.transform.retain, feed, key, paths, texts),
        *_image_gaps(text, feed),
        *(
            f"rebuild_ref_unaffected:{ref}"
            for ref, declared in record.refs.items()
            if declared.disposition in _REWRITTEN and ref in olds and olds[ref] not in affected
        ),
    ]
    found_gaps = tuple(dict.fromkeys(gaps))
    return Binding(record, olds, history, resolved, feed, found, affected, found_gaps)


def _ref_set_gaps(record: RebuildRecord, refs: Collection[str] | None) -> list[str]:
    """The refs to move must be exactly the record blob's ref set."""
    return (
        ["rebuild_ref_set_mismatch"] if refs is not None and set(refs) != set(record.refs) else []
    )


def _blob(root: Path, spec: str) -> str:
    shown = run_git(root, "cat-file", "blob", spec, check=False, text=False)
    if shown.returncode:
        refuse("rebuild_record_unread")
    try:
        return shown.stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        refuse("rebuild_record_unread", cause=error)


def _old_values(
    root: Path, record: RebuildRecord, old: str, key: bytes
) -> tuple[dict[str, str], list[str]]:
    """Resolve each declared ref's old value: `old`, a clear ID, or its current value's digest."""
    values: dict[str, str] = {}
    gaps: list[str] = []
    for ref, declared in record.refs.items():
        if declared.old == "old":
            values[ref] = old
            continue
        current = run_git(root, "rev-parse", "--verify", "--quiet", ref, check=False).stdout.strip()
        candidates = {current} if current else set()
        if isinstance(declared.old, str):
            candidates = {declared.old} if _present(root, declared.old) else set()
        value = named(declared.old, candidates, key)
        if value:
            values[ref] = value
        else:
            gaps.append(f"rebuild_original_unresolved:{ref}")
    return values, gaps


def _scope_gaps(root: Path, record: RebuildRecord, path: str, old: str, key: bytes) -> list[str]:
    """`base` is an ancestor of `old`, and `base..old` touches only the record's own Change."""
    change = path.rpartition("/")[0] + "/"
    ancestors = set(run_git(root, "rev-list", old).stdout.split())
    base = named(record.base, ancestors, key)
    if not base:
        return ["rebuild_base_unresolved"]
    touched = run_git(
        root, "log", "--format=", "--name-only", "-m", "--no-renames", f"{base}..{old}"
    ).stdout.split("\n")
    outside = [name for name in touched if name and not name.startswith(change)]
    return ["rebuild_base_outside_change"] if outside else []


def _unsigned_gaps(root: Path, record: RebuildRecord) -> Iterator[str]:
    """Each original named in clear must carry a signature that today's trust anchor verifies."""
    for label, oid in _clear_names(record):
        types = object_types(root, (oid,)) if _present(root, oid) else {}
        kind: Literal["commit", "annotated-tag"] = (
            "annotated-tag" if types.get(oid) == "tag" else "commit"
        )
        if not types or verify_git_object_trust(root, oid, kind).get("verdict") != "pass":
            yield f"rebuild_original_unsigned:{label}"


def _clear_names(record: RebuildRecord) -> Iterator[tuple[str, str]]:
    """Every original that the record names by ID, with the field that names it."""
    if isinstance(record.base, str):
        yield "base", record.base
    for ref, declared in record.refs.items():
        states = {f"refs:{ref}": declared.old} | {
            f"peers:{ref}:{peer}": state for peer, state in declared.peers.items()
        }
        yield from (
            (label, state)
            for label, state in states.items()
            if isinstance(state, str) and state not in {"old", "absent"}
        )
    for kind in ("trailers", "paragraphs", "spans", "hosts", "paths", "ports", "ids"):
        entries = enumerate(getattr(record.transform, kind))
        yield from (
            (f"witness:{kind}:{index}", entry.witness.object)
            for index, entry in entries
            if isinstance(entry.witness.object, str)
        )


def _image_gaps(text: str, feed: Feed) -> list[str]:
    """The record must hold no declared item, so that the rebuilt image keeps its blob."""
    held = occurrences((Sighting("record", "record", "", text),), feed)
    return ["rebuild_record_changed_in_image"] if held else []


def _public_path(root: Path) -> str:
    """The namespace path of the one declared public-distribution peer, or empty when unresolved."""
    try:
        topology = publication_topology(root, release_config(root))
    except ValueError:
        return ""
    peers = topology.get("remotes")
    remotes = [
        str(peer.get("git_remote") or "")
        for peer in (peers if isinstance(peers, list) else [])
        if isinstance(peer, dict) and peer.get("role") == _PUBLIC
    ]
    url = forge_web_repository(root, remotes[0]).url if len(remotes) == 1 else ""
    return normalized_path(urlsplit(url).path) if url else ""


def _present(root: Path, oid: str) -> bool:
    found = run_git(root, "cat-file", "-e", f"{oid}^{{object}}", check=False)
    return found.returncode == 0
