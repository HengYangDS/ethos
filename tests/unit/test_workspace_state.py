from __future__ import annotations

import sqlite3
from pathlib import Path

from ethos_workspace.state import (
    append_chronicle_event,
    append_event,
    initialize_state,
    list_chronicle_events,
    list_events,
)


def test_state_initialization_creates_expected_tables(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"

    initialize_state(db_path)

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }
    assert {
        "schema_migrations",
        "events",
        "chronicle_events",
        "sessions",
        "leases",
        "gate_runs",
        "action_runs",
        "evidence_index",
        "cache_entries",
    } <= tables


def test_chronicle_append_is_transactional(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)

    append_chronicle_event(
        db_path,
        event_type="self.audit",
        subject="repo:ethos",
        payload={"ok": True},
    )

    events = list_chronicle_events(db_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "self.audit"
    assert events[0]["payload"] == {"ok": True}


def test_event_append_is_transactional(tmp_path: Path) -> None:
    db_path = tmp_path / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)

    append_event(
        db_path,
        event_type="quality.claims",
        subject="repo:ethos",
        payload={"ok": True},
    )

    events = list_events(db_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "quality.claims"
    assert events[0]["payload"] == {"ok": True}
