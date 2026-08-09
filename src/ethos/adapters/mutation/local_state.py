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

_DATABASE_FILES = ("state.sqlite", "state.sqlite-shm", "state.sqlite-wal")
_LEASE_SELECT = "select id, subject, owner, expires_at, payload_json from leases"
_LEASE_INSERT = (
    "insert into leases(id, subject, owner, expires_at, payload_json) values (?, ?, ?, ?, ?)"
)
LeaseRow = tuple[str, str, str, str, str]
Manifest = tuple[tuple[str, str], ...]


def _legacy_state_root(repo: Path) -> Path:
    policy = load_branch_role_policy(repo)
    worktrees = worktree_records(repo, current_path=repo, policy=policy)
    return accepted_worktree_root(worktrees, repo).resolve() / ".ethos" / "state"


def _manifest(repo: Path, root: Path, *, legacy: bool = False) -> Manifest:
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


def _database_snapshot(path: Path) -> tuple[str, tuple[LeaseRow, ...]]:
    if not path.is_file() or not path.stat().st_size:
        return "", ()
    with closing(sqlite3.connect(read_only_state_uri(path), uri=True)) as connection:
        digest = hashlib.sha256("\n".join(connection.iterdump()).encode()).hexdigest()
        if not validate_current_lease_schema(connection):
            return digest, ()
        rows = tuple(
            (str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]))
            for row in connection.execute(f"{_LEASE_SELECT} order by subject")
        )
    return digest, rows


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
        else:
            by_subject[row[1]] = by_id[row[0]] = row
    return tuple(sorted(by_subject.values(), key=lambda row: row[1])), tuple(gaps)


def _move_files(source: Path, target: Path, relatives: tuple[str, ...]) -> None:
    for relative in relatives:
        origin = source / relative
        if not origin.exists():
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        origin.rename(destination)


def _verify_migration(migration: _Migration) -> None:
    migration.verify()


