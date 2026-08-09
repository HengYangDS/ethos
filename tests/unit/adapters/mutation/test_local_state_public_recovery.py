from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.local_state as local_state
import ethos.adapters.store.state.schema as state_schema
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _database(path: Path, *, valid: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        if valid:
            connection.execute("begin immediate")
            state_schema.initialize_state_connection(connection)
        else:
            connection.execute("create table foreign_state(id integer primary key)")
        connection.commit()


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
    plan = local_state._Migration.plan(repo)  # noqa: SLF001
    occupied = plan.target.with_name(f".{plan.target.name}.migrate-{plan.digest[:12]}")
    occupied.mkdir(parents=True)

    report = local_state.local_state_migration(
        repo,
        apply=True,
        expect_plan_digest=plan.digest,
    )

    assert report["required_gaps"] == ["local_state_migration_staging_occupied"]
    assert legacy.exists()


def test_local_state_failed_verification_restores_existing_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source = repo / ".ethos/state/state.sqlite"
    target = state_schema.state_database(repo)
    _database(source)
    _database(target)
    marker = target.parent / "target-marker"
    marker.write_text("preserve\n", encoding="utf-8")
    plan = local_state._Migration.plan(repo)  # noqa: SLF001
    monkeypatch.setattr(
        local_state,
        "_verify_migration",
        lambda _migration: (_ for _ in ()).throw(ValueError("verification_failed")),
    )

    report = local_state.local_state_migration(
        repo,
        apply=True,
        expect_plan_digest=plan.digest,
    )

    assert report["required_gaps"] == ["verification_failed"]
    assert marker.read_text(encoding="utf-8") == "preserve\n"
    assert source.exists()


def test_local_state_verification_detects_source_remaining(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source = repo / ".ethos/state/state.sqlite"
    _database(source)
    migration = local_state._Migration.plan(repo)  # noqa: SLF001

    with pytest.raises(ValueError, match="local_state_migration_verification_failed"):
        migration.verify()


def test_local_state_materialize_skips_duplicate_and_empty_database(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    source_root = repo / ".ethos/state"
    target_root = state_schema.local_state_root(repo)
    source_file = source_root / "same.txt"
    target_file = target_root / "same.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("source\n", encoding="utf-8")
    target_file.write_text("target\n", encoding="utf-8")
    migration = local_state._Migration(  # noqa: SLF001
        repo=repo,
        source=source_root,
        target=target_root,
        source_manifest=(("same.txt", "source"),),
        target_manifest=(("same.txt", "target"),),
        source_database_digest="",
        target_database_digest="",
        leases=(),
        gaps=(),
    )
    staging = tmp_path / "staging"

    migration.materialize(staging)

    assert (staging / "same.txt").read_text(encoding="utf-8") == "target\n"
    assert (staging / "state.sqlite").is_file()
