"""Destructively replace one provable legacy Lease with the terminal wire."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.openspec.commitment import resolve_openspec_commitment_carrier
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.lifecycle.transitions import (
    replace_exact_lease_from_connection,
)
from ethos.adapters.store.state.lease.projection import LeaseRow
from ethos.adapters.store.state.lease.projection import lease_row
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseRecoveryRequest

if TYPE_CHECKING:
    from pathlib import Path


def recover_legacy_lease(
    *,
    root: Path,
    request: LeaseRecoveryRequest,
) -> dict[str, object]:
    """Normalize one same-holder legacy row from exact Git and Commitment facts."""
    repo = repository_root(root)
    branch = request.branch
    head = current_head(repo)
    database = state_database(repo)
    row = _raw_row(database, branch)
    payload = _legacy_payload(row.payload_json) if row is not None else {}
    canonical_holder, gaps = _observation_gaps(repo, request, row, payload, head)
    try:
        carrier = resolve_openspec_commitment_carrier(
            repo, change_id=request.change_id, tree_ref=head
        )
        binding = exact_commitment_fields(
            repo,
            head=head,
            carrier=carrier,
            change_id=request.change_id,
        )
    except ValueError as exc:
        gaps.append(str(exc))
    issued_at = _time(payload.get("issued_at"))
    renewed_at = _time(payload.get("renewed_at"))
    if issued_at is None:
        gaps.append("lease_issued_at_invalid")
    if renewed_at is None:
        gaps.append("lease_renewed_at_invalid")
    if gaps:
        return _report(branch, "block", "blocked", gaps, row, payload)

    assert row is not None
    assert issued_at is not None
    assert renewed_at is not None
    replacement = _replacement(
        request,
        row=row,
        payload=payload,
        holder_ref=canonical_holder,
        issued_at=issued_at,
        binding=binding,
    )
    if not request.apply:
        return _report(branch, "pass", "recoverable", [], row, payload, replacement)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        current = connection.execute(
            "select id, subject, owner, expires_at, payload_json from leases where subject = ?",
            (branch,),
        ).fetchone()
        if current is None or lease_row(current) != row:
            connection.rollback()
            return _report(
                branch,
                "block",
                "blocked",
                [f"lease_maintenance_candidate_drift:{request.lease_id}"],
                row,
                payload,
            )
        recovered = replace_exact_lease_from_connection(
            connection,
            current=row,
            replacement=replacement,
        )
        connection.commit()
    return {
        **_report(branch, "pass", "recovered", [], row, payload, replacement),
        "lease": recovered,
    }


def _observation_gaps(
    repo: Path,
    request: LeaseRecoveryRequest,
    row: LeaseRow | None,
    payload: dict[str, Any],
    head: str,
) -> tuple[str, list[str]]:
    gaps: list[str] = []
    try:
        holder = HolderRef.parse(request.holder_ref).serialize()
    except ValueError:
        holder = request.holder_ref
        gaps.append("holder_ref_invalid")
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    branch = run_git(repo, "symbolic-ref", "--short", "HEAD", check=False).stdout.strip()
    checks = (
        (actor == holder, "lease_actor_mismatch"),
        (branch == request.branch, "lease_branch_mismatch"),
        (head == request.expect_head, "expect_head_mismatch"),
    )
    gaps.extend(gap for valid, gap in checks if not valid)
    if row is None:
        gaps.append(f"work_lane_missing_lease:{request.branch}")
        return holder, gaps
    checks = (
        (row.id == request.lease_id, "lease_id_stale"),
        (row.owner == holder, "lease_holder_mismatch"),
        (row.expires_at == request.expected_expires_at, "lease_expires_at_stale"),
        (row.payload_sha256 == request.expected_payload_sha256, "lease_payload_sha256_stale"),
        (str(payload.get("lane_ref") or row.subject) == request.branch, "lease_subject_mismatch"),
        (str(payload.get("holder_ref") or row.owner) == holder, "lease_holder_mismatch"),
        (_integer(payload.get("epoch")) == request.expected_epoch, "lease_epoch_stale"),
    )
    gaps.extend(gap for valid, gap in checks if not valid)
    legacy_head = str(payload.get("expected_head") or "")
    if not legacy_head:
        gaps.append("lease_legacy_expected_head_missing")
    elif legacy_head != head and not is_ancestor(repo, legacy_head, head):
        gaps.append("lease_head_not_descendant")
    return holder, gaps


def _replacement(
    request: LeaseRecoveryRequest,
    *,
    row: LeaseRow,
    payload: dict[str, Any],
    holder_ref: str,
    issued_at: datetime,
    binding: dict[str, str],
) -> LaneLease:
    now = datetime.now(UTC)
    return LaneLease(
        lane_incarnation_id=str(
            payload.get("lane_incarnation_id") or f"lane-incarnation:{uuid.uuid4()}"
        ),
        lease_id=row.id,
        lane_ref=request.branch,
        holder_ref=holder_ref,
        epoch=request.expected_epoch + 1,
        issued_at=issued_at,
        renewed_at=now,
        expires_at=now + timedelta(seconds=request.ttl_seconds),
        expected_head=binding["expected_head"],
        expected_tree=binding["expected_tree"],
        base_commitment_path=binding["base_commitment_path"],
        base_commitment_bytes_sha256=binding["base_commitment_bytes_sha256"],
        base_commitment_digest=binding["base_commitment_digest"],
        path_scope=tuple(
            str(item) for item in payload.get("path_scope", ()) if isinstance(item, str)
        ),
        handoff=None,
    )


def _raw_row(database: Path, branch: str):
    if not database.exists():
        return None
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("begin")
        initialize_state_connection(connection)
        row = connection.execute(
            "select id, subject, owner, expires_at, payload_json from leases where subject = ?",
            (branch,),
        ).fetchone()
    return lease_row(row) if row is not None else None


def _legacy_payload(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _report(
    branch: str,
    verdict: str,
    state: str,
    gaps: list[str],
    row,
    payload: dict[str, Any],
    replacement: LaneLease | None = None,
) -> dict[str, object]:
    observation = {
        "branch": branch,
        "lease_id": row.id if row is not None else "",
        "holder_ref": row.owner if row is not None else "",
        "expires_at": row.expires_at if row is not None else "",
        "payload_sha256": row.payload_sha256 if row is not None else "",
        "legacy_expected_head": str(payload.get("expected_head") or ""),
    }
    return {
        "verdict": verdict,
        "state": state,
        "branch": branch,
        "observation": observation,
        "replacement": replacement.to_payload() if replacement is not None else {},
        "required_gaps": list(dict.fromkeys(gaps)),
    }
