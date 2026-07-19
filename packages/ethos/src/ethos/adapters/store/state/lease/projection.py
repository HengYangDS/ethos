"""Lane Lease read model and payload projection."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Any

from ethos_core.normalization.core import string_sequence

if TYPE_CHECKING:
    from pathlib import Path


def active_leases(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    now = datetime.now(UTC)
    try:
        rows = lease_rows(db_path)
    except sqlite3.Error:
        return []
    leases: list[dict[str, Any]] = []
    for row in rows:
        try:
            expires_at = datetime.fromisoformat(row[3])
        except (TypeError, ValueError):
            continue
        if expires_at <= now:
            continue
        leases.append(
            {
                "id": row[0],
                "subject": row[1],
                "expires_at": row[3],
                **lease_contract_fields(json_object(row[4])),
                "payload": json_object(row[4]),
            }
        )
    return leases


def lease_rows(db_path: Path) -> list[sqlite3.Row | tuple[Any, ...]]:
    try:
        with closing(sqlite3.connect(db_path)) as connection:
            return _selectlease_rows(connection)
    except sqlite3.Error:
        uri = f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            return _selectlease_rows(connection)


def _selectlease_rows(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row | tuple[Any, ...]]:
    return connection.execute(
        """
        select id, subject, owner, expires_at, payload_json
        from leases
        order by subject, id
        """,
    ).fetchall()


def json_object(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def integer_value(value: object) -> int:
    """Normalize a lease integer field without trusting an untyped payload."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def lease_contract_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "lane_incarnation_id": str(payload.get("lane_incarnation_id") or ""),
        "lease_id": str(payload.get("lease_id") or ""),
        "lane_ref": str(payload.get("lane_ref") or ""),
        "holder_ref": str(payload.get("holder_ref") or ""),
        "epoch": integer_value(payload.get("epoch")),
        "issued_at": str(payload.get("issued_at") or ""),
        "renewed_at": str(payload.get("renewed_at") or ""),
        "expected_head": str(payload.get("expected_head") or ""),
        "claim_id": str(payload.get("claim_id") or ""),
        "path_scope": string_sequence(payload.get("path_scope"), drop_empty=True),
    }
