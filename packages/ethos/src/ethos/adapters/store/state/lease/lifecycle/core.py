from __future__ import annotations

import contextlib
import datetime as dt
import json
import operator
import sqlite3
import uuid
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.state.lease.projection import json_object
from ethos.adapters.store.state.lease.projection import lease_contract_fields
from ethos_core.contracts.coordination import HolderRef
from ethos_core.normalization.core import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

type LeaseRow = sqlite3.Row | tuple[Any, ...]
type Payload = dict[str, Any]

_SCHEMA = (
    "create table if not exists leases (id text primary key,subject text not null,"
    "owner text not null,expires_at text not null,payload_json text not null)"
)
_INSERT = "insert into leases(id,subject,owner,expires_at,payload_json) values (?,?,?,?,?)"
_SELECT = "select id,subject,owner,expires_at,payload_json from leases where subject=? order by id"
_UPDATE = "update leases set owner=?,expires_at=?,payload_json=? where id=?"
_NON_AUTHORITY_FIELDS = ("mints_authority", "filesystem_fence", "distributed_lock")
_OFFER_KEYS = "offer_id subject holder_ref target_holder_ref lease_id epoch expected_head state"
_OFFER_UPDATE_KEYS = "handoff_state handoff_offer_id handoff_target_holder_ref handoff_offered_at"
_ACCEPT_UPDATE_KEYS = "holder_ref epoch renewed_at handoff_state handoff_accepted_at"
_NEW_KEYS = "lane_incarnation_id lease_id lane_ref holder_ref epoch path_scope coordination_scope"
_RECORD_KEYS = "id subject expires_at payload"


def _error(gap: str, *facts: object) -> ValueError:
    return ValueError(gap + ":" + "!=".join(map(str, facts)))


def initialize_lease_state(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(sqlite3.connect(db_path)) as connection:
        for statement in ("pragma journal_mode=wal", "pragma foreign_keys=on", _SCHEMA):
            connection.execute(statement)
        connection.commit()


def acquire_lease(
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    ttl_seconds: int = 86400,
    payload: Payload | None = None,
) -> Payload:
    holder_ref = HolderRef.parse(holder_ref).serialize()
    lease_id, now = f"lease:{uuid.uuid4()}", dt.datetime.now(dt.UTC)
    expires_at = (now + dt.timedelta(seconds=ttl_seconds)).isoformat()
    normalized = _new_payload(subject, holder_ref, lease_id, dict(payload or {}), now)
    initialize_lease_state(db_path)
    with _transaction(db_path) as connection:
        if connection.execute(_SELECT, (subject,)).fetchone():
            raise _error("lane_lease_" + "conflict", subject)
        values = (lease_id, subject, holder_ref, expires_at, json.dumps(normalized, sort_keys=True))
        connection.execute(_INSERT, values)
    return _record((lease_id, subject, holder_ref, expires_at, ""), normalized)


def renew_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    ttl_seconds: int = 86400,
) -> Payload:
    return _refresh(db_path, _cas(locals()), ttl_seconds, require_expired=False)


def resume_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    ttl_seconds: int = 86400,
    contrary_decision: bool = False,
) -> Payload:
    if contrary_decision:
        raise _error("lease_resume_" + "blocked_by_decision", subject)
    return _refresh(db_path, _cas(locals()), ttl_seconds, require_expired=True)


def offer_lease_handoff(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    target_holder_ref: str,
    expected_head: str,
) -> Payload:
    HolderRef.parse(target_holder_ref)
    offer_id = f"handoff-offer:{uuid.uuid4()}"
    offered_at = dt.datetime.now(dt.UTC).isoformat()
    cas = _cas(locals())
    updates = dict(
        zip(
            _OFFER_UPDATE_KEYS.split(),
            ("offered", offer_id, target_holder_ref, offered_at),
            strict=True,
        )
    )
    _change_current(db_path, cas, updates)
    keys = _OFFER_KEYS.split()
    values = (offer_id, *cas[:2], target_holder_ref, *cas[2:], "offered")
    return dict(zip(keys, values, strict=True))


def accept_lease_handoff(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    target_holder_ref: str,
    offer_id: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    holder_quiesced: bool,
    ttl_seconds: int = 86400,
) -> Payload:
    HolderRef.parse(target_holder_ref)
    if not holder_quiesced:
        raise _error("lease_handoff_" + "holder_not_quiesced", subject)
    now = dt.datetime.now(dt.UTC)
    expires_at = (now + dt.timedelta(seconds=ttl_seconds)).isoformat()
    values = (target_holder_ref, expected_epoch + 1, now.isoformat(), "accepted", now.isoformat())
    updates = dict(zip(_ACCEPT_UPDATE_KEYS.split(), values, strict=True))
    cas = (subject, None, expected_lease_id, expected_epoch, expected_head)
    checks = (
        ("handoff_offer", offer_id, "handoff_offer_id"),
        ("handoff_target", target_holder_ref, "handoff_target_holder_ref"),
    )
    options = (None, expires_at, target_holder_ref, checks)
    return _change_current(db_path, cas, updates, options)


