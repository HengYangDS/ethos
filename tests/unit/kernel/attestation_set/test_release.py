"""Explicit release removes one open-predicate member and the custody bytes it alone bound."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.attestation_set as attestation_set
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.custody import store_custody
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation

_OWNER = "agent:test:custody-owner"


def _claim(ordinal: int, *references: str, predicate: str = "observation:custody") -> Attestation:
    return attestation_fixture(
        predicate=predicate,
        verifier=_OWNER,
        subject=f"git:commit:{'0' * 39}{ordinal}"
        if predicate == "proof:execution"
        else f"input:{ordinal}",
        issued_at=datetime(2026, 10, 16, tzinfo=UTC),
        payload_kind="input:custody",
        payload_body={"ordinal": ordinal},
        evidence_refs=references or (f"evidence:test:{ordinal}",),
    )


def _stored(repo: Path, digest: str) -> Path:
    return Path(git_common_dir(repo)) / "ethos/custody/sha256" / digest


def test_verifier_release_removes_the_member_and_its_unbound_custody(tmp_path: Path) -> None:
    """Bytes leave with their last binder; bytes another member binds stay."""
    repo = init_git_repo(tmp_path / "repo")
    shared, alone = store_custody(repo, b"shared"), store_custody(repo, b"alone")
    first = _claim(1, f"custody:sha256:{shared}", f"custody:sha256:{alone}")
    second = _claim(2, f"custody:sha256:{shared}")
    before = attestation_set.record_attestations(repo, (first, second))["root"]

    result = attestation_set.release_attestation(repo, first.id, actor=_OWNER)

    assert result["previous_root"] == before
    assert result["released"] == first.id
    assert result["custody_deleted"] == (alone,)
    assert attestation_set.read_attestation_set(repo) == (result["root"], (second,))
    assert _stored(repo, shared).exists()
    assert not _stored(repo, alone).exists()
    last = attestation_set.release_attestation(repo, second.id, actor=_OWNER)
    assert last["custody_deleted"] == (shared,)
    assert attestation_set.read_attestation_set(repo)[1] == ()


def test_reviewed_owner_release_needs_content_review_and_a_reason(tmp_path: Path) -> None:
    """Another actor releases only with a non-blank review reason; preview changes nothing."""
    repo = init_git_repo(tmp_path / "repo")
    member = _claim(3)
    root = attestation_set.record_attestations(repo, (member,))["root"]

    for review in ("", "  "):
        with pytest.raises(ValueError, match=r"^attestation_release_actor_unadmitted$"):
            attestation_set.release_attestation(repo, member.id, actor="human:owner", review=review)
    assert attestation_set.read_attestation_set(repo)[0] == root
    preview = attestation_set.release_attestation(
        repo, member.id, actor="human:owner", review="consumer closed", apply=False
    )
    assert preview == {"previous_root": root, "root": root, "released": member.id}
    attestation_set.release_attestation(
        repo, member.id, actor="human:owner", review="consumer closed"
    )
    assert attestation_set.read_attestation_set(repo)[1] == ()


def test_release_refuses_product_lifetimes_and_absent_members(tmp_path: Path) -> None:
    """Product records end only by their lifetime, and an absent member is not released."""
    repo = init_git_repo(tmp_path / "repo")
    proof = _claim(4, predicate="proof:execution")
    root = attestation_set.record_attestations(repo, (proof,))["root"]

    with pytest.raises(ValueError, match=f"^attestation_release_product_lifetime:{proof.id}$"):
        attestation_set.release_attestation(repo, proof.id, actor=_OWNER, review="x")
    absent = hashlib.sha256(b"absent").hexdigest()
    with pytest.raises(ValueError, match=f"^attestation_release_member_absent:{absent}$"):
        attestation_set.release_attestation(repo, absent, actor=_OWNER, review="x")
    assert attestation_set.read_attestation_set(repo)[0] == root
