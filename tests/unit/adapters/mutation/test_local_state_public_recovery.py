from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.mutation.local_state as local_state
import ethos.adapters.store.state.schema as state_schema
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    import pytest


def _database(path: Path, *, valid: bool = True, lease: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        if valid:
            connection.execute("begin immediate")
            state_schema.initialize_state_connection(connection)
            if lease:
                connection.execute(
                    "insert into leases(id,subject,owner,expires_at,payload_json) "
                    "values(?,?,?,?,?)",
                    ("lease:test", "work/test", "agent:test", "2030-01-01T00:00:00Z", "{}"),
                )
        else:
            connection.execute("create table foreign_state(id integer primary key)")
        connection.commit()


def _plan(repo: Path) -> dict[str, object]:
    report = local_state.local_state_migration(repo, apply=False)
    assert report["verdict"] == "pass"
    assert report["state"] == "ready"
    return report


def _apply(repo: Path, plan: dict[str, object]) -> dict[str, object]:
    return local_state.local_state_migration(
        repo,
        apply=True,
        expect_plan_digest=str(plan["plan_digest"]),
    )


def test_local_state_invalid_legacy_schema_fails_closed_without_rows(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = repo / ".ethos/state/state.sqlite"
    _database(legacy, valid=False)

    report = local_state.local_state_migration(repo, apply=False)

    assert report["verdict"] == "pass"
    assert report["state"] == "ready"
    assert report["manifest"] == []


def test_local_state_occupied_staging_blocks_before_effect(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    legacy = repo / ".ethos/state/state.sqlite"
    _database(legacy)
    plan = _plan(repo)
    target = Path(str(plan["target"]))
    occupied = target.with_name(f".{target.name}.migrate-{str(plan['plan_digest'])[:12]}")
    occupied.mkdir(parents=True)

    report = _apply(repo, plan)

    assert report["required_gaps"] == ["local_state_migration_staging_occupied"]
    assert legacy.exists()


def test_local_state_failed_verification_restores_existing_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source = repo / ".ethos/state/state.sqlite"
    target = state_schema.state_database(repo)
    _database(source, lease=True)
    _database(target)
    marker = target.parent / "target-marker"
    marker.write_text("preserve\n", encoding="utf-8")
    observed = iter((True, True, True, True, False))
    monkeypatch.setattr(
        local_state,
        "validate_current_lease_schema",
        lambda _connection: next(observed),
    )
    plan = _plan(repo)

    report = _apply(repo, plan)

    assert report["required_gaps"] == ["local_state_migration_verification_failed"]
    assert marker.read_text(encoding="utf-8") == "preserve\n"
    assert source.exists()


def test_local_state_verification_detects_source_remaining(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source = repo / ".ethos/state/state.sqlite"
    _database(source)
    plan = _plan(repo)
    original = Path.rename

    def retain_source(path: Path, target: Path) -> Path:
        if path == source:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            return target
        return original(path, target)

    monkeypatch.setattr(Path, "rename", retain_source)
    report = _apply(repo, plan)

    assert report["required_gaps"] == ["local_state_migration_verification_failed"]
    assert source.exists()
    assert not state_schema.state_database(repo).exists()


def test_local_state_public_materialization_preserves_duplicate_and_initializes_database(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source_root = repo / ".ethos/state"
    plan = local_state.local_state_migration(repo, apply=False)
    target_root = Path(str(plan["target"]))
    source_file = source_root / "same.txt"
    target_file = target_root / "same.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("same\n", encoding="utf-8")
    target_file.write_text("same\n", encoding="utf-8")
    plan = _plan(repo)

    report = _apply(repo, plan)

    assert report["state"] == "migrated"
    assert target_file.read_text(encoding="utf-8") == "same\n"
    assert state_schema.state_database(repo).is_file()
    assert not source_file.exists()
