"""Git-common content-addressed custody of evidence bytes bound by Attestation members."""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING
from typing import Final

from filelock import FileLock

from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ethos.contracts.semantic import Attestation

CUSTODY_PREFIX: Final = "custody:sha256:"
_DIGEST = re.compile(r"[0-9a-f]{64}")
_LOCK_SECONDS: Final = 300


def binds_custody(attestation: Attestation) -> bool:
    """Return whether an Attestation names any custody binding, valid or not."""
    return any(reference.startswith(CUSTODY_PREFIX) for reference in attestation.evidence_refs)


def custody_digests(attestation: Attestation) -> tuple[str, ...]:
    """Return the digests whose stored bytes an Attestation binds as evidence."""
    digests = tuple(
        reference.removeprefix(CUSTODY_PREFIX)
        for reference in attestation.evidence_refs
        if reference.startswith(CUSTODY_PREFIX)
    )
    for digest in digests:
        if not _DIGEST.fullmatch(digest):
            message = f"attestation_custody_reference_invalid:{digest}"
            raise ValueError(message)
    return digests


def _custody_path(repo: Path, digest: str) -> Path:
    return local_state_root(repo) / "custody" / "sha256" / digest


def custody_lock(repo: Path) -> FileLock:
    """Serialize custody stores and deletions with the set swaps that bind or unbind them."""
    path = local_state_root(repo) / "custody" / "lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(path, timeout=_LOCK_SECONDS, mode=0o600, preserve_lock_file=True)


def store_custody(repo: Path, payload: bytes) -> str:
    """Keep exact evidence bytes under their SHA-256 digest and return the digest."""
    digest = hashlib.sha256(payload).hexdigest()
    write_content_addressed(
        _custody_path(repo, digest), payload, collision="custody_identity_collision"
    )
    return digest


def require_custody(repo: Path, digests: Iterable[str]) -> None:
    """Fail closed unless every digest still has exactly its stored bytes."""
    for digest in digests:
        try:
            stored = _custody_path(repo, digest).read_bytes()
        except OSError:
            stored = None
        if stored is None or hashlib.sha256(stored).hexdigest() != digest:
            message = f"attestation_custody_missing:{digest}"
            raise ValueError(message)


def release_custody(repo: Path, digests: Iterable[str]) -> tuple[str, ...]:
    """Delete the stored bytes of exactly these digests, returning those that existed."""
    released: list[str] = []
    for digest in dict.fromkeys(digests):
        try:
            _custody_path(repo, digest).unlink()
        except FileNotFoundError:
            continue
        released.append(digest)
    return tuple(released)


def stored_custody(repo: Path) -> frozenset[str]:
    """Return the digests that currently have stored bytes, ignoring in-flight temporaries."""
    store = local_state_root(repo) / "custody" / "sha256"
    if not store.is_dir():
        return frozenset()
    return frozenset(path.name for path in store.iterdir() if _DIGEST.fullmatch(path.name))
