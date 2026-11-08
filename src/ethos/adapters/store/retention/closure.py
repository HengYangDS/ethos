"""The digests that a repository's kept records name, kept current while an apply runs.

A preview and an apply share these roots: every live Attestation member, every regular store file
outside other owners' trees, the owned items and this verb's own records, and every blob of the
accepted tree. Each item that stays lends its own digests. A refresh decodes only what moved since
the last one, so a compare can repeat cheaply; a mistaken match only keeps a record.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.retention.kinds import owned_directories
from ethos.adapters.store.retention.roots import carrier_tokens

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ethos.adapters.store.retention.kinds import StoreItem

# Owners of these trees keep their own retention; the verb neither reads nor retires them.
_UNSCANNED = frozenset({"runtime", "packages", "hooks", "tool-cache", "cache"})
_OWN_RECORDS = ("requests/record-retirement", "receipts/record-retirement")


def live_member_bytes(root: Path) -> list[bytes]:
    """Return each live Attestation member's bytes; a damaged set refuses, none is empty."""
    try:
        _set_root, members = read_attestation_set(root)
    except ValueError as error:
        message = f"record_retirement_roots_unavailable:{error}"
        raise ValueError(message) from error
    return [member.model_dump_json().encode() for member in members]


def set_root(repo: Path) -> str:
    """Return the object that the Attestation set ref names, or nothing without a set."""
    return _ref(repo, ATTESTATION_SET_REF)


def _ref(repo: Path, name: str) -> str:
    return run_git(repo, "rev-parse", "--verify", "--quiet", name, check=False).stdout.strip()


@dataclass
class Closure:
    """The digests that the roots and every staying item name, with what each refresh read."""

    repo: Path
    store: Path
    branch: str
    depth: int
    budget: int
    owned: frozenset[Path] = frozenset()
    tokens: set[str] = field(default_factory=set)
    _files: dict[Path, tuple[int, int]] = field(default_factory=dict)
    _blobs: set[str] = field(default_factory=set)
    _roots: tuple[str, str] | None = None

    def refresh(self) -> None:
        """Decode the members after a set swap, unread accepted blobs and changed kept files."""
        roots = self._current()
        if self._roots is None or roots[0] != self._roots[0]:
            for data in live_member_bytes(self.repo):
                self.tokens |= self._decode(data, "attestation member")
        for path in self._kept_files():
            stat = path.stat()
            if self._files.get(path) != (stat.st_size, stat.st_mtime_ns):
                self.lend((path,))
                self._files[path] = (stat.st_size, stat.st_mtime_ns)
        if self._roots is None or roots[1] != self._roots[1]:
            for oid, name, data in _accepted_blobs(self.repo, roots[1], self._blobs):
                self.tokens |= self._decode(data, f"{roots[1]}:{name}")
                self._blobs.add(oid)
        self._roots = roots

    def moved(self) -> bool:
        """Return whether the set or the accepted branch moved since the last refresh."""
        return self._current() != self._roots

    def lend(self, paths: Iterable[Path]) -> None:
        """Add the digests that the present files of a staying item or a kept file name."""
        for path in paths:
            if not path.is_file():
                continue
            name = path.relative_to(self.store).as_posix()
            if path.stat().st_size > self.budget:
                message = f"record_retirement_carrier_undecodable:{name}"
                raise ValueError(message)
            self.tokens |= self._decode(path.read_bytes(), name)

    def reached(self, candidates: Iterable[StoreItem]) -> list[StoreItem]:
        """Return the candidates whose digests a root or a staying item names."""
        return [item for item in candidates if item.tokens & self.tokens]

    def members_clear(self, deleted: Iterable[StoreItem]) -> bool:
        """Return whether no live member names a deleted item, read now."""
        named: set[str] = set()
        for data in live_member_bytes(self.repo):
            named |= self._decode(data, "attestation member")
        return not any(item.tokens & named for item in deleted)

    def _decode(self, data: bytes, name: str) -> frozenset[str]:
        return carrier_tokens(data, depth=self.depth, budget=self.budget, name=name)

    def _current(self) -> tuple[str, str]:
        return set_root(self.repo), _ref(self.repo, f"refs/heads/{self.branch}")

    def _kept_files(self) -> list[Path]:
        """Return every regular store file that no item owns, without tombstones or temporaries."""
        own = tuple(self.store / name for name in _OWN_RECORDS)
        owned = set(owned_directories(self.store))
        tops = [path for path in sorted(self.store.iterdir()) if path.name not in _UNSCANNED]
        return [
            path
            for top in tops
            for path in ((top,) if top.is_symlink() or not top.is_dir() else sorted(top.rglob("*")))
            if path not in self.owned
            and not any(path.is_relative_to(directory) for directory in own)
            and not (path.name.startswith(".") and path.parent in owned)
            and not path.is_symlink()
            and path.is_file()
        ]


def _accepted_blobs(repo: Path, commit: str, seen: set[str]) -> list[tuple[str, str, bytes]]:
    """Return each blob of the accepted tree not read before, with its object ID and path."""
    listing = run_git(repo, "ls-tree", "-r", "-z", commit, text=False).stdout
    entries = {
        oid: name.decode("utf-8", errors="surrogateescape")
        for record in listing.split(b"\0")
        if record
        for meta, _tab, name in (record.partition(b"\t"),)
        if meta.split()[1] == b"blob"
        for oid in (meta.split()[2].decode(),)
        if oid not in seen
    }
    if not entries:
        return []
    request = b"".join(f"{oid}\n".encode() for oid in entries)
    stream = run_git(repo, "cat-file", "--batch", stdin=request, text=False).stdout
    blobs: list[tuple[str, str, bytes]] = []
    offset = 0
    for oid, name in entries.items():
        header_end = stream.index(b"\n", offset)
        size = int(stream[offset:header_end].split()[2])
        blobs.append((oid, name, stream[header_end + 1 : header_end + 1 + size]))
        offset = header_end + 1 + size + 1
    return blobs
