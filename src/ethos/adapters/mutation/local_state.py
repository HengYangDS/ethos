"""One-way migration of misplaced checkout-local ETHOS runtime state."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.workspace import worktree_records
from ethos.adapters.store.state.schema import initialize_state_connection
from ethos.adapters.store.state.schema import local_state_root
from ethos.adapters.store.state.schema import read_only_state_uri
from ethos.adapters.store.state.schema import validate_current_lease_schema
from ethos.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path

_DATABASE_FILES = frozenset({"state.sqlite", "state.sqlite-shm", "state.sqlite-wal"})
_LEASE_SELECT = "select id, subject, owner, expires_at, payload_json from leases"
_LEASE_INSERT = (
    "insert into leases(id, subject, owner, expires_at, payload_json) values (?, ?, ?, ?, ?)"
)
LeaseRow = tuple[str, str, str, str, str]
Manifest = tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class _MigrationPlan:
    repo: Path
    source: Path
    target: Path
    source_manifest: Manifest
    target_manifest: Manifest
    source_database_digest: str
    target_database_digest: str
    leases: tuple[LeaseRow, ...]
    gaps: tuple[str, ...]

    @property
    def digest(self) -> str:
        lines = (
            self.source.resolve().as_posix(),
            self.target.resolve().as_posix(),
            *(f"source:{path}:{digest}" for path, digest in self.source_manifest),
            *(f"target:{path}:{digest}" for path, digest in self.target_manifest),
            f"source-database:{self.source_database_digest}",
            f"target-database:{self.target_database_digest}",
            *("lease:" + "\0".join(row) for row in self.leases),
            *(f"gap:{gap}" for gap in self.gaps),
        )
        return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _legacy_state_root(repo: Path) -> Path:
    policy = load_branch_role_policy(repo)
    worktrees = worktree_records(repo, current_path=repo, policy=policy)
    accepted = accepted_worktree_root(worktrees, repo).resolve()
    return accepted / ".ethos" / "state"


def _file_manifest(repo: Path, root: Path, *, legacy: bool) -> Manifest:
    tracked = set(git_files(repo, ".ethos/state")) if legacy else set()
    if not root.is_dir():
        return ()
    return tuple(
        (relative, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and (relative := path.relative_to(root).as_posix()) not in _DATABASE_FILES
        and (not legacy or f".ethos/state/{relative}" not in tracked)
    )


def _source_invalid(source: Path) -> bool:
    return source.is_symlink() or (
        source.exists()
        and (not source.is_dir() or any(path.is_symlink() for path in source.rglob("*")))
    )


def _database_rows(path: Path) -> tuple[LeaseRow, ...]:
    if not path.is_file() or path.stat().st_size == 0:
        return ()
    with closing(sqlite3.connect(read_only_state_uri(path), uri=True)) as connection:
        if not validate_current_lease_schema(connection):
            return ()
        return tuple(
            (str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]))
            for row in connection.execute(f"{_LEASE_SELECT} order by subject")
        )


def _database_digest(path: Path) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        return ""
    with closing(sqlite3.connect(read_only_state_uri(path), uri=True)) as connection:
        dump = "\n".join(connection.iterdump())
    return hashlib.sha256(dump.encode()).hexdigest()


def _merge_leases(
    source: tuple[LeaseRow, ...], target: tuple[LeaseRow, ...]
) -> tuple[tuple[LeaseRow, ...], tuple[str, ...]]:
    by_subject = {row[1]: row for row in target}
    by_id = {row[0]: row for row in target}
    gaps: list[str] = []
    for row in source:
        incumbent = by_subject.get(row[1]) or by_id.get(row[0])
        if incumbent is not None and incumbent != row:
            gaps.append(f"local_state_lease_conflict:{row[1]}")
            continue
        by_subject[row[1]] = row
        by_id[row[0]] = row
    return tuple(sorted(by_subject.values(), key=lambda row: row[1])), tuple(gaps)


def _file_conflicts(source: Manifest, target: Manifest) -> tuple[str, ...]:
    target_by_path = dict(target)
    return tuple(
        f"local_state_file_conflict:{path}"
        for path, digest in source
        if path in target_by_path and target_by_path[path] != digest
    )


def _migration_plan(root: Path) -> _MigrationPlan:
    repo = repository_root(root)
    source = _legacy_state_root(repo)
    target = local_state_root(repo)
    invalid_source = _source_invalid(source)
    source_manifest = () if invalid_source else _file_manifest(repo, source, legacy=True)
    target_manifest = _file_manifest(repo, target, legacy=False)
    gaps = ["local_state_source_invalid"] if invalid_source else []
    leases: tuple[LeaseRow, ...] = ()
    source_database_digest = ""
    target_database_digest = ""
    try:
        source_database_digest = _database_digest(source / "state.sqlite")
        target_database_digest = _database_digest(target / "state.sqlite")
        leases, lease_gaps = _merge_leases(
            _database_rows(source / "state.sqlite"),
            _database_rows(target / "state.sqlite"),
        )
    except (RuntimeError, sqlite3.Error):
        gaps.append("local_state_database_invalid")
    else:
        gaps.extend(lease_gaps)
    gaps.extend(_file_conflicts(source_manifest, target_manifest))
    return _MigrationPlan(
        repo=repo,
        source=source,
        target=target,
        source_manifest=source_manifest,
        target_manifest=target_manifest,
        source_database_digest=source_database_digest,
        target_database_digest=target_database_digest,
        leases=leases,
        gaps=tuple(gaps),
    )


def _occupied(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _prune_empty_directories(source: Path) -> None:
    for path in sorted((item for item in source.rglob("*") if item.is_dir()), reverse=True):
        if not any(path.iterdir()):
            path.rmdir()
    if source.is_dir() and not any(source.iterdir()):
        source.rmdir()


def _copy_target(plan: _MigrationPlan, staging: Path) -> None:
    staging.mkdir(parents=True)
    for relative, _digest in plan.target_manifest:
        source = plan.target / relative
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _merge_source_files(plan: _MigrationPlan, staging: Path) -> None:
    for relative, _digest in plan.source_manifest:
        destination = staging / relative
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plan.source / relative, destination)


def _write_database(path: Path, source: Path, rows: tuple[LeaseRow, ...]) -> None:
    if source.is_file() and source.stat().st_size:
        with (
            closing(sqlite3.connect(read_only_state_uri(source), uri=True)) as origin,
            closing(sqlite3.connect(path)) as destination,
        ):
            origin.backup(destination)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("begin immediate")
        initialize_state_connection(connection)
        connection.execute("delete from leases")
        connection.executemany(_LEASE_INSERT, rows)
        connection.commit()


def _move_source_to_hold(plan: _MigrationPlan, hold: Path) -> None:
    hold.mkdir(parents=True)
    relatives = (*[path for path, _digest in plan.source_manifest], *_DATABASE_FILES)
    for relative in relatives:
        origin = plan.source / relative
        if not origin.exists():
            continue
        destination = hold / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        origin.rename(destination)


def _restore_source(hold: Path, source: Path) -> None:
    if not hold.is_dir():
        return
    for current in sorted(path for path in hold.rglob("*") if path.is_file()):
        destination = source / current.relative_to(hold)
        destination.parent.mkdir(parents=True, exist_ok=True)
        current.rename(destination)
    shutil.rmtree(hold, ignore_errors=True)


def _restore_target(target: Path, backup: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    if backup.exists():
        backup.rename(target)


def _verify_migration(plan: _MigrationPlan) -> None:
    observed = _migration_plan(plan.repo)
    if observed.source_manifest or observed.gaps:
        message = "local_state_migration_verification_failed"
        raise ValueError(message)


def _apply_migration(plan: _MigrationPlan) -> None:
    digest = plan.digest
    staging = plan.target.with_name(f".{plan.target.name}.migrate-{digest[:12]}")
    backup = plan.target.with_name(f".{plan.target.name}.backup-{digest[:12]}")
    hold = plan.target.with_name(f".{plan.target.name}.source-{digest[:12]}")
    if any(_occupied(path) for path in (staging, backup, hold)):
        message = "local_state_migration_staging_occupied"
        raise ValueError(message)
    try:
        _copy_target(plan, staging)
        _merge_source_files(plan, staging)
        _write_database(staging / "state.sqlite", plan.source / "state.sqlite", plan.leases)
        _move_source_to_hold(plan, hold)
        if plan.target.exists():
            plan.target.rename(backup)
        staging.rename(plan.target)
        _verify_migration(plan)
    except BaseException:
        _restore_target(plan.target, backup)
        _restore_source(hold, plan.source)
        shutil.rmtree(staging, ignore_errors=True)
        raise
    shutil.rmtree(backup, ignore_errors=True)
    shutil.rmtree(hold, ignore_errors=True)
    _prune_empty_directories(plan.source)


def local_state_migration(
    root: Path,
    *,
    apply: bool,
    expect_plan_digest: str | None = None,
) -> dict[str, object]:
    """Plan or atomically merge legacy checkout state into the Git common directory."""
    plan = _migration_plan(root)
    gaps = list(plan.gaps)
    if apply and expect_plan_digest != plan.digest:
        gaps.insert(0, "local_state_migration_plan_digest_mismatch")
    has_source = bool(plan.source_manifest or (plan.source / "state.sqlite").exists())
    state = "blocked" if gaps else "current" if not has_source else "ready"
    if apply and not gaps and has_source:
        try:
            _apply_migration(plan)
        except ValueError as exc:
            gaps.append(str(exc))
        except OSError:
            gaps.append("local_state_migration_io_failed")
        state = "blocked" if gaps else "migrated"
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "source": plan.source.as_posix(),
        "target": plan.target.as_posix(),
        "plan_digest": plan.digest,
        "manifest": [{"path": path, "sha256": sha256} for path, sha256 in plan.source_manifest],
        "required_gaps": gaps,
    }


def local_state_mutation_guard(root: Path) -> dict[str, object]:
    """Require one reviewed migration before any legacy-backed mutation."""
    plan = _migration_plan(root)
    if plan.source_database_digest and not plan.target_database_digest:
        resolved = root.resolve()
        return {
            "required_gaps": ["local_state_migration_required"],
            "plan_digest": plan.digest,
            "next_action": (
                f"ethos migrate-local-state --root {resolved} --apply --authorize "
                f"--expect-head {current_head(resolved)} "
                f"--expect-plan-digest {plan.digest} --json"
            ),
        }
    return {"required_gaps": [], "plan_digest": "", "next_action": ""}
