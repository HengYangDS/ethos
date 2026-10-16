"""Custody keeps exact evidence bytes outside the Attestation set until their release."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

import ethos.adapters.store.custody as custody
from ethos.adapters.repo.git import git_common_dir
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture


def _stored(repo: Path, digest: str) -> Path:
    return Path(git_common_dir(repo)) / "ethos" / "custody" / "sha256" / digest


def test_custody_stores_exact_bytes_under_their_digest(tmp_path: Path) -> None:
    """Stored evidence is byte-exact, idempotent and outside the index and tracked tree."""
    repo = init_git_repo(tmp_path / "repo")
    payload = b"original failed receipt\n\x00\xff"

    digest = custody.store_custody(repo, payload)

    assert digest == hashlib.sha256(payload).hexdigest()
    assert _stored(repo, digest).read_bytes() == payload
    assert custody.store_custody(repo, payload) == digest
    custody.require_custody(repo, (digest,))
    assert git(repo, "status", "--porcelain", "--ignored") == ""


def test_custody_refuses_missing_or_changed_bytes(tmp_path: Path) -> None:
    """A digest without its exact bytes fails closed."""
    repo = init_git_repo(tmp_path / "repo")
    absent = hashlib.sha256(b"absent").hexdigest()
    with pytest.raises(ValueError, match=f"^attestation_custody_missing:{absent}$"):
        custody.require_custody(repo, (absent,))

    digest = custody.store_custody(repo, b"evidence")
    _stored(repo, digest).write_bytes(b"changed")
    with pytest.raises(ValueError, match=f"^attestation_custody_missing:{digest}$"):
        custody.require_custody(repo, (digest,))


def test_custody_release_deletes_only_the_named_digests(tmp_path: Path) -> None:
    """Release removes exactly the requested bytes and reports what it removed."""
    repo = init_git_repo(tmp_path / "repo")
    kept, released = custody.store_custody(repo, b"kept"), custody.store_custody(repo, b"released")

    assert custody.release_custody(repo, (released, released)) == (released,)
    assert custody.release_custody(repo, (released,)) == ()
    assert not _stored(repo, released).exists()
    assert _stored(repo, kept).read_bytes() == b"kept"


def test_custody_digests_select_only_custody_references() -> None:
    """Only well-formed custody references bind stored bytes."""
    digest = hashlib.sha256(b"evidence").hexdigest()

    def member(*references: str):
        return attestation_fixture(
            predicate="observation:repository",
            verifier="agent:test:custody",
            subject="input:occurrence:custody",
            issued_at=datetime(2026, 10, 16, tzinfo=UTC),
            payload_kind="input:custody",
            payload_body={"claim": "preserved"},
            evidence_refs=references,
        )

    assert custody.custody_digests(member(f"custody:sha256:{digest}", "evidence:other")) == (
        digest,
    )
    with pytest.raises(ValueError, match=r"^attestation_custody_reference_invalid:not-a-digest$"):
        custody.custody_digests(member("custody:sha256:not-a-digest"))
