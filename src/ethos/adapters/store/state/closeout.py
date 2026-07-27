"""Durable target-scoped ownerless-closeout fences."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from contextlib import closing
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn
from uuid import UUID
from uuid import uuid4

from ethos.adapters.store.state.lease.projection import observe_lease_row
from ethos.adapters.store.state.schema import initialize_closeout_fence_connection
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import read_only_state_uri
from ethos.adapters.store.state.schema import validate_current_closeout_fence_schema
from ethos.adapters.store.state.schema import validate_current_lease_schema
from ethos.contracts.coordination import HolderRef
from ethos.contracts.resolution.closeout import OwnerlessCloseoutFenceBinding

if TYPE_CHECKING:
    from ethos.contracts.coordination import LaneLease

_SELECT = """select subject, expected_head, decision_id, executor_ref, accepted_branch,
accepted_head, target_binding_digest, payload_json from closeout_fences where subject = ?"""
_FENCE_ROW_FIELDS = 8
_LEASE_ROW_FIELDS = 5
_OBSERVED_FENCE_FIELDS = 2
_LEASE_INVALID = "lease_invalid"
_GIT_OID = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_PAYLOAD_FIELDS = {
    "acquisition_id",
    "target_path",
    "lane_incarnation_id",
    "observation_digest",
    "decision_sha256",
    "chronicle_digest",
}


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _record(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, object]:
    if len(row) != _FENCE_ROW_FIELDS or any(
        type(row[index]) is not str for index in range(_FENCE_ROW_FIELDS)
    ):
        _fail("lane_closeout_fence_binding_invalid", "unknown")
    subject = row[0]
    payload = json.loads(row[7])
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_FIELDS:
        _fail("lane_closeout_fence_binding_invalid", subject)
    if any(type(payload[field]) is not str for field in _PAYLOAD_FIELDS):
        _fail("lane_closeout_fence_binding_invalid", subject)
    executor_ref = _canonical_holder(row[3], subject)
    binding = {
        "subject": subject,
        "expected_head": row[1],
        "decision_id": row[2],
        "executor_ref": executor_ref,
        "accepted_branch": row[4],
        "accepted_head": row[5],
        "payload": {
            **_validated_payload(
                OwnerlessCloseoutFenceBinding(
                    subject=subject,
                    expected_head=row[1],
                    decision_id=row[2],
                    executor_ref=executor_ref,
                    accepted_branch=row[4],
                    accepted_head=row[5],
                    target_path=payload["target_path"],
                    lane_incarnation_id=payload["lane_incarnation_id"],
                    observation_digest=payload["observation_digest"],
                    decision_sha256=payload["decision_sha256"],
                    chronicle_digest=payload["chronicle_digest"],
                )
            ),
            "acquisition_id": _validated_acquisition_id(payload["acquisition_id"], subject),
        },
    }
    target_binding_digest = hashlib.sha256(_canonical(binding).encode()).hexdigest()
    if row[6] != target_binding_digest:
        _fail("lane_closeout_fence_binding_invalid", subject)
    return {**binding, "target_binding_digest": target_binding_digest}


def _fail(gap: str, subject: str) -> NoReturn:
    message = f"{gap}:{subject}"
    raise ValueError(message)


def _canonical_holder(raw: object, subject: str) -> str:
    if not isinstance(raw, str):
        _fail("lane_closeout_fence_binding_invalid", subject)
    if type(raw) is not str:
        _fail("lane_closeout_fence_binding_invalid", subject)
    try:
        canonical = HolderRef.parse(raw).serialize()
    except (TypeError, ValueError):
        _fail("lane_closeout_fence_binding_invalid", subject)
    if canonical != raw:
        _fail("lane_closeout_fence_binding_invalid", subject)
    return canonical


def _validated_acquisition_id(raw: object, subject: str) -> str:
    if not isinstance(raw, str):
        _fail("lane_closeout_fence_binding_invalid", subject)
    if type(raw) is not str:
        _fail("lane_closeout_fence_binding_invalid", subject)
    try:
        canonical = str(UUID(raw))
    except (AttributeError, TypeError, ValueError):
        _fail("lane_closeout_fence_binding_invalid", subject)
    if canonical != raw:
        _fail("lane_closeout_fence_binding_invalid", subject)
    return canonical


def _has_unexpired_lease(connection: sqlite3.Connection, *, subject: str) -> bool:
    """Keep ownerless closeout fenced only by a current, unambiguous lease."""
    try:
        leases = _validated_lease_rows(connection)
    except (TypeError, ValueError):
        return True
    now = datetime.now(UTC)
    return any(
        lease.lane_ref == subject and expires.astimezone(UTC) > now for lease, expires in leases
    )


def _validated_payload(binding: OwnerlessCloseoutFenceBinding) -> dict[str, str]:
    """Validate and render the durable target facts for one exact fence binding."""
    subject = binding.subject
    expected_head = binding.expected_head
    decision_id = binding.decision_id
    accepted_branch = binding.accepted_branch
    accepted_head = binding.accepted_head
    target_path = binding.target_path
    lane_incarnation_id = binding.lane_incarnation_id
    observation_digest = binding.observation_digest
    decision_sha256 = binding.decision_sha256
    chronicle_digest = binding.chronicle_digest
    values = (
        subject,
        expected_head,
        decision_id,
        accepted_branch,
        accepted_head,
        target_path,
        lane_incarnation_id,
        observation_digest,
        decision_sha256,
        chronicle_digest,
    )
    if any(type(value) is not str for value in values):
        _fail("lane_closeout_fence_binding_invalid", "unknown")
    path = Path(target_path)
    checks = (
        bool(subject) and subject == subject.strip(),
        bool(decision_id) and decision_id == decision_id.strip(),
        bool(accepted_branch) and accepted_branch == accepted_branch.strip(),
        bool(lane_incarnation_id) and lane_incarnation_id == lane_incarnation_id.strip(),
        bool(_GIT_OID.fullmatch(expected_head)),
        bool(_GIT_OID.fullmatch(accepted_head)),
        path.is_absolute(),
        bool(_SHA256.fullmatch(observation_digest)),
        bool(_SHA256.fullmatch(decision_sha256)),
        bool(_SHA256.fullmatch(chronicle_digest)),
    )
    if not all(checks):
        _fail("lane_closeout_fence_binding_invalid", subject)
    return {
        "target_path": path.resolve(strict=False).as_posix(),
        "lane_incarnation_id": lane_incarnation_id,
        "observation_digest": observation_digest,
        "decision_sha256": decision_sha256,
        "chronicle_digest": chronicle_digest,
    }


def closeout_fence_exists_from_connection(connection: sqlite3.Connection, *, subject: str) -> bool:
    """Return whether an exact subject fence exists in the current transaction."""
    if not validate_current_closeout_fence_schema(connection):
        return False
    return (
        connection.execute("select 1 from closeout_fences where subject = ?", (subject,)).fetchone()
        is not None
    )


def acquire_closeout_fence(
    db_path: Path, *, binding: OwnerlessCloseoutFenceBinding
) -> dict[str, object]:
    """Atomically reserve one ownerless target against lease acquisition."""
    subject = binding.subject
    expected_head = binding.expected_head
    decision_id = binding.decision_id
    executor_ref = _canonical_holder(binding.executor_ref, "unknown")
    accepted_branch = binding.accepted_branch
    accepted_head = binding.accepted_head
    payload_base = _validated_payload(binding)
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
            current = _record(row) if row is not None else None
            current_payload = current["payload"] if current is not None else None
            acquisition_id = (
                _validated_acquisition_id(current_payload.get("acquisition_id"), subject)
                if isinstance(current_payload, dict)
                else str(uuid4())
            )
            payload = {**payload_base, "acquisition_id": acquisition_id}
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
            if current is not None:
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


class OwnerlessCloseoutStateError(ValueError):
    """Classified fail-closed state observation failure."""

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind}:{detail}")
        self.kind = kind
        self.detail = detail


def observe_ownerless_closeout_state(
    db_path: Path,
    *,
    subject: str,
    observed_fence: tuple[str, dict[str, object] | None] | None = None,
) -> tuple[str, dict[str, object] | None]:
    """Validate raw lease and fence facts without projecting damage as absence."""
    snapshot = _closeout_state_snapshot(db_path)
    if snapshot is None:
        return "absent", None
    leases, fence_schema = snapshot
    now = datetime.now(UTC)
    for lease, expires in leases:
        if lease.lane_ref == subject and expires.astimezone(UTC) > now:
            _state_error("coordinated", "lease")
    if observed_fence is not None:
        if not fence_schema:
            _state_error("fence_unverifiable", "state")
        return _validated_observed_fence(observed_fence)
    if not fence_schema:
        return "absent", None
    fence = probe_closeout_fence(db_path, subject=subject)
    if fence[0] == "unverifiable":
        _state_error("fence_unverifiable", "state")
    return fence


def _closeout_state_snapshot(
    db_path: Path,
) -> tuple[list[tuple[LaneLease, datetime]], bool] | None:
    if not os.path.lexists(db_path):
        sidecars = ("-wal", "-shm", "-journal")
        if any(os.path.lexists(Path(f"{db_path}{suffix}")) for suffix in sidecars):
            _state_error("state_unverifiable", "sidecar")
        return None
    try:
        metadata = db_path.lstat()
        if db_path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            _state_error("state_unverifiable", "database")
        with closing(sqlite3.connect(read_only_state_uri(db_path), uri=True)) as connection:
            if not validate_current_lease_schema(connection):
                _state_error("state_unverifiable", "database")
            try:
                leases = _validated_lease_rows(connection)
            except (TypeError, ValueError) as error:
                _state_error("state_unverifiable", "lease", error)
            fence_schema = validate_current_closeout_fence_schema(connection)
    except OwnerlessCloseoutStateError:
        raise
    except (OSError, RuntimeError, sqlite3.Error, TypeError, ValueError) as error:
        _state_error("state_unverifiable", "database", error)
    return leases, fence_schema


def _validated_lease_rows(
    connection: sqlite3.Connection,
) -> list[tuple[LaneLease, datetime]]:
    rows = connection.execute(
        "select id, subject, owner, expires_at, payload_json from leases order by subject, id"
    ).fetchall()
    return [_validated_lease(row) for row in rows]


def _validated_lease(
    row: sqlite3.Row | tuple[Any, ...],
) -> tuple[LaneLease, datetime]:
    if len(row) != _LEASE_ROW_FIELDS:
        raise ValueError(_LEASE_INVALID)
    observation = observe_lease_row(row)
    if observation.state == "unknown" or observation.lease is None:
        raise ValueError(_LEASE_INVALID)
    return observation.lease, observation.lease.expires_at


def _validated_observed_fence(
    observed: tuple[str, dict[str, object] | None],
) -> tuple[str, dict[str, object] | None]:
    if type(observed) is not tuple or len(observed) != _OBSERVED_FENCE_FIELDS:
        _state_error("fence_unverifiable", "state")
    state, fence = observed
    if state == "absent" and fence is None:
        return observed
    if (
        state != "present"
        or not isinstance(fence, dict)
        or set(fence)
        != {
            "subject",
            "expected_head",
            "decision_id",
            "executor_ref",
            "accepted_branch",
            "accepted_head",
            "payload",
            "target_binding_digest",
        }
    ):
        _state_error("fence_unverifiable", "state")
    try:
        validated = _record(
            (
                fence["subject"],
                fence["expected_head"],
                fence["decision_id"],
                fence["executor_ref"],
                fence["accepted_branch"],
                fence["accepted_head"],
                fence["target_binding_digest"],
                _canonical(fence["payload"]),
            )
        )
    except (TypeError, ValueError) as error:
        _state_error("fence_unverifiable", "state", error)
    return "present", validated


def _state_error(kind: str, detail: str, cause: Exception | None = None) -> NoReturn:
    error = OwnerlessCloseoutStateError(kind, detail)
    if cause is None:
        raise error
    raise error from cause
