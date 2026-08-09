from __future__ import annotations

import sqlite3
from shutil import rmtree
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.local_state as local_state
import ethos.adapters.store.state.schema as state_schema
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _legacy(root: Path) -> Path:
    return root / ".ethos/state"


def _database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("begin immediate")
        state_schema.initialize_state_connection(connection)
        connection.commit()


def test_local_state_rejects_symlink_source_without_following_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init_git_repo(tmp_path / "repo")
    external = tmp_path / "external"
    external.mkdir()
    (external / "sentinel").write_text("preserve\n", encoding="utf-8")
    legacy = _legacy(root)
    rmtree(legacy)
    legacy.symlink_to(external, target_is_directory=True)
    monkeypatch.setattr(local_state, "_legacy_state_root", lambda _root: legacy)

    report = local_state.local_state_migration(root, apply=False)

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["local_state_source_invalid"]
    assert (external / "sentinel").read_text(encoding="utf-8") == "preserve\n"


def test_local_state_reports_invalid_database_as_structured_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init_git_repo(tmp_path / "repo")
    legacy = _legacy(root)
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "state.sqlite").write_bytes(b"not sqlite")
    monkeypatch.setattr(local_state, "_legacy_state_root", lambda _root: legacy)

    report = local_state.local_state_migration(root, apply=False)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["local_state_database_invalid"]


@pytest.mark.parametrize(
    ("failure", "gap"),
    [
        (
            ValueError("local_state_migration_staging_occupied"),
            "local_state_migration_staging_occupied",
        ),
        (OSError("disk unavailable"), "local_state_migration_io_failed"),
    ],
)
def test_local_state_apply_converts_effect_failures_to_public_gaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    gap: str,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    legacy = _legacy(root)
    _database(legacy / "state.sqlite")
    monkeypatch.setattr(local_state, "_legacy_state_root", lambda _root: legacy)
    plan = local_state.local_state_migration(root, apply=False)
    migration_type = type(local_state.local_state_migration.__globals__["_Migration"].plan(root))
    monkeypatch.setattr(migration_type, "apply", lambda _self: (_ for _ in ()).throw(failure))

    report = local_state.local_state_migration(
        root,
        apply=True,
        expect_plan_digest=str(plan["plan_digest"]),
    )

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [gap]
    assert (legacy / "state.sqlite").exists()


def test_local_state_guard_names_exact_root_head_and_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init_git_repo(tmp_path / "repo")
    legacy = _legacy(root)
    _database(legacy / "state.sqlite")
    monkeypatch.setattr(local_state, "_legacy_state_root", lambda _root: legacy)

    report = local_state.local_state_mutation_guard(root)

    assert report["required_gaps"] == ["local_state_migration_required"]
    assert report["plan_digest"]
    assert report["next_action"] == (
        f"ethos migrate-local-state --root {root.resolve()} --apply --authorize "
        f"--expect-head {git(root, 'rev-parse', 'HEAD')} "
        f"--expect-plan-digest {report['plan_digest']} --json"
    )


def test_local_state_guard_is_current_when_common_database_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init_git_repo(tmp_path / "repo")
    legacy = _legacy(root)
    _database(legacy / "state.sqlite")
    _database(state_schema.state_database(root))
    monkeypatch.setattr(local_state, "_legacy_state_root", lambda _root: legacy)

    assert local_state.local_state_mutation_guard(root) == {
        "required_gaps": [],
        "plan_digest": "",
        "next_action": "",
    }
