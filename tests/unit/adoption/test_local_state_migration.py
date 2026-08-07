from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import ethos.adapters.mutation.local_state as local_state_module
from ethos.adapters.mutation.local_state import local_state_migration
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_LEASE_INSERT = (
    "insert into leases(id, subject, owner, expires_at, payload_json) values (?, ?, ?, ?, ?)"
)


def _initialize_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.commit()


def _insert_lease(path: Path, *, lease_id: str, subject: str, owner: str = "agent:test") -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(_LEASE_INSERT, (lease_id, subject, owner, "2030-01-01T00:00:00Z", "{}"))


def test_local_state_migration_moves_checkout_state_into_git_common_dir(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = repo / ".ethos" / "state"
    database = legacy / "state.sqlite"
    _initialize_database(database)
    artifact = legacy / "attestations" / "artifacts" / "artifact.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"artifact": true}\n', encoding="utf-8")
    attestation = legacy / "attestations" / "proof.json"
    attestation.write_text('{"proof": true}\n', encoding="utf-8")

    plan = local_state_migration(repo, apply=False)

    assert plan["verdict"] == "pass"
    assert plan["state"] == "ready"
    assert plan["source"] == legacy.as_posix()
    assert plan["target"] == state_database(repo).parent.as_posix()
    assert database.exists()
    assert not state_database(repo).exists()

    result = local_state_migration(
        repo,
        apply=True,
        expect_plan_digest=str(plan["plan_digest"]),
    )

    assert result["verdict"] == "pass"
    assert result["state"] == "migrated"
    assert sorted(
        path.relative_to(legacy).as_posix() for path in legacy.rglob("*") if path.is_file()
    ) == [".gitignore"]
    assert state_database(repo).exists()
    assert (state_database(repo).parent / "attestations" / "proof.json").read_text(
        encoding="utf-8"
    ) == '{"proof": true}\n'
    assert (state_database(repo).parent / "attestations" / "artifacts" / "artifact.json").read_text(
        encoding="utf-8"
    ) == '{"artifact": true}\n'
    with sqlite3.connect(state_database(repo)) as connection:
        assert connection.execute("select count(*) from leases").fetchone() == (0,)


def test_local_state_migration_fails_closed_on_target_or_plan_drift(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = repo / ".ethos" / "state"
    _initialize_database(legacy / "state.sqlite")
    target = state_database(repo).parent
    target.mkdir(parents=True)
    (target / "foreign").write_text("occupied\n", encoding="utf-8")
    plan = local_state_migration(repo, apply=False)

    occupied = local_state_migration(
        repo,
        apply=True,
        expect_plan_digest=str(plan["plan_digest"]),
    )

    assert occupied["verdict"] == "pass"
    assert occupied["state"] == "migrated"
    assert not (legacy / "state.sqlite").exists()
    assert (target / "foreign").read_text(encoding="utf-8") == "occupied\n"

    _initialize_database(legacy / "state.sqlite")
    stale = local_state_migration(
        repo,
        apply=True,
        expect_plan_digest="0" * 64,
    )
    assert stale["verdict"] == "block"
    assert stale["required_gaps"] == ["local_state_migration_plan_digest_mismatch"]
    assert (legacy / "state.sqlite").exists()


def test_local_state_migration_uses_the_accepted_root_from_a_linked_worktree(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    lane = create_change_source_lane(
        repo,
        tmp_path / "repo-work-source",
        branch="work/source",
        holder_ref="agent:test:case:source",
    )
    legacy = repo / ".ethos" / "state"
    current = state_database(repo)
    current.replace(legacy / "state.sqlite")

    result = local_state_migration(lane, apply=False)

    assert result["verdict"] == "pass"
    assert result["state"] == "ready"
    assert result["source"] == legacy.as_posix()


def test_local_state_migration_merges_existing_target_files_and_disjoint_leases(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = repo / ".ethos" / "state"
    source_database = legacy / "state.sqlite"
    target_database = state_database(repo)
    _initialize_database(source_database)
    _insert_lease(source_database, lease_id="lease:source", subject="work/source")
    source_proof = legacy / "attestations" / "proof.json"
    source_proof.parent.mkdir(parents=True)
    source_proof.write_text('{"proof": true}\n', encoding="utf-8")
    _initialize_database(target_database)
    _insert_lease(target_database, lease_id="lease:target", subject="work/target")
    target_effect = target_database.parent / "git-effects" / "effect.json"
    target_effect.parent.mkdir(parents=True)
    target_effect.write_text('{"effect": true}\n', encoding="utf-8")

    plan = local_state_migration(repo, apply=False)
    result = local_state_migration(
        repo,
        apply=True,
        expect_plan_digest=str(plan["plan_digest"]),
    )

    assert result["verdict"] == "pass"
    assert result["state"] == "migrated"
    assert target_effect.read_text(encoding="utf-8") == '{"effect": true}\n'
    assert (target_database.parent / "attestations" / "proof.json").read_text(
        encoding="utf-8"
    ) == '{"proof": true}\n'
    with sqlite3.connect(target_database) as connection:
        assert connection.execute("select subject from leases order by subject").fetchall() == [
            ("work/source",),
            ("work/target",),
        ]


def test_local_state_migration_preserves_non_lease_source_tables(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source_database = repo / ".ethos" / "state" / "state.sqlite"
    _initialize_database(source_database)
    with sqlite3.connect(source_database) as connection:
        connection.execute("create table legacy_events (id integer primary key, payload text)")
        connection.execute("insert into legacy_events(payload) values ('preserve me')")
    target_database = state_database(repo)
    _initialize_database(target_database)
    _insert_lease(target_database, lease_id="lease:target", subject="work/target")
    plan = local_state_migration(repo, apply=False)

    result = local_state_migration(
        repo,
        apply=True,
        expect_plan_digest=str(plan["plan_digest"]),
    )

    assert result["verdict"] == "pass"
    with sqlite3.connect(target_database) as connection:
        assert connection.execute("select payload from legacy_events").fetchall() == [
            ("preserve me",)
        ]
        assert connection.execute("select subject from leases").fetchall() == [("work/target",)]


def test_local_state_migration_rejects_file_or_lease_conflicts(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = repo / ".ethos" / "state"
    source_database = legacy / "state.sqlite"
    target_database = state_database(repo)
    _initialize_database(source_database)
    _insert_lease(source_database, lease_id="lease:source", subject="work/conflict")
    _initialize_database(target_database)
    _insert_lease(
        target_database,
        lease_id="lease:target",
        subject="work/conflict",
        owner="agent:other",
    )

    lease_conflict = local_state_migration(repo, apply=False)

    assert lease_conflict["verdict"] == "block"
    assert lease_conflict["required_gaps"] == ["local_state_lease_conflict:work/conflict"]
    with sqlite3.connect(target_database) as connection:
        connection.execute("delete from leases")
    source_file = legacy / "attestations" / "same.json"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("source\n", encoding="utf-8")
    target_file = target_database.parent / "attestations" / "same.json"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("target\n", encoding="utf-8")

    file_conflict = local_state_migration(repo, apply=False)

    assert file_conflict["verdict"] == "block"
    assert file_conflict["required_gaps"] == ["local_state_file_conflict:attestations/same.json"]


def test_local_state_migration_compensates_partial_move(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = repo / ".ethos" / "state"
    _initialize_database(legacy / "state.sqlite")
    proof = legacy / "attestations" / "proof.json"
    proof.parent.mkdir(parents=True)
    proof.write_text('{"proof": true}\n', encoding="utf-8")
    plan = local_state_migration(repo, apply=False)

    monkeypatch.setattr(
        local_state_module,
        "_verify_migration",
        lambda *_args: (_ for _ in ()).throw(ValueError("local_state_migration_source_drift")),
    )

    result = local_state_migration(
        repo,
        apply=True,
        expect_plan_digest=str(plan["plan_digest"]),
    )

    assert result["verdict"] == "block"
    assert result["required_gaps"] == ["local_state_migration_source_drift"]
    assert (legacy / "state.sqlite").exists()
    assert proof.read_text(encoding="utf-8") == '{"proof": true}\n'
    assert not state_database(repo).parent.exists()
    assert not list(state_database(repo).parent.parent.glob(".ethos.migrate-*"))


def test_local_state_migration_is_idempotent_when_checkout_state_is_absent(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = repo / ".ethos" / "state"
    for path in sorted(legacy.rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    legacy.rmdir()

    result = local_state_migration(repo, apply=False)

    assert result["verdict"] == "pass"
    assert result["state"] == "current"
    assert result["required_gaps"] == []


def test_public_local_state_migration_requires_exact_head_and_plan_digest(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _initialize_database(repo / ".ethos" / "state" / "state.sqlite")
    head = git(repo, "rev-parse", "HEAD")

    plan = run_ethos("migrate-local-state", "--root", repo.as_posix(), "--json", cwd=repo)

    assert plan["verdict"] == "pass"
    assert plan["state"] == "ready"
    digest = plan["data"]["plan_digest"]
    missing_cas = run_ethos_blocked(
        "migrate-local-state",
        "--root",
        repo.as_posix(),
        "--apply",
        "--json",
        cwd=repo,
    )
    assert missing_cas["required_gaps"] == ["authorization_required", "expect_head_required"]

    applied = run_ethos(
        "migrate-local-state",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--expect-plan-digest",
        digest,
        "--json",
        cwd=repo,
    )

    assert applied["verdict"] == "pass"
    assert applied["state"] == "migrated"
    assert state_database(repo).exists()


def test_migration_restores_clean_accepted_root_and_lane_start(tmp_path: Path) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    (repo / ".gitignore").write_text("", encoding="utf-8")
    git(repo, "rm", ".ethos/state/.gitignore")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-m", "do not ignore misplaced state")
    git(candidate, "reset", "--hard", "dev")
    source = create_change_source_lane(
        repo,
        tmp_path / "repo-work-source-next",
        branch="work/source-next",
        holder_ref="agent:test:case:source",
    )
    current_state = state_database(repo).parent
    legacy = repo / ".ethos" / "state"
    for path in sorted(current_state.rglob("*")):
        if path.is_file():
            destination = legacy / path.relative_to(current_state)
            destination.parent.mkdir(parents=True, exist_ok=True)
            path.rename(destination)
    for path in sorted((item for item in current_state.rglob("*") if item.is_dir()), reverse=True):
        path.rmdir()
    current_state.rmdir()
    assert git(repo, "status", "--short")

    plan = run_ethos("migrate-local-state", "--root", repo.as_posix(), "--json", cwd=repo)
    migrated = run_ethos(
        "migrate-local-state",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        git(repo, "rev-parse", "HEAD"),
        "--expect-plan-digest",
        plan["data"]["plan_digest"],
        "--json",
        cwd=repo,
    )
    lane = tmp_path / "repo-work-next"
    started = run_ethos(
        "lane",
        "start",
        "next",
        "--root",
        repo.as_posix(),
        "--path",
        lane.as_posix(),
        "--source-root",
        source.as_posix(),
        "--holder-ref",
        "agent:test:case:next",
        "--apply",
        "--json",
        cwd=repo,
    )

    assert migrated["state"] == "migrated"
    assert git(repo, "status", "--short") == ""
    assert started["verdict"] == "pass"
    assert started["state"] == "started"
    assert lane.is_dir()
