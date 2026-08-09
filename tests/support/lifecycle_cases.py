"""Shared state constructors for lifecycle contract matrices."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.contracts.coordination import LaneLease
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate


@dataclass(frozen=True, slots=True)
class LaneStartCase:
    """One accepted/candidate/source/target topology for lane-start matrices."""

    repo: Path
    candidate: Path
    source: Path
    target: Path

    @classmethod
    def create(cls, tmp_path: Path, *, holder: str) -> LaneStartCase:
        repo, candidate = init_repo_with_candidate(tmp_path)
        source = create_change_source_lane(
            repo,
            tmp_path / "repo-work-source",
            holder_ref=holder,
        )
        return cls(repo, candidate, source, tmp_path / "repo-work-feature")

    def start(self, *, holder: str, **updates: object) -> dict[str, object]:
        arguments = {
            "root": self.repo,
            "name": "feature",
            "source_root": self.source,
            "path": self.target,
            "holder_ref": holder,
            "apply": True,
            **updates,
        }
        return start_work_lane(**arguments)

    def assert_absent(self) -> None:
        assert "work/feature" not in leases_by_branch(self.repo)
        assert ref_head(self.repo, "work/feature") == ""
        assert not self.target.exists()

    def assert_retained(self, *, head: str) -> None:
        assert "work/feature" in leases_by_branch(self.repo)
        assert ref_head(self.repo, "work/feature") == head

    def commit_source_drift(self, *, commitment: bool = False) -> None:
        if commitment:
            carrier = self.source / "openspec/changes/fixture-change/commitment.toml"
            carrier.write_text(carrier.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            relative = carrier.relative_to(self.source).as_posix()
        else:
            source_file = self.source / "SOURCE.md"
            source_file.write_text("drift\n", encoding="utf-8")
            relative = source_file.name
        git(self.source, "add", relative)
        git(
            self.source,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "drift source without advancing lease",
        )


def assert_public_decision(
    report: dict[str, object],
    *,
    verdict: str,
    state: str | None = None,
    gaps: list[str] | None = None,
) -> None:
    """Assert the stable public decision envelope without duplicating projections."""
    assert report["verdict"] == verdict
    assert "ok" not in report
    mutation = report.get("mutation")
    if isinstance(mutation, dict):
        decision = mutation.get("decision")
        if isinstance(decision, dict):
            assert decision["verdict"] == verdict
    if state is not None:
        assert report["state"] == state
    if gaps is not None:
        assert report["required_gaps"] == gaps


def rebind_effect(case: object) -> GitEffect:
    request = case.request
    return GitEffect(
        updates={
            f"refs/heads/{request.branch}": GitRefUpdate(
                expected=request.expect_head,
                desired=request.target_commit,
            )
        }
    )


def rebind_attestation_path(worktree: Path, effect: GitEffect) -> Path:
    return (
        Path(git_common_dir(worktree))
        / "ethos"
        / "attestations"
        / "commitment-rebind"
        / f"{effect.digest()}.json"
    )


def tamper_attestation(
    original: dict[str, object],
    *,
    location: str,
    field: str,
    replacement: str,
) -> Attestation:
    payload = deepcopy(original)
    if location == "attestation":
        payload[field] = replacement
    else:
        statement = payload["statement"]
        assert isinstance(statement, dict)
        target = statement if location == "statement" else statement[location]
        assert isinstance(target, dict)
        target[field] = replacement
    payload.update(statement_digest="0" * 64, id="0" * 64)
    payload["issued_at"] = datetime.fromisoformat(str(payload["issued_at"]))
    payload["valid_from"] = datetime.fromisoformat(str(payload["valid_from"]))
    payload["advisories"] = tuple(payload["advisories"])
    payload["evidence_refs"] = tuple(payload["evidence_refs"])
    return Attestation.issue(
        {
            name: value
            for name, value in payload.items()
            if name not in {"schema_version", "id", "statement_digest"}
        }
    )


def strict_lease(
    *,
    branch: str = "work/example",
    holder: str = "agent:test:case:holder",
    **updates: object,
) -> LaneLease:
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "lane_incarnation_id": "lane-incarnation:example",
        "lease_id": "lease:example",
        "lane_ref": branch,
        "holder_ref": holder,
        "epoch": 1,
        "issued_at": now,
        "renewed_at": now,
        "expires_at": now + timedelta(days=1),
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
        "path_scope": (),
    }
    values.update(updates)
    return LaneLease.model_validate(values)


def insert_lease_row(
    database: Path,
    lease: LaneLease,
    *,
    payload: dict[str, object] | None = None,
    row_expires_at: str | None = None,
) -> None:
    raw_payload = json.dumps(payload or lease.to_payload(), sort_keys=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) "
            "values (?, ?, ?, ?, ?)",
            (
                lease.lease_id,
                lease.lane_ref,
                lease.holder_ref.serialize(),
                row_expires_at or lease.expires_at.isoformat(),
                raw_payload,
            ),
        )
