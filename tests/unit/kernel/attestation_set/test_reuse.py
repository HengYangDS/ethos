"""Byte-reuse boundaries never replace current Git membership or evidence semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.attestation_set as attestation_set
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import occurrence_attestation

if TYPE_CHECKING:
    from pathlib import Path

_CAPACITY = 256 * 1024


@pytest.fixture(autouse=True)
def bounded_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the reuse bound with small inputs instead of production-sized members."""
    monkeypatch.setattr(
        attestation_set, "_validated_member", attestation_set.member_validator(_CAPACITY)
    )


@pytest.mark.parametrize("payload_bytes", [0, 131_072])
def test_attestation_set_reuses_validation_but_not_selected_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload_bytes: int
) -> None:
    """Identical bytes decode once while changed and missing refs stay observable."""
    repo = init_git_repo(tmp_path / "repo")
    one, two = (
        occurrence_attestation(3_001, payload_bytes=payload_bytes),
        occurrence_attestation(3_002 + payload_bytes),
    )
    first = attestation_set.record_attestations(repo, (one,))
    validate = Mock(wraps=Attestation.model_validate_json)
    monkeypatch.setattr(Attestation, "model_validate_json", validate)

    for _ in range(3):
        assert attestation_set.read_attestation_set(repo) == (first["root"], (one,))
    assert validate.call_count == 1

    second = attestation_set.record_attestations(repo, (two,))
    assert attestation_set.read_attestation_set(repo) == (
        second["root"],
        tuple(sorted((one, two), key=lambda item: item.id)),
    )
    assert validate.call_count == 2
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, str(first["root"]))
    assert attestation_set.read_attestation_set(repo) == (first["root"], (one,))
    git(repo, "update-ref", "-d", attestation_set.ATTESTATION_SET_REF)
    assert attestation_set.read_attestation_set(repo) == ("", ())


def test_attestation_set_rereads_members_without_repeated_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Warm pure validation still freshly reads every selected immutable object."""
    repo = init_git_repo(tmp_path / "repo")
    one, two = occurrence_attestation(3_101), occurrence_attestation(3_102)
    first = attestation_set.record_attestations(repo, (one,))
    attestation_set.read_attestation_set(repo)
    second = attestation_set.record_attestations(repo, (two,))
    requested: list[tuple[str, ...]] = []
    read = attestation_set.read_objects

    def observed(
        repository: Path, object_ids: tuple[str, ...], **options: Any
    ) -> tuple[bytes, ...]:
        requested.append(object_ids)
        return read(repository, object_ids, **options)

    monkeypatch.setattr(attestation_set, "read_objects", observed)
    validate = Mock(wraps=Attestation.model_validate_json)
    monkeypatch.setattr(Attestation, "model_validate_json", validate)
    records = tuple(sorted((one, two), key=lambda item: item.id))
    expected = (
        second["root"],
        *(
            git(
                repo,
                "rev-parse",
                f"{second['root']}:evidence/attestations/{item.id[:2]}/{item.id}.json",
            )
            for item in records
        ),
    )

    for _ in range(2):
        assert attestation_set.read_attestation_set(repo) == (second["root"], records)
    assert requested == [expected, expected]
    assert validate.call_count == 1
    assert first["root"] != second["root"]


def test_attestation_set_oversized_member_does_not_consume_reuse_capacity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A large valid member stays admissible without retaining its bytes or value."""
    repo = init_git_repo(tmp_path / "repo")
    large = occurrence_attestation(3_007, payload_bytes=2 * _CAPACITY)
    attestation_set.record_attestations(repo, (large,))
    validate = Mock(wraps=Attestation.model_validate_json)
    monkeypatch.setattr(Attestation, "model_validate_json", validate)

    assert attestation_set.read_attestation_set(repo)[1] == (large,)
    assert attestation_set.read_attestation_set(repo)[1] == (large,)
    assert validate.call_count == 2


def test_attestation_set_reuses_retained_members_before_scan_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A set larger than the byte budget reuses every retained current member."""
    repo = init_git_repo(tmp_path / "repo")
    records = tuple(
        sorted(
            (
                occurrence_attestation(ordinal, payload_bytes=_CAPACITY * 3 // 10)
                for ordinal in range(5_000, 5_004)
            ),
            key=lambda item: item.id,
        )
    )
    selected = attestation_set.record_attestations(repo, records)["root"]
    validate = Mock(wraps=Attestation.model_validate_json)
    monkeypatch.setattr(Attestation, "model_validate_json", validate)

    assert attestation_set.read_attestation_set(repo) == (selected, records)
    assert validate.call_count == len(records)
    for _ in range(3):
        before = validate.call_count
        assert attestation_set.read_attestation_set(repo) == (selected, records)
        assert validate.call_count - before == 1


def test_attestation_set_eviction_changes_work_not_membership_or_meaning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reading more than the reuse capacity evicts old bytes without losing evidence."""
    repo = init_git_repo(tmp_path / "repo")
    records = tuple(
        sorted(
            (occurrence_attestation(n, payload_bytes=_CAPACITY * 6 // 10) for n in (4_000, 4_001)),
            key=lambda x: x.id,
        )
    )
    first = records[0]
    first_root = attestation_set.record_attestations(repo, (first,))["root"]
    assert attestation_set.read_attestation_set(repo)[1] == (first,)
    attestation_set.record_attestations(repo, records[1:])
    assert len(attestation_set.read_attestation_set(repo)[1]) == len(records)
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, str(first_root))
    validate = Mock(wraps=Attestation.model_validate_json)
    monkeypatch.setattr(Attestation, "model_validate_json", validate)

    assert attestation_set.read_attestation_set(repo) == (first_root, (first,))
    assert validate.call_count == 1
