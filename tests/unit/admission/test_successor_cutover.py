from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.admission.successor_cutover import load_envelope
from ethos.adapters.admission.successor_cutover import replace_lease

if TYPE_CHECKING:
    from pathlib import Path


def _write_envelope(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_envelope_requires_exact_external_digest(tmp_path: Path) -> None:
    path = tmp_path / "envelope.json"
    digest = _write_envelope(path, {"operation": "semantic-kernel-successor-cutover-v1"})

    assert load_envelope(path, digest)["operation"].endswith("-v1")
    with pytest.raises(ValueError, match="successor_envelope_digest_mismatch"):
        load_envelope(path, "0" * 64)


def test_envelope_rejects_group_writable_file(tmp_path: Path) -> None:
    path = tmp_path / "envelope.json"
    digest = _write_envelope(path, {"operation": "semantic-kernel-successor-cutover-v1"})
    path.chmod(0o660)

    with pytest.raises(ValueError, match="group_or_world_writable"):
        load_envelope(path, digest)


def test_lease_cutover_is_full_row_cas_and_single_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.sqlite"
    before_payload = json.dumps({"wire": "before"}, sort_keys=True)
    after_payload = json.dumps({"wire": "after"}, sort_keys=True)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "create table leases (id text primary key, subject text, owner text, expires_at text, payload_json text)"
        )
        connection.execute(
            "insert into leases values (?, ?, ?, ?, ?)",
            ("lease:one", "work/one", "actor:one", "later", before_payload),
        )
    monkeypatch.setattr(
        "ethos.adapters.admission.successor_cutover.state_database", lambda _root: db
    )
    before = {
        "id": "lease:one",
        "subject": "work/one",
        "owner": "actor:one",
        "expires_at": "later",
        "payload_json": before_payload,
        "payload_sha256": hashlib.sha256(before_payload.encode()).hexdigest(),
    }
    after = {
        **before,
        "owner": "actor:two",
        "payload_json": after_payload,
        "payload_sha256": hashlib.sha256(after_payload.encode()).hexdigest(),
    }
    envelope = {"lease_before": before, "lease_after": after}

    replace_lease(tmp_path, envelope)
    with sqlite3.connect(db) as connection:
        assert connection.execute("select owner, payload_json from leases").fetchone() == (
            "actor:two",
            after_payload,
        )
    with pytest.raises(ValueError, match="successor_incumbent_lease_drift"):
        replace_lease(tmp_path, envelope)


def test_lease_cutover_rejects_identity_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ethos.adapters.admission.successor_cutover.state_database",
        lambda _root: tmp_path / "unused.sqlite",
    )
    before = {
        "id": "lease:one",
        "subject": "work/one",
        "owner": "actor:one",
        "expires_at": "later",
        "payload_json": "{}",
        "payload_sha256": hashlib.sha256(b"{}").hexdigest(),
    }

    with pytest.raises(ValueError, match="successor_lease_identity_mismatch"):
        replace_lease(
            tmp_path,
            {"lease_before": before, "lease_after": {**before, "id": "lease:two"}},
        )
