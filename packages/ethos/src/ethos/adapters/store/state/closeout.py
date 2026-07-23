"""Durable target-scoped ownerless-closeout fences."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos.adapters.store.state.schema import initialize_closeout_fence_connection
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import read_only_state_uri
from ethos.adapters.store.state.schema import validate_current_closeout_fence_schema
from ethos_core.contracts.coordination import HolderRef

_SELECT = """select subject, expected_head, decision_id, executor_ref, accepted_branch,
accepted_head, target_binding_digest, payload_json from closeout_fences where subject = ?"""
_GIT_OID = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_WCP_SCHEMA_VERSION = "workstation.repo-family-governance.v1"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _record(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, object]:
    return {
        "subject": str(row[0]),
        "expected_head": str(row[1]),
        "decision_id": str(row[2]),
        "executor_ref": str(row[3]),
        "accepted_branch": str(row[4]),
        "accepted_head": str(row[5]),
        "target_binding_digest": str(row[6]),
        "payload": json.loads(str(row[7])),
    }


def _fail(gap: str, subject: str) -> None:
    message = f"{gap}:{subject}"
    raise ValueError(message)


def _has_unexpired_lease(connection: sqlite3.Connection, *, subject: str) -> bool:
    """Keep ownerless closeout fenced only by a current, unambiguous lease."""
    row = connection.execute(
        "select expires_at from leases where subject = ?", (subject,)
    ).fetchone()
    if row is None:
        return False
    try:
        expires_at = datetime.fromisoformat(str(row[0]))
    except ValueError:
        return True
    if expires_at.tzinfo is None:
        return True
    return expires_at.astimezone(UTC) > datetime.now(UTC)


def _validated_payload(  # noqa: PLR0913, RUF100 - exact durable fence binding
    *,
    subject: str,
    expected_head: str,
    decision_id: str,
    accepted_branch: str,
    accepted_head: str,
    target_path: str,
    lane_incarnation_id: str,
    observation_digest: str,
    decision_sha256: str,
    chronicle_digest: str,
    wcp_schema_version: str,
    wcp_decision_sha256: str,
    wcp_binding_digest: str,
) -> dict[str, str]:
    path = Path(target_path)
    checks = (
        subject.startswith("work/"),
        bool(decision_id.strip()),
        bool(accepted_branch.strip()),
        bool(lane_incarnation_id.strip()),
        bool(_GIT_OID.fullmatch(expected_head)),
        bool(_GIT_OID.fullmatch(accepted_head)),
        path.is_absolute(),
        bool(_SHA256.fullmatch(observation_digest)),
        bool(_SHA256.fullmatch(decision_sha256)),
        bool(_SHA256.fullmatch(chronicle_digest)),
        wcp_schema_version == _WCP_SCHEMA_VERSION,
        bool(_SHA256.fullmatch(wcp_decision_sha256)),
        decision_sha256 == wcp_decision_sha256,
        bool(_SHA256.fullmatch(wcp_binding_digest)),
    )
    if not all(checks):
        _fail("lane_closeout_fence_binding_invalid", subject)
    return {
        "target_path": path.resolve(strict=False).as_posix(),
        "lane_incarnation_id": lane_incarnation_id,
        "observation_digest": observation_digest,
        "decision_sha256": decision_sha256,
        "chronicle_digest": chronicle_digest,
        "wcp_schema_version": wcp_schema_version,
        "wcp_decision_sha256": wcp_decision_sha256,
        "wcp_binding_digest": wcp_binding_digest,
    }


def closeout_fence_exists_from_connection(connection: sqlite3.Connection, *, subject: str) -> bool:
    """Return whether an exact subject fence exists in the current transaction."""
    if not validate_current_closeout_fence_schema(connection):
        return False
    return (
        connection.execute("select 1 from closeout_fences where subject = ?", (subject,)).fetchone()
        is not None
    )


def acquire_closeout_fence(  # noqa: PLR0913, RUF100 - exact durable fence binding
    db_path: Path,
    *,
    subject: str,
    expected_head: str,
    decision_id: str,
    executor_ref: str,
    accepted_branch: str,
    accepted_head: str,
    target_path: str,
    lane_incarnation_id: str,
    observation_digest: str,
    decision_sha256: str,
    chronicle_digest: str,
    wcp_schema_version: str,
    wcp_decision_sha256: str,
    wcp_binding_digest: str,
) -> dict[str, object]:
    """Atomically reserve one ownerless target against lease acquisition."""
    executor_ref = HolderRef.parse(executor_ref).serialize()
    payload = _validated_payload(
        subject=subject,
        expected_head=expected_head,
        decision_id=decision_id,
        accepted_branch=accepted_branch,
        accepted_head=accepted_head,
        target_path=target_path,
        lane_incarnation_id=lane_incarnation_id,
        observation_digest=observation_digest,
        decision_sha256=decision_sha256,
        chronicle_digest=chronicle_digest,
        wcp_schema_version=wcp_schema_version,
        wcp_decision_sha256=wcp_decision_sha256,
        wcp_binding_digest=wcp_binding_digest,
    )
    payload_json = _canonical(payload)
    binding = {
        "subject": subject,
        "expected_head": expected_head,
        "decision_id": decision_id,
        "executor_ref": executor_ref,
        "accepted_branch": accepted_branch,
        "accepted_head": accepted_head,
        "payload": json.loads(payload_json),
    }
    target_binding_digest = hashlib.sha256(_canonical(binding).encode()).hexdigest()
    candidate = {**binding, "target_binding_digest": target_binding_digest}
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("pragma journal_mode = wal")
        connection.execute("begin immediate")
        try:
            initialize_state_connection(connection)
            initialize_closeout_fence_connection(connection)
            if _has_unexpired_lease(connection, subject=subject):
                _fail("lane_closeout_coordinated", subject)
            row = connection.execute(_SELECT, (subject,)).fetchone()
            if row is not None:
                current = _record(row)
                if current["decision_id"] != decision_id:
                    _fail("lane_closeout_target_competition", subject)
                if current != candidate:
                    _fail("lane_closeout_fence_binding_mismatch", subject)
                result = current
            else:
                connection.execute(
                    """insert into closeout_fences(subject, expected_head, decision_id,
                    executor_ref, accepted_branch, accepted_head, target_binding_digest,
                    payload_json)
                    values (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        subject,
                        expected_head,
                        decision_id,
                        executor_ref,
                        accepted_branch,
                        accepted_head,
                        target_binding_digest,
                        payload_json,
                    ),
                )
                result = candidate
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return result


