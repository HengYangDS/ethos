"""Reference-intent public CAS and reclamation boundaries."""

from __future__ import annotations

import hashlib
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


def test_intent_lock_times_out_without_overwriting_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(intent, "_LOCK_ATTEMPTS", 1)
    monkeypatch.setattr(
        intent.os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError)
    )
    monkeypatch.setattr(intent.time, "sleep", lambda _seconds: None)

    with pytest.raises(ValueError, match="ref_intent_lock_timeout"):
        _write(tmp_path)


def test_claim_detects_disappeared_and_changed_intent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    written = _write(tmp_path)
    reader = intent._read  # noqa: SLF001
    original = reader(intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json")
    assert original is not None

    calls = iter((original, None))
    monkeypatch.setattr(intent, "_read", lambda _path: next(calls))
    missing = intent.claim_ref_intent(
        root=tmp_path,
        ref_name="refs/heads/dev",
        update=_update(),
        operation="candidate.accept",
        phase="prepared",
        plan_digest=PLAN,
    )
    assert (missing["present"], missing["gap"]) == (False, "ref_intent_missing")

    changed = original.model_copy(update={"nonce": "c" * 64})
    calls = iter((original, changed))
    monkeypatch.setattr(intent, "_read", lambda _path: next(calls))
    report = intent.claim_ref_intent(
        root=tmp_path,
        ref_name="refs/heads/dev",
        update=_update(),
        operation="candidate.accept",
        phase="prepared",
        plan_digest=PLAN,
    )
    assert report["gap"] == "ref_intent_changed"


def test_claim_rechecks_identity_after_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    written = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json"
    reader = intent._read  # noqa: SLF001
    original = reader(path)
    assert original is not None
    drifted = original.model_copy(update={"operation": "candidate.refresh"})
    calls = iter((original, drifted))
    monkeypatch.setattr(intent, "_read", lambda _path: next(calls))

    report = intent.claim_ref_intent(
        root=tmp_path,
        ref_name="refs/heads/dev",
        update=_update(),
        operation="candidate.accept",
        phase="prepared",
        plan_digest=PLAN,
    )

    assert report["gap"] == "ref_intent_operation_mismatch"


def test_expired_intent_reclamation_detects_concurrent_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    written = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json"
    reader = intent._read  # noqa: SLF001
    original = reader(path)
    assert original is not None
    expired = original.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)})
    changed = expired.model_copy(update={"nonce": "d" * 64})
    calls = iter((expired, changed))
    monkeypatch.setattr(intent, "_read", lambda _path: next(calls))

    report = intent.claim_ref_intent(
        root=tmp_path,
        ref_name="refs/heads/dev",
        update=_update(),
        operation="candidate.accept",
        phase="prepared",
        plan_digest=PLAN,
    )

    assert report["gap"] == "ref_intent_changed"


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
    path = directory / f"{first['nonce']}.json"
    model = intent._read(path)  # noqa: SLF001
    assert model is not None
    committed = model.model_copy(update={"phase": "committed"})
    second = directory / "second.json"
    second.write_text(committed.model_dump_json(), encoding="utf-8")
    path.write_text(committed.model_dump_json(), encoding="utf-8")

    report = intent.committed_ref_intent(root=tmp_path, operation="candidate.accept", desired=NEW)
    assert (report["present"], report["gap"]) == (True, "ref_intent_ambiguous")


def test_write_detects_nonce_collision_after_public_identity_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    existing = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{existing['nonce']}.json"
    model = intent._read(path)  # noqa: SLF001
    assert model is not None
    collision = model.model_copy(update={"nonce": "e" * 64})
    monkeypatch.setattr(intent, "_read", lambda _path: collision)

    with pytest.raises(ValueError, match="ref_intent_collision"):
        _write(tmp_path)


def test_public_lookup_rejects_invalid_nonce_and_ignores_uncommitted(tmp_path: Path) -> None:
    written = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json"
    assert (
        intent.committed_ref_intent(
            root=tmp_path,
            operation="candidate.accept",
            desired=NEW,
        )["gap"]
        == "ref_intent_missing"
    )

    payload = path.read_text(encoding="utf-8").replace(str(written["nonce"]), "f" * 64)
    path.write_text(payload, encoding="utf-8")
    report = intent.committed_ref_intent(
        root=tmp_path,
        operation="candidate.accept",
        desired=NEW,
    )

    assert report["gap"] == "ref_intent_missing"
    assert not path.exists()


def test_public_abort_reports_invalid_stored_phase(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    written = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json"
    model = intent._read(path)  # noqa: SLF001
    assert model is not None
    invalid = model.model_copy(update={"phase": "unexpected"})
    monkeypatch.setattr(intent, "_read", lambda _path: invalid)

    report = intent.claim_ref_intent(
        root=tmp_path,
        ref_name="refs/heads/dev",
        update=_update(),
        operation="candidate.accept",
        phase="aborted",
        plan_digest=PLAN,
    )

    assert report["gap"] == "ref_intent_not_prepared"


def test_invalid_cleanup_preserves_file_replaced_by_valid_intent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    written = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json"
    model = intent._read(path)  # noqa: SLF001
    assert model is not None
    reads = iter((None, model))
    monkeypatch.setattr(intent, "_read", lambda _path: next(reads))

    report = intent.committed_ref_intent(
        root=tmp_path,
        operation="candidate.accept",
        desired=NEW,
    )

    assert report["gap"] == "ref_intent_missing"
    assert path.exists()
