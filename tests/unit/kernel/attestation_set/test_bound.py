"""The selected set carries bounded claims; file bytes belong to custody evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.attestation_set as attestation_set
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import occurrence_attestation

if TYPE_CHECKING:
    from pathlib import Path


def test_record_refuses_a_member_above_the_bound(tmp_path: Path) -> None:
    """A member whose canonical bytes exceed one mebibyte leaves the selected set unchanged."""
    repo = init_git_repo(tmp_path / "repo")
    large = occurrence_attestation(5_001, payload_bytes=attestation_set.MEMBER_BYTES_LIMIT)

    refused = f"^attestation_member_too_large:{large.id}$"
    with pytest.raises(ValueError, match=refused):
        attestation_set.record_attestations(repo, (large,))
    with pytest.raises(ValueError, match=refused):
        attestation_set.record_attestation_once(repo, large)
    assert attestation_set.read_attestation_set(repo) == ("", ())


def test_record_admits_a_member_within_the_bound(tmp_path: Path) -> None:
    """A member below the bound is added unchanged."""
    repo = init_git_repo(tmp_path / "repo")
    member = occurrence_attestation(5_002, payload_bytes=attestation_set.MEMBER_BYTES_LIMIT - 8192)

    assert len(member.canonical_json().encode()) <= attestation_set.MEMBER_BYTES_LIMIT
    root = attestation_set.record_attestations(repo, (member,))["root"]
    assert attestation_set.read_attestation_set(repo) == (root, (member,))
