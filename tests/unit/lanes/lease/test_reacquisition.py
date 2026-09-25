"""Missing coordination can be reacquired without altering retained work."""

from __future__ import annotations

import shlex
import sqlite3
from contextlib import closing
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

import ethos.adapters.mutation.lane_lifecycle.lease.acquisition as lease_acquisition
import ethos.adapters.store.state.lease.lifecycle.transitions as lease_storage
import ethos.adapters.store.state.lease.projection as lease_projection
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.governed_repository import render_branch_policy
from tests.support.lifecycle_cases import strict_lease

SOURCE = "agent:test:case:source"
TARGET = "agent:test:case:target"


def _unleased_dirty_lane(tmp_path):
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "retained-work"
    git(repo, "worktree", "add", "-b", "work/retained", str(target), "dev")
    (target / "README.md").write_text("staged\n")
    git(target, "add", "README.md")
    (target / "README.md").write_text("unstaged\n")
    (target / "untracked.txt").write_bytes(b"retained\x00bytes")
    return repo, target


def _reacquire(root, target, **options):
    return lease_acquisition.reacquire_lease(root=root, path=target, holder_ref=TARGET, **options)


def _reacquire_arguments(planned):
    return {
        "expect_head": planned["head"],
        "expect_snapshot": planned["snapshot"],
        "expires_at": planned["expires_at"],
        "authorize": True,
        "apply": True,
    }


@pytest.mark.parametrize("stale_policy", [False, True])
def test_reacquire_missing_lease_preserves_index_and_dirty_content(
    tmp_path, monkeypatch, stale_policy
):
    repo, target = _unleased_dirty_lane(tmp_path)
    if stale_policy:
        (target / ".ethos/workspace.toml").write_text('[branch_roles]\naccepted_branch="lost"\n')
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    before = (git(target, "rev-parse", "HEAD"), git(target, "diff", "--cached"))

    planned = run_ethos(
        "lane",
        "lease",
        "reacquire",
        "--path",
        str(target),
        "--holder-ref",
        TARGET,
        "--root",
        str(target),
        "--json",
        cwd=repo,
    )
    assert planned["verdict"] == "pass"
    assert lease_projection.observe_lease(state_database(repo), "work/retained").state == "missing"
    arguments = shlex.split(planned["next_action"])
    assert arguments[:4] == ["ethos", "lane", "lease", "reacquire"]
    assert "--expect-snapshot" in arguments
    applied = run_ethos(*arguments[1:], cwd=repo)["data"]
    repeated = run_ethos(*arguments[1:], cwd=repo)["data"]
    assert applied["verdict"] == repeated["verdict"] == "pass"
    assert applied["state"] == "acquired"
    assert repeated["state"] == "recognized"
    assert applied["lease"] == repeated["lease"]
    assert applied["attestation"] == repeated["attestation"]
    assert applied["lease"]["holder_ref"] == TARGET
    assert applied["lease"]["generation"] == 1
    assert applied["attestation"]["commitment_digest"] is None
    assert (git(target, "rev-parse", "HEAD"), git(target, "diff", "--cached")) == before
    assert git(target, "show", ":README.md") == "staged"
    assert (target / "README.md").read_text() == "unstaged\n"
    assert (target / "untracked.txt").read_bytes() == b"retained\x00bytes"


def test_reacquire_recognizes_previous_complete_accepted_policy(tmp_path, monkeypatch):
    repo, target = _unleased_dirty_lane(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir(parents=True, exist_ok=True)
    workspace.write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="independent",
        ).replace("canonical_sibling_worktrees = false\n", "")
    )
    git(repo, "add", workspace.as_posix())
    git(repo, "commit", "-m", "retain previous complete policy")
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    before = (
        git(target, "rev-parse", "HEAD"),
        git(target, "diff", "--cached"),
        (target / "README.md").read_bytes(),
        (target / "untracked.txt").read_bytes(),
    )

    planned = _reacquire(repo, target)
    applied = _reacquire(repo, target, **_reacquire_arguments(planned))

    assert planned["verdict"] == "pass", planned
    assert planned["state"] == "planned"
    assert applied["verdict"] == "pass", applied
    assert applied["state"] == "acquired"
    assert before == (
        git(target, "rev-parse", "HEAD"),
        git(target, "diff", "--cached"),
        (target / "README.md").read_bytes(),
        (target / "untracked.txt").read_bytes(),
    )


