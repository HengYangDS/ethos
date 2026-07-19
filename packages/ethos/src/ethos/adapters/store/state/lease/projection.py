"""Lane Lease read model and payload projection."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
from contextlib import closing
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos.adapters.store.state.schema import read_only_state_uri
from ethos_core.contracts.coordination import HolderRef
from ethos_core.contracts.coordination import LaneLease
from ethos_core.normalization.core import string_sequence


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
    with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
        return _selectlease_rows(connection)


def lease_inventory_rows(db_path: Path) -> list[dict[str, Any]]:
    """Return all lease rows with raw-payload validity retained for maintenance."""
    if not db_path.exists():
        return []
    with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
        return lease_inventory_rows_from_connection(connection)


def lease_inventory_rows_from_connection(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    """Return maintenance lease rows from the caller's current transaction."""
    rows = _selectlease_rows(connection)
    inventory: list[dict[str, Any]] = []
    for row in rows:
        raw_payload = str(row[4])
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError:
            parsed = None
        inventory.append(
            {
                "id": str(row[0]),
                "subject": str(row[1]),
                "owner": str(row[2]),
                "expires_at": str(row[3]),
                "payload_json": raw_payload,
                "payload": parsed if isinstance(parsed, dict) else {},
                "payload_valid": isinstance(parsed, dict),
            }
        )
    return inventory


def lease_inventory_rows(db_path: Path) -> list[dict[str, Any]]:
    """Return all lease rows with raw-payload validity retained for maintenance."""
    if not db_path.exists():
        return []
    rows = lease_rows(db_path)
    inventory: list[dict[str, Any]] = []
    for row in rows:
        raw_payload = str(row[4])
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError:
            parsed = None
        inventory.append(
            {
                "id": str(row[0]),
                "subject": str(row[1]),
                "owner": str(row[2]),
                "expires_at": str(row[3]),
                "payload_json": raw_payload,
                "payload": parsed if isinstance(parsed, dict) else {},
                "payload_valid": isinstance(parsed, dict),
            }
        )
    return inventory


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


def lease_maintenance_inventory(
    root: Path,
    *,
    observed: datetime,
    branch_refs: set[str],
    worktree_branches: set[str],
) -> tuple[dict[str, Any], set[str]]:
    """Return conservative lease delete candidates and live expected HEADs."""
    db_path = root / ".ethos" / "state" / "state.sqlite"
    candidates: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    live_heads: set[str] = set()
    try:
        rows = lease_inventory_rows(db_path)
    except sqlite3.Error as exc:
        return {
            "delete_candidates": [],
            "retained": [],
            "error": exc.__class__.__name__,
        }, live_heads
    for row in rows:
        reasons, expires = _lease_retention_reasons(
            root,
            row,
            observed=observed,
            branch_refs=branch_refs,
            worktree_branches=worktree_branches,
        )
        payload = row["payload"]
        expected_head = str(payload.get("expected_head") or "")
        if expires is not None and expires > observed and expected_head:
            live_heads.add(expected_head)
        item = {
            "id": row["id"],
            "subject": row["subject"],
            "owner": row["owner"],
            "expires_at": row["expires_at"],
            "payload_sha256": hashlib.sha256(row["payload_json"].encode("utf-8")).hexdigest(),
        }
        if reasons:
            retained.append({**item, "reasons": reasons})
        else:
            candidates.append(item)
    return {"delete_candidates": candidates, "retained": retained}, live_heads


def _lease_retention_reasons(
    root: Path,
    row: dict[str, Any],
    *,
    observed: datetime,
    branch_refs: set[str],
    worktree_branches: set[str],
) -> tuple[list[str], datetime | None]:
    reasons, expires = _lease_time_reasons(row, observed)
    payload = row["payload"]
    if not row["payload_valid"]:
        reasons.append("malformed_payload")
    if row["payload_valid"] and _lease_contract_ambiguous(row):
        reasons.append("ambiguous_lease")
    subject = str(row["subject"])
    if not _valid_branch_subject(root, subject):
        reasons.append("malformed_subject")
    if subject in branch_refs:
        reasons.append("branch_ref_present")
    if subject in worktree_branches:
        reasons.append("linked_worktree_present")
    recorded_path = payload.get("path") if row["payload_valid"] else None
    if recorded_path is not None and not isinstance(recorded_path, str):
        reasons.append("malformed_recorded_path")
    elif isinstance(recorded_path, str) and recorded_path:
        path = Path(recorded_path)
        path = path if path.is_absolute() else root / path
        if os.path.lexists(path):
            reasons.append("recorded_path_present")
    return sorted(set(reasons)), expires


def _lease_contract_ambiguous(row: dict[str, Any]) -> bool:
    payload = row["payload"]
    epoch = payload.get("epoch")
    if isinstance(epoch, bool) or not isinstance(epoch, int):
        return True
    try:
        lease = LaneLease(
            lane_incarnation_id=payload.get("lane_incarnation_id"),
            lease_id=payload.get("lease_id"),
            lane_ref=payload.get("lane_ref"),
            holder_ref=HolderRef.parse(str(payload.get("holder_ref") or "")),
            epoch=epoch,
            issued_at=payload.get("issued_at"),
            renewed_at=payload.get("renewed_at"),
            expires_at=row["expires_at"],
            expected_head=payload.get("expected_head", ""),
            claim_id=payload.get("claim_id", ""),
            path_scope=payload.get("path_scope", ()),
        )
    except (TypeError, ValueError):
        return True
    return (
        lease.lease_id != row["id"]
        or lease.lane_ref != row["subject"]
        or lease.holder_ref.serialize() != row["owner"]
        or payload.get("coordination_scope") != "git_common_directory"
        or payload.get("mints_authority") is not False
        or payload.get("filesystem_fence") is not False
        or payload.get("distributed_lock") is not False
    )


def _valid_branch_subject(root: Path, subject: str) -> bool:
    if not subject:
        return False
    completed = subprocess.run(
        ["git", "check-ref-format", f"refs/heads/{subject}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _lease_time_reasons(
    row: dict[str, Any], observed: datetime
) -> tuple[list[str], datetime | None]:
    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except (TypeError, ValueError):
        return ["malformed_expiry"], None
    if expires.tzinfo is None:
        return ["malformed_expiry"], None
    normalized = expires.astimezone(UTC)
    return (["unexpired"] if normalized > observed else []), normalized


def live_lease_expected_heads(
    connection: sqlite3.Connection | None,
    observed: datetime,
) -> set[str]:
    """Return unexpired lease HEADs visible in the caller transaction."""
    if connection is None:
        return set()
    heads: set[str] = set()
    for row in lease_inventory_rows_from_connection(connection):
        _, expires = _lease_time_reasons(row, observed)
        expected_head = str(row["payload"].get("expected_head") or "")
        if expires is not None and expires > observed and expected_head:
            heads.add(expected_head)
    return heads