def advance_lease_head(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    db_path: Path,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    old_head: str,
    new_head: str,
) -> Payload:
    HolderRef.parse(holder_ref)
    initialize_lease_state(db_path)
    return _change_current(
        db_path,
        _cas(locals(), head="old_head"),
        {"expected_head": new_head, "head_observed_at": dt.datetime.now(dt.UTC).isoformat()},
    )


def expected_current_lease(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    connection: sqlite3.Connection,
    *,
    subject: str,
    holder_ref: str,
    expected_lease_id: str,
    expected_epoch: int,
    expected_head: str,
    require_expired: bool,
) -> tuple[LeaseRow, Payload]:
    cas = (subject, holder_ref, expected_lease_id, expected_epoch, expected_head)
    return _checked(connection, cas, require_expired)


def _refresh(db_path, cas, ttl_seconds, *, require_expired):
    HolderRef.parse(cas[1])
    initialize_lease_state(db_path)
    now = dt.datetime.now(dt.UTC)
    expires_at = (now + dt.timedelta(seconds=ttl_seconds)).isoformat()
    options = (require_expired, expires_at, "", ())
    return _change_current(db_path, cas, {"renewed_at": now.isoformat()}, options)


def _change_current(db_path, cas, updates, options=None):
    require_expired, expires_at, owner, checks = options or (False, "", "", ())
    with _transaction(db_path) as connection:
        row, payload = _checked(connection, cas, require_expired, checks)
        payload.update(updates)
        values = (
            owner or str(row[2]),
            expires_at or str(row[3]),
            json.dumps(payload, sort_keys=True),
            str(row[0]),
        )
        connection.execute(_UPDATE, values)
    return _record(row, payload, expires_at=expires_at)


def _checked(connection, cas, require_expired, checks=()):
    subject, holder_ref, lease_id, epoch, head = cas
    row = _row(connection, subject)
    payload = json_object(row[4])
    _equal("lease_id", lease_id, str(row[0]))
    if holder_ref is not None:
        _equal("holder", holder_ref, str(payload.get("holder_ref") or ""))
    actual_epoch = int(payload.get("epoch") or 0)
    if actual_epoch != epoch:
        raise _error("lease_epoch_" + "stale", epoch, actual_epoch)
    _equal("head", head, str(payload.get("expected_head") or ""))
    for kind, expected, key in checks:
        _equal(kind, expected, str(payload.get(key) or ""))
    if require_expired is not None and _expired(str(row[3])) != require_expired:
        state = "not_expired" if require_expired else "expired"
        raise _error("lease_" + state, subject)
    return row, payload


def _new_payload(subject, holder_ref, lease_id, payload, now):
    stamp = now.isoformat()
    values = (
        str(payload.get("lane_incarnation_id") or f"lane-incarnation:{uuid.uuid4()}"),
        lease_id,
        subject,
        holder_ref,
        int(payload.get("epoch") or 1),
        string_sequence(payload.get("path_scope"), drop_empty=True),
        "git_common_directory",
    )
    payload.update(zip(_NEW_KEYS.split(), values, strict=True))
    defaults = {"issued_at": stamp, "renewed_at": stamp, "expected_head": "", "claim_id": ""}
    payload.update({key: str(payload.get(key) or value) for key, value in defaults.items()})
    payload.update(dict.fromkeys(_NON_AUTHORITY_FIELDS, False))
    return payload


def _cas(values, *, head="expected_head"):
    subject, holder, lease, epoch, value = operator.itemgetter(
        "subject", "holder_ref", "expected_lease_id", "expected_epoch", head
    )(values)
    return *map(str, (subject, holder, lease)), int(epoch), str(value)


@contextlib.contextmanager
def _transaction(db_path):
    with contextlib.closing(sqlite3.connect(db_path)) as connection:
        connection.execute("pragma foreign_keys=on")
        connection.execute("begin immediate")
        yield connection
        connection.commit()


def _row(connection, subject):
    rows = connection.execute(_SELECT, (subject,)).fetchall()
    if len(rows) != 1:
        gap = "work_lane_missing_lease" if not rows else "lane_lease_ambiguous"
        raise _error(gap, subject)
    return rows[0]


def _record(row, payload, *, expires_at=""):
    record = lease_contract_fields(payload)
    values = (str(row[0]), str(row[1]), expires_at or str(row[3]), payload)
    record.update(zip(_RECORD_KEYS.split(), values, strict=True))
    return record


def _equal(kind, expected, actual):
    if expected == actual:
        return
    gaps = {"holder": "lease_holder_mismatch", "lease_id": "lease_id_stale"}
    gaps |= {"head": "lease_head_stale", "handoff_offer": "lease_handoff_offer_stale"}
    gaps["handoff_target"] = "lease_handoff_target_mismatch"
    gap = gaps.get(kind, f"lease_{kind}_mismatch")
    raise _error(gap, expected, actual)


def _expired(value):
    try:
        expires_at = dt.datetime.fromisoformat(value)
    except ValueError:
        return True
    expires_at = expires_at.replace(tzinfo=dt.UTC) if expires_at.tzinfo is None else expires_at
    return expires_at <= dt.datetime.now(dt.UTC)