@dataclass(frozen=True, slots=True)
class _Migration:
    repo: Path
    source: Path
    target: Path
    source_manifest: Manifest
    target_manifest: Manifest
    source_database_digest: str
    target_database_digest: str
    leases: tuple[LeaseRow, ...]
    gaps: tuple[str, ...]

    @classmethod
    def plan(cls, root: Path) -> _Migration:
        repo = repository_root(root)
        source = _legacy_state_root(repo)
        target = local_state_root(repo)
        invalid = source.is_symlink() or (
            source.exists()
            and (not source.is_dir() or any(path.is_symlink() for path in source.rglob("*")))
        )
        source_manifest = () if invalid else _manifest(repo, source, legacy=True)
        target_manifest = _manifest(repo, target)
        gaps = ["local_state_source_invalid"] if invalid else []
        source_digest = target_digest = ""
        leases: tuple[LeaseRow, ...] = ()
        try:
            source_digest, source_leases = _database_snapshot(source / "state.sqlite")
            target_digest, target_leases = _database_snapshot(target / "state.sqlite")
            leases, lease_gaps = _merge_leases(source_leases, target_leases)
        except (RuntimeError, sqlite3.Error):
            gaps.append("local_state_database_invalid")
        else:
            gaps.extend(lease_gaps)
        target_files = dict(target_manifest)
        gaps.extend(
            f"local_state_file_conflict:{path}"
            for path, digest in source_manifest
            if path in target_files and target_files[path] != digest
        )
        return cls(
            repo,
            source,
            target,
            source_manifest,
            target_manifest,
            source_digest,
            target_digest,
            leases,
            tuple(gaps),
        )

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

    @property
    def has_source(self) -> bool:
        return bool(self.source_manifest or self.source_database_digest)

    def verify(self) -> None:
        observed = type(self).plan(self.repo)
        expected = dict(self.target_manifest)
        expected.update(self.source_manifest)
        source_present = _manifest(self.repo, self.source, legacy=True) or any(
            (self.source / name).exists() for name in _DATABASE_FILES
        )
        if (
            source_present
            or dict(observed.target_manifest) != expected
            or observed.leases != self.leases
            or observed.gaps
        ):
            message = "local_state_migration_verification_failed"
            raise ValueError(message)

    def apply(self) -> None:
        suffix = self.digest[:12]
        staging = self.target.with_name(f".{self.target.name}.migrate-{suffix}")
        backup = self.target.with_name(f".{self.target.name}.backup-{suffix}")
        hold = self.target.with_name(f".{self.target.name}.source-{suffix}")
        if any(path.exists() or path.is_symlink() for path in (staging, backup, hold)):
            message = "local_state_migration_staging_occupied"
            raise ValueError(message)
        source_relatives = tuple(path for path, _digest in self.source_manifest) + _DATABASE_FILES
        try:
            self.materialize(staging)
            _move_files(self.source, hold, source_relatives)
            if self.target.exists():
                self.target.rename(backup)
            staging.rename(self.target)
            _verify_migration(self)
        except BaseException:
            if self.target.exists():
                shutil.rmtree(self.target)
            if backup.exists():
                backup.rename(self.target)
            _move_files(hold, self.source, source_relatives)
            shutil.rmtree(staging, ignore_errors=True)
            shutil.rmtree(hold, ignore_errors=True)
            raise
        shutil.rmtree(backup, ignore_errors=True)
        shutil.rmtree(hold, ignore_errors=True)
        for path in sorted(
            (item for item in self.source.rglob("*") if item.is_dir()), reverse=True
        ):
            if not any(path.iterdir()):
                path.rmdir()
        if self.source.is_dir() and not any(self.source.iterdir()):
            self.source.rmdir()

    def materialize(self, staging: Path) -> None:
        staging.mkdir(parents=True)
        for root, manifest in (
            (self.target, self.target_manifest),
            (self.source, self.source_manifest),
        ):
            for relative, _digest in manifest:
                destination = staging / relative
                if destination.exists():
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / relative, destination)
        database_source = (
            self.source / "state.sqlite"
            if self.source_database_digest
            else self.target / "state.sqlite"
        )
        if database_source.is_file() and database_source.stat().st_size:
            with (
                closing(sqlite3.connect(read_only_state_uri(database_source), uri=True)) as origin,
                closing(sqlite3.connect(staging / "state.sqlite")) as destination,
            ):
                origin.backup(destination)
        with closing(sqlite3.connect(staging / "state.sqlite")) as connection:
            connection.execute("begin immediate")
            initialize_state_connection(connection)
            connection.execute("delete from leases")
            connection.executemany(_LEASE_INSERT, self.leases)
            connection.commit()


def local_state_migration(
    root: Path,
    *,
    apply: bool,
    expect_plan_digest: str | None = None,
) -> dict[str, object]:
    """Plan or atomically merge legacy checkout state into the Git common directory."""
    migration = _Migration.plan(root)
    gaps = list(migration.gaps)
    if apply and expect_plan_digest != migration.digest:
        gaps.insert(0, "local_state_migration_plan_digest_mismatch")
    state = "blocked" if gaps else "ready" if migration.has_source else "current"
    if apply and not gaps and migration.has_source:
        try:
            migration.apply()
        except ValueError as exc:
            gaps.append(str(exc))
        except (OSError, sqlite3.Error):
            gaps.append("local_state_migration_io_failed")
        state = "blocked" if gaps else "migrated"
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "source": migration.source.as_posix(),
        "target": migration.target.as_posix(),
        "plan_digest": migration.digest,
        "manifest": [
            {"path": path, "sha256": sha256} for path, sha256 in migration.source_manifest
        ],
        "required_gaps": gaps,
    }


def local_state_mutation_guard(root: Path) -> dict[str, object]:
    """Require one reviewed migration before any legacy-backed mutation."""
    migration = _Migration.plan(root)
    if migration.source_database_digest and not migration.target_database_digest:
        resolved = root.resolve()
        return {
            "required_gaps": ["local_state_migration_required"],
            "plan_digest": migration.digest,
            "next_action": (
                f"ethos migrate-local-state --root {resolved} --apply --authorize "
                f"--expect-head {current_head(resolved)} "
                f"--expect-plan-digest {migration.digest} --json"
            ),
        }
    return {"required_gaps": [], "plan_digest": "", "next_action": ""}
