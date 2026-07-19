from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.mutation.proof import proof_state_dir
from ethos.adapters.store.state.schema import initialize_state
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

OBSERVED_AT = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)


def maintenance_repo(tmp_path: Path) -> Path:
    return init_git_repo(tmp_path / "repo")


def insert_lease(
    repo: Path,
    *,
    lease_id: str,
    subject: str,
    expires_at: str,
    payload: dict[str, object] | str,
) -> None:
    db_path = repo / ".ethos" / "state" / "state.sqlite"
    initialize_state(db_path)
    if isinstance(payload, dict):
        payload = dict(payload)
        if payload.get("lease_id") == "lease:fixture":
            payload["lease_id"] = lease_id
        if payload.get("lane_ref") == "work/fixture":
            payload["lane_ref"] = subject
    payload_json = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            insert into leases(id, subject, owner, expires_at, payload_json)
            values (?, ?, 'agent:test:case:owner', ?, ?)
            """,
            (lease_id, subject, expires_at, payload_json),
        )
        connection.commit()


def current_lease_payload(*, path: str = "", expected_head: str = "") -> dict[str, object]:
    return {
        "lease_id": "lease:fixture",
        "lane_incarnation_id": "lane-incarnation:fixture",
        "lane_ref": "work/fixture",
        "holder_ref": "agent:test:case:owner",
        "epoch": 1,
        "issued_at": "2026-07-01T00:00:00+00:00",
        "renewed_at": "2026-07-01T00:00:00+00:00",
        "expected_head": expected_head,
        "claim_id": "",
        "path_scope": [],
        "coordination_scope": "git_common_directory",
        "mints_authority": False,
        "filesystem_fence": False,
        "distributed_lock": False,
        "path": path,
    }


def write_proof(repo: Path, head: str) -> Path:
    path = proof_state_dir(repo) / f"{head}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 3, "head": head, "state": "proven"}))
    return path


def unreachable_commit(repo: Path) -> str:
    tree = git(repo, "write-tree")
    return git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit-tree",
        tree,
        "-m",
        "unreachable maintenance proof",
    )
