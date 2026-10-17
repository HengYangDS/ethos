"""Custody bytes survive a deletion that races a record binding the same digest."""

from __future__ import annotations

import threading
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.repo.attestation_set as attestation_set
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.custody import store_custody
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture
from tests.support.semantic import occurrence_attestation

if TYPE_CHECKING:
    from ethos.contracts.semantic import Attestation

_START = datetime(2026, 10, 1, tzinfo=UTC)


def _binder(digest: str, *, expired: bool) -> Attestation:
    """An expired takeover window ends; the successor is open custody evidence."""
    predicate = "lane-resolution:takeover" if expired else "observation:evidence-custody"
    return attestation_fixture(
        predicate=predicate,
        verifier="agent:test:custody-race",
        subject=f"input:custody:{'expired' if expired else 'successor'}",
        issued_at=_START,
        payload_kind=predicate,
        payload_body={"preserved": "shared"},
        valid_until=_START + timedelta(hours=1) if expired else None,
        evidence_refs=(f"custody:sha256:{digest}",),
    )


def test_a_record_cannot_bind_bytes_while_their_deletion_is_in_flight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A record that binds bytes being deleted waits for the deletion, then stores them again."""
    repo = init_git_repo(tmp_path / "repo")
    payload = b"shared custody evidence"
    digest = store_custody(repo, payload)
    attestation_set.record_attestations(repo, (_binder(digest, expired=True),))
    successor = _binder(digest, expired=False)
    progressed = threading.Event()
    recorder = threading.Thread(
        target=lambda: (
            attestation_set.record_attestations(repo, (successor,), custody=(payload,)),
            progressed.set(),
        )
    )
    original_lock, original_release = attestation_set.custody_lock, attestation_set.release_custody

    def observed_lock(root: Path) -> Any:
        if threading.current_thread() is recorder:
            progressed.set()
        return original_lock(root)

    def racing_release(root: Path, digests: list[str]) -> tuple[str, ...]:
        if digest in digests and recorder.ident is None:
            recorder.start()
            # The recorder either finishes its swap or reaches the custody lock first.
            assert progressed.wait(timeout=120)
        return original_release(root, digests)

    monkeypatch.setattr(attestation_set, "custody_lock", observed_lock)
    monkeypatch.setattr(attestation_set, "release_custody", racing_release)
    attestation_set.record_attestations(repo, (occurrence_attestation(6_101),))
    recorder.join(timeout=120)

    assert not recorder.is_alive()
    assert successor.id in {item.id for item in attestation_set.read_attestation_set(repo)[1]}
    stored = Path(git_common_dir(repo)) / "ethos/custody/sha256" / digest
    assert stored.read_bytes() == payload


def test_binding_already_stored_bytes_waits_for_an_in_flight_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A record that binds stored bytes without supplying them is refused once they are deleted."""
    repo = init_git_repo(tmp_path / "repo")
    digest = store_custody(repo, b"shared custody evidence")
    attestation_set.record_attestations(repo, (_binder(digest, expired=True),))
    successor = _binder(digest, expired=False)
    outcome: list[object] = []
    recorder = threading.Thread(target=lambda: outcome.append(_record_or_error(repo, successor)))
    original_release = attestation_set.release_custody

    def racing_release(root: Path, digests: list[str]) -> tuple[str, ...]:
        if digest in digests and recorder.ident is None:
            recorder.start()
            recorder.join(timeout=2)
        return original_release(root, digests)

    monkeypatch.setattr(attestation_set, "release_custody", racing_release)
    attestation_set.record_attestations(repo, (occurrence_attestation(6_102),))
    recorder.join(timeout=120)

    members = {item.id for item in attestation_set.read_attestation_set(repo)[1]}
    assert outcome == [f"attestation_custody_missing:{digest}"]
    assert successor.id not in members


def _record_or_error(repo: Path, member: Attestation) -> object:
    try:
        return attestation_set.record_attestations(repo, (member,))
    except ValueError as error:
        return str(error)


def test_an_update_that_exhausts_its_retries_leaves_no_unbound_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bytes stored for a record that never entered the set are deleted with the failed update."""
    repo = init_git_repo(tmp_path / "repo")
    kept = b"bytes a selected member binds"
    attestation_set.record_attestations(
        repo, (_binder(store_custody(repo, kept), expired=False),), custody=(kept,)
    )
    stored = b"bytes for a record that loses every swap"
    record = _binder(store_custody(repo, stored), expired=False)
    root = attestation_set.read_attestation_set(repo)[0]
    monkeypatch.setattr(attestation_set, "_compare_and_swap_root", lambda *_a, **_k: False)

    with pytest.raises(ValueError, match=r"^attestation_set_cas_retry_exhausted$"):
        attestation_set.record_attestations(repo, (record,), custody=(stored,))

    store = Path(git_common_dir(repo)) / "ethos/custody/sha256"
    assert sorted(path.read_bytes() for path in store.iterdir()) == [kept]
    assert attestation_set.read_attestation_set(repo)[0] == root


def test_the_next_custody_update_deletes_bytes_a_failed_cleanup_left(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A reported custody gap needs no caller action: the next locked swap removes the bytes."""
    repo = init_git_repo(tmp_path / "repo")
    left = b"bytes an ended binder left behind"
    ended_binder = _binder(store_custody(repo, left), expired=True)
    attestation_set.record_attestations(repo, (ended_binder,))
    original = attestation_set.release_custody

    def failing_release(*_arguments: object) -> tuple[str, ...]:
        message = "custody store unavailable"
        raise OSError(message)

    monkeypatch.setattr(attestation_set, "release_custody", failing_release)
    first = attestation_set.record_attestations(repo, (occurrence_attestation(7_001),))
    monkeypatch.setattr(attestation_set, "release_custody", original)
    kept = b"bytes the next record binds"
    attestation_set.record_attestations(
        repo, (_binder(store_custody(repo, kept), expired=False),), custody=(kept,)
    )

    store = Path(git_common_dir(repo)) / "ethos/custody/sha256"
    assert first["custody_gap"] == "custody store unavailable"
    assert sorted(path.read_bytes() for path in store.iterdir()) == [kept]
