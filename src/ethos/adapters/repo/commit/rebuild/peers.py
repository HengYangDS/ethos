"""Read a history rebuild's peers through the one namespace listing and judge them by its record.

Each declared peer is listed once, under `refs/heads/`, `refs/tags/` and `refs/ethos/` and the
review heads that publication retirement names. A declared ref must hold its declared state there:
the local old value, a declared peer value named in clear or by keyed digest, or `absent`. An
undeclared branch or tag, and any `refs/ethos/` ref, refuses. A review head counts when it reaches
an affected commit, and one whose object this repository lacks is unknown. The listing records
nothing, and a failed one names the peer and its fixed gap, never the peer's stderr.
"""

from __future__ import annotations

from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

from ethos.adapters.mutation.publication.observation import observe_remote_namespaces
from ethos.adapters.mutation.publication.retirement import REVIEW_HEADS
from ethos.adapters.repo.commit.rebuild.entries import named
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Iterator
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.repository.rebuild_record import Original
    from ethos.repository.rebuild_record import RebuildRecord

_NAMESPACES = ("refs/heads/*", "refs/tags/*", "refs/ethos/*", *REVIEW_HEADS)
_DECLARED = ("refs/heads/", "refs/tags/")


def peer_states(
    root: Path,
    record: RebuildRecord,
    *,
    olds: Mapping[str, str],
    key: bytes,
    remotes: Mapping[str, str],
    affected: Collection[str],
) -> tuple[list[str], dict[str, dict[str, int]]]:
    """Return every peer's gaps against the record, and each listed peer's review-head counts."""
    named_peers = {peer for item in record.refs.values() for peer in item.peers}
    gaps = [f"rebuild_peer_unknown:{peer}" for peer in sorted(named_peers - set(remotes))]
    reviews: dict[str, dict[str, int]] = {}
    for peer, remote in remotes.items():
        listing = observe_remote_namespaces(root, remote, _NAMESPACES)
        if listing.failure is not None:
            gaps.append(f"rebuild_peer_unread:{peer}")
            continue
        held = {ref: oid for ref, oid in listing.refs.items() if not ref.endswith("^{}")}
        gaps += _peer_gaps(peer, held, record, olds, key)
        reviews[peer] = _reviewed(root, _review_heads(held), affected)
    return gaps, reviews


def _peer_gaps(
    peer: str, held: Mapping[str, str], record: RebuildRecord, olds: Mapping[str, str], key: bytes
) -> Iterator[str]:
    """A declared ref holds its state; an undeclared branch or tag, or `refs/ethos/`, refuses."""
    for ref, item in record.refs.items():
        state = item.peers.get(peer)
        if state is not None and not _holds(held.get(ref, ""), state, olds.get(ref, ""), key):
            yield f"rebuild_peer_state:{ref}:{peer}"
    for ref in held:
        declared = peer in getattr(record.refs.get(ref), "peers", {})
        if ref.startswith(_DECLARED) and not declared:
            yield f"rebuild_peer_ref_undeclared:{peer}:{ref}"
    if any(ref.startswith("refs/ethos/") for ref in held):
        yield f"rebuild_peer_ethos_ref:{peer}"


def _review_heads(held: Mapping[str, str]) -> list[str]:
    return [oid for ref, oid in held.items() if any(fnmatchcase(ref, p) for p in REVIEW_HEADS)]


def _holds(observed: str, state: str | Original, old: str, key: bytes) -> bool:
    """Whether the peer's value is the declared state: absent, the old value or a peer value."""
    if state == "absent":
        return not observed
    expected = old if state == "old" else state
    return bool(observed) and named(expected, {observed}, key) == observed


def _reviewed(root: Path, heads: list[str], affected: Collection[str]) -> dict[str, int]:
    """Count the review heads that reach an affected commit; an absent object is unknown."""
    counted = {"affected": 0, "unknown": 0}
    for head in heads:
        reached = run_git(root, "rev-list", "--ignore-missing", head, check=False).stdout.split()
        counted["unknown"] += not reached
        counted["affected"] += any(commit in affected for commit in reached)
    return counted
