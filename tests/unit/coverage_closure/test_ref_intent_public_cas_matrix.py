"""Reference-intent public CAS and reclamation boundaries."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.ref_intent as intent
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from pathlib import Path

OLD = "a" * 40
NEW = "b" * 40
PLAN = hashlib.sha256(b"plan").hexdigest()


def _update(old: str = OLD, new: str = NEW) -> GitRefUpdate:
    return GitRefUpdate(expected=old, desired=new)


def _write(root: Path, *, operation: str = "candidate.accept") -> dict[str, object]:
    return intent.write_ref_intent(
        root=root,
        ref_name="refs/heads/dev",
        update=_update(),
        operation=operation,
        plan_digest=PLAN,
    )


def _path(root: Path, written: dict[str, object]) -> Path:
    return intent.ref_intent_dir(root) / f"{written['nonce']}.json"


def _payload(root: Path, written: dict[str, object]) -> dict[str, object]:
    return json.loads(_path(root, written).read_text(encoding="utf-8"))


def _store(root: Path, written: dict[str, object], **updates: object) -> None:
    payload = _payload(root, written)
    payload.update(updates)
    _path(root, written).write_text(json.dumps(payload), encoding="utf-8")


def _claim(root: Path, phase: str = "prepared", *, operation: str = "candidate.accept"):
    return intent.claim_ref_intent(
        root=root,
        ref_name="refs/heads/dev",
        update=_update(),
        operation=operation,
        phase=phase,
        plan_digest=PLAN,
    )


def test_intent_lock_times_out_without_overwriting_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        intent.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError),
    )
    monkeypatch.setattr(intent.time, "sleep", lambda _seconds: None)

    with pytest.raises(ValueError, match="ref_intent_lock_timeout"):
        _write(tmp_path)


def test_claim_detects_disappeared_intent(tmp_path: Path) -> None:
    written = _write(tmp_path)
    _path(tmp_path, written).unlink()

    report = _claim(tmp_path)

    assert (report["present"], report["gap"]) == (False, "ref_intent_missing")


def test_claim_rechecks_identity_after_public_storage_drift(tmp_path: Path) -> None:
    written = _write(tmp_path)
    _store(tmp_path, written, operation="candidate.refresh")

    report = _claim(tmp_path)

    assert report["gap"] == "ref_intent_payload_invalid"
    assert not _path(tmp_path, written).exists()


def test_expired_intent_is_reclaimed_and_removed(tmp_path: Path) -> None:
    written = _write(tmp_path)
    _store(tmp_path, written, expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat())

    report = _claim(tmp_path)

    assert report["gap"] == "ref_intent_stale"
    assert not _path(tmp_path, written).exists()


def test_prepared_intent_remains_valid_until_transaction_closeout(tmp_path: Path) -> None:
    written = _write(tmp_path)
    assert _claim(tmp_path)["gap"] == ""
    _store(
        tmp_path,
        written,
        expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
    )

    report = _claim(tmp_path)

    assert report["gap"] == ""
    assert _payload(tmp_path, written)["phase"] == "prepared"


def test_committed_lookup_removes_invalid_and_reports_ambiguity(tmp_path: Path) -> None:
    directory = intent.ref_intent_dir(tmp_path)
    directory.mkdir(parents=True)
    invalid = directory / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    assert (
        intent.committed_ref_intent(root=tmp_path, operation="candidate.accept", desired=NEW)["gap"]
        == "ref_intent_missing"
    )
    assert not invalid.exists()

    first = _write(tmp_path)
    assert _claim(tmp_path)["gap"] == ""
    assert _claim(tmp_path, "committed")["gap"] == ""
    second = directory / "second.json"
    second.write_bytes(_path(tmp_path, first).read_bytes())

    report = intent.committed_ref_intent(root=tmp_path, operation="candidate.accept", desired=NEW)

    assert (report["present"], report["gap"]) == (True, "ref_intent_ambiguous")


def test_write_is_idempotent_for_the_same_public_identity(tmp_path: Path) -> None:
    first = _write(tmp_path)
    second = _write(tmp_path)

    assert second == first
    assert len(list(intent.ref_intent_dir(tmp_path).glob("*.json"))) == 1


def test_public_lookup_rejects_invalid_nonce_and_ignores_uncommitted(tmp_path: Path) -> None:
    written = _write(tmp_path)
    path = _path(tmp_path, written)
    assert (
        intent.committed_ref_intent(
            root=tmp_path,
            operation="candidate.accept",
            desired=NEW,
        )["gap"]
        == "ref_intent_missing"
    )

    _store(tmp_path, written, nonce="f" * 64)
    report = intent.committed_ref_intent(
        root=tmp_path,
        operation="candidate.accept",
        desired=NEW,
    )

    assert report["gap"] == "ref_intent_missing"
    assert not path.exists()


def test_public_abort_reports_invalid_stored_phase(tmp_path: Path) -> None:
    written = _write(tmp_path)
    assert _claim(tmp_path)["gap"] == ""
    assert _claim(tmp_path, "committed")["gap"] == ""

    report = _claim(tmp_path, "aborted")

    assert report["gap"] == ""
    assert _path(tmp_path, written).exists()


def test_invalid_cleanup_preserves_replacement_written_during_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written = _write(tmp_path)
    path = _path(tmp_path, written)
    valid = path.read_text(encoding="utf-8")
    path.write_text("{", encoding="utf-8")
    original_read = type(path).read_text
    reads = 0

    def replace_after_invalid(observed: Path, *args: object, **kwargs: object) -> str:
        nonlocal reads
        text = original_read(observed, *args, **kwargs)
        if observed == path:
            reads += 1
            if reads == 1:
                observed.write_text(valid, encoding="utf-8")
        return text

    monkeypatch.setattr(type(path), "read_text", replace_after_invalid)

    report = intent.committed_ref_intent(
        root=tmp_path,
        operation="candidate.accept",
        desired=NEW,
    )

    assert report["gap"] == "ref_intent_missing"
    assert path.exists()