@pytest.mark.parametrize(
    "drift",
    [
        "head",
        "index",
        "working",
        "untracked",
        "lease",
        "same-holder",
        "renewed",
        "lock",
        "actor",
        "expired",
        "protected",
        "foreign",
    ],
)
def test_reacquire_rejects_exact_snapshot_or_ownership_drift(tmp_path, monkeypatch, drift):
    repo, target = _unleased_dirty_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    arguments = _reacquire_arguments(_reacquire(repo, target))
    if drift == "head":
        git(target, "commit", "-m", "advance retained source")
    elif drift == "index":
        git(target, "reset", "HEAD", "README.md")
    elif drift in {"working", "untracked"}:
        (target / ("README.md" if drift == "working" else "untracked.txt")).write_text("changed\n")
    elif drift in {"lease", "expired", "same-holder", "renewed"}:
        lease_storage.acquire_lease(
            state_database(repo),
            lease=strict_lease(
                branch="work/retained",
                holder=TARGET if drift in {"same-holder", "renewed"} else SOURCE,
                generation=2 if drift == "renewed" else 1,
                expires_at=(
                    datetime.fromisoformat(arguments["expires_at"])
                    if drift == "renewed"
                    else datetime.now(UTC) + timedelta(days=-1 if drift == "expired" else 1)
                ),
            ),
        )
    elif drift == "lock":
        git(repo, "worktree", "lock", str(target))
    elif drift == "actor":
        monkeypatch.setenv("ETHOS_ACTOR", SOURCE)
    elif drift == "protected":
        target = repo
    else:
        target, _candidate = init_repo_with_candidate(tmp_path / "foreign")
    result = _reacquire(repo, target, **arguments)
    assert result["verdict"] == "block", result
    observed = lease_projection.observe_lease(state_database(repo), "work/retained")
    assert observed.state == {
        "lease": "valid",
        "same-holder": "valid",
        "renewed": "valid",
        "expired": "expired",
    }.get(drift, "missing")
    if drift in {"lease", "expired"}:
        assert observed.record()["holder_ref"] == SOURCE


def test_reacquire_rejects_invalid_request_and_unreadable_state(tmp_path, monkeypatch):
    repo, target = _unleased_dirty_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    arguments = _reacquire_arguments(_reacquire(repo, target))
    for invalid in (
        {"authorize": False},
        {"expires_at": ""},
        {"expires_at": "2020-01-01T00:00:00Z"},
    ):
        assert _reacquire(repo, target, **(arguments | invalid))["verdict"] == "block"
        assert (
            lease_projection.observe_lease(state_database(repo), "work/retained").state == "missing"
        )
    state_database(repo).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(state_database(repo))) as connection, connection:
        connection.execute("create table leases (old_id text)")
    result = _reacquire(repo, target, **arguments)
    assert result["verdict"] == "unknown"
    assert result["required_gaps"] == ["state_schema_lease_table_definition_mismatch"]


def test_reacquire_rolls_back_lease_when_content_changes_during_insertion(tmp_path, monkeypatch):
    repo, target = _unleased_dirty_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    planned = _reacquire(repo, target)
    insert = lease_storage.acquire_lease_from_connection

    def drift(connection, *, lease):
        result = insert(connection, lease=lease)
        (target / "README.md").write_text("concurrent edit\n")
        return result

    monkeypatch.setattr(lease_storage, "acquire_lease_from_connection", drift)
    result = _reacquire(repo, target, **_reacquire_arguments(planned))

    assert result["verdict"] == "block"
    assert "lease_reacquire_snapshot_drift" in result["required_gaps"]
    assert lease_projection.observe_lease(state_database(repo), "work/retained").state == "missing"
    assert (target / "README.md").read_text() == "concurrent edit\n"


def test_reacquire_recovers_evidence_failure_without_replacing_committed_lease(
    tmp_path, monkeypatch
):
    repo, target = _unleased_dirty_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", TARGET)
    planned = _reacquire(repo, target)
    record = lease_acquisition.record_attestations

    def unavailable(*_args):
        message = "evidence unavailable"
        raise ValueError(message)

    monkeypatch.setattr(lease_acquisition, "record_attestations", unavailable)
    partial = _reacquire(repo, target, **_reacquire_arguments(planned))
    assert partial["state"] == "partial_transition"
    lease = lease_projection.observe_lease(state_database(repo), "work/retained").record()
    assert lease["holder_ref"] == TARGET
    monkeypatch.setattr(lease_acquisition, "record_attestations", record)
    recovered = _reacquire(repo, target, **_reacquire_arguments(planned))
    assert recovered["verdict"] == "pass"
    assert recovered["lease"] == lease