def release_closeout_fence(
    db_path: Path, *, subject: str, decision_id: str, target_binding_digest: str
) -> None:
    """Release only the exact decision and target binding through SQLite CAS."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("pragma journal_mode = wal")
        connection.execute("begin immediate")
        try:
            initialize_state_connection(connection)
            initialize_closeout_fence_connection(connection)
            cursor = connection.execute(
                """delete from closeout_fences
                where subject = ? and decision_id = ? and target_binding_digest = ?""",
                (subject, decision_id, target_binding_digest),
            )
            if cursor.rowcount != 1:
                _fail("lane_closeout_fence_release_stale", subject)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def get_closeout_fence(db_path: Path, *, subject: str) -> dict[str, object] | None:
    """Read one target fence without creating or mutating local state."""
    state, fence = probe_closeout_fence(db_path, subject=subject)
    return fence if state == "present" else None


def probe_closeout_fence(db_path: Path, *, subject: str) -> tuple[str, dict[str, object] | None]:
    """Distinguish an exact fence, explicit absence, and an unverifiable store."""
    if not db_path.is_file() or db_path.is_symlink():
        return "unverifiable", None
    try:
        with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
            try:
                current_schema = validate_current_closeout_fence_schema(connection)
            except RuntimeError:
                return "unverifiable", None
            if not current_schema:
                return "unverifiable", None
            row = connection.execute(_SELECT, (subject,)).fetchone()
        return ("present", _record(row)) if row is not None else ("absent", None)
    except (OSError, sqlite3.Error, TypeError, ValueError, json.JSONDecodeError):
        return "unverifiable", None
