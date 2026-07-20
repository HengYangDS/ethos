from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.store.state.lease.lifecycle.core as lease
import ethos.adapters.store.state.lease.lifecycle.effects as effects
import ethos.adapters.store.state.lease.projection as projection
import ethos.adapters.store.state.schema as state_schema

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _rejects(pattern: str, call: Callable[[], object]) -> None:
    with pytest.raises((RuntimeError, ValueError), match=pattern):
        call()


def _legacy(path: Path, cache: str = "") -> None:
    sql = "create table leases(id text primary key,owner text,resource text,expires_at text,created_at text);create table cache_entries(value text);insert into leases values('blank','owner','','expiry','created');insert into leases values('kept','owner','work/x','expiry','created');"  # fmt: skip
    with closing(sqlite3.connect(path)) as db:
        db.executescript(sql)
        if cache:
            db.execute("insert into cache_entries values(?)", (cache,))
        db.commit()


def test_state_and_lease_fail_closed_matrix(tmp_path: Path) -> None:
    migrated = tmp_path / "migrated.sqlite"
    _legacy(migrated)
    state_schema.initialize_state(migrated)
    with closing(sqlite3.connect(migrated)) as db:
        rows = db.execute("select id,subject,payload_json from leases").fetchall()
        cache = db.execute("select name from sqlite_master where name='cache_entries'").fetchone()
    assert (rows, cache) == ([("kept", "work/x", "{}")], None)
    blocked = tmp_path / "blocked.sqlite"
    _legacy(blocked, "live")
    _rejects("cache_entries_not_empty", lambda: state_schema.initialize_state(blocked))
    db_path = tmp_path / "leases.sqlite"
    current = lease.acquire_lease(db_path, subject="work/x", holder_ref="agent:test:case:owner", payload={"expected_head": "a" * 40})  # fmt: skip
    request = {"subject": "work/x", "holder_ref": current["holder_ref"], "expected_lease_id": current["lease_id"], "expected_epoch": current["epoch"], "expected_head": "a" * 40}  # fmt: skip
    _rejects("blocked_by_decision", lambda: lease.resume_lease(db_path, **request, contrary_decision=True))  # fmt: skip
    with closing(sqlite3.connect(db_path)) as db:
        _rejects("not_expired", lambda: lease.expected_current_lease(db, **request, require_expired=True))  # fmt: skip
        db.execute("insert into leases values(?,?,?,?,?)", ("lease:second", "work/x", current["holder_ref"], current["expires_at"], "{}"))  # fmt: skip
        db.commit()
        _rejects("lane_lease_ambiguous", lambda: lease.expected_current_lease(db, **request, require_expired=False))  # fmt: skip
    assert effects.update_lease_payload(db_path, subject="missing", payload={}) == {}
    assert effects.delete_lease(tmp_path / "missing.sqlite", subject="work/x") == 0
    _rejects("candidate_drift", lambda: effects.delete_exact_leases(db_path, [{"id": "missing"}]))
    assert projection.integer_value(value=True) == 0
