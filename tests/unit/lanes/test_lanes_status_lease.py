from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.read import active_leases
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_workspace_status_rejects_control_root_legacy_json_owner_projection(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {
                        "branch": "work/feature",
                        "owner": "agent:test",
                        "expires_at": "2999-01-01T00:00:00Z",
                        "worktree_path": worktree.as_posix(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "",
        "lease_id": "",
        "lease_epoch": 0,
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/feature"],
    }
    assert "work_lane_missing_lease:work/feature" in status["required_gaps"]


def test_workspace_status_prefers_sqlite_lease_over_json_projection(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-sqlite",
        apply=True,
    )
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {
                        "branch": "work/feature",
                        "owner": "agent:json",
                        "expires_at": "2999-01-01T00:00:00Z",
                        "worktree_path": worktree.as_posix(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": True,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "agent:test:case:agent-sqlite",
        "lease_id": status["closeout_support"]["lease_id"],
        "lease_epoch": 1,
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": [],
    }


def test_workspace_status_ignores_expired_json_lease_projection(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {
                        "branch": "work/feature",
                        "owner": "agent:expired",
                        "expires_at": "2000-01-01T00:00:00Z",
                        "worktree_path": worktree.as_posix(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "",
        "lease_id": "",
        "lease_epoch": 0,
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/feature"],
    }


def test_workspace_status_ignores_malformed_json_lease_projection(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text("[", encoding="utf-8")

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "",
        "lease_id": "",
        "lease_epoch": 0,
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/feature"],
    }


def test_workspace_status_ignores_invalid_json_lease_rows(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps({"schema_version": 1, "leases": "not-a-list"}),
        encoding="utf-8",
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "",
        "lease_id": "",
        "lease_epoch": 0,
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/feature"],
    }

    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    "not-a-dict",
                    {
                        "branch": "work/feature",
                        "owner": "agent:bad-date",
                        "expires_at": "not-a-date",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "",
        "lease_id": "",
        "lease_epoch": 0,
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/feature"],
    }


def test_workspace_status_rejects_naive_legacy_json_owner_projection(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"
    git(repo, "worktree", "add", "-b", "work/feature", worktree.as_posix(), "dev")
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {
                        "branch": "work/feature",
                        "owner": "agent:naive",
                        "expires_at": "2999-01-01T00:00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/feature",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "",
        "lease_id": "",
        "lease_epoch": 0,
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/feature"],
    }


def test_workspace_status_blocks_raw_work_lane_without_lease(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-raw"
    git(repo, "worktree", "add", "-b", "work/raw", worktree.as_posix(), "dev")

    status = workspace_status(worktree)

    assert status["closeout_support"] == {
        "supported": False,
        "branch": "work/raw",
        "target_branch": "candidate/dev",
        "target_path": candidate.as_posix(),
        "operation": "land_to_candidate",
        "holder_ref": "",
        "lease_id": "",
        "lease_epoch": 0,
        "claim_id": "",
        "claim_binding": "missing",
        "required_gaps": ["work_lane_missing_lease:work/raw"],
    }
    assert status["required_gaps"] == ["work_lane_missing_lease:work/raw"]


def test_workspace_status_reports_closeout_holder_from_lane_lease(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-feature"

    report = start_work_lane(
        root=repo,
        name="feature",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    status = workspace_status(worktree)

    assert report["ok"] is True
    assert status["closeout_support"]["holder_ref"] == "agent:test:case:agent-test"
    assert status["closeout_support"]["lease_id"].startswith("lease:")
    assert status["closeout_support"]["lease_epoch"] == 1


def test_workspace_status_ignores_retired_state_lease_schema(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    state_db = repo / ".ethos" / "state" / "state.sqlite"
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    with closing(sqlite3.connect(state_db)) as connection:
        connection.execute(
            """
            create table leases (
              id text primary key,
              owner text not null default '',
              resource text not null default '',
              expires_at text not null default '',
              created_at text not null
            )
            """
        )
        connection.execute(
            """
            insert into leases(id, owner, resource, expires_at, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (
                "lease:retired",
                "agent:retired",
                "work/retired",
                expires_at.isoformat(),
                datetime.now(UTC).isoformat(),
            ),
        )

    status = workspace_status(repo)
    leases = active_leases(state_db)

    assert status["role"] == "accepted_root"
    assert leases == []
