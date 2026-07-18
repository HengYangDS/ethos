"""Shared utilities for the retrieval sub-package.

No imports from other retrieval submodules. Provides path helpers, hashing,
git HEAD resolution, and manifest lookup primitives used across the sub-package.
"""

from __future__ import annotations

import hashlib
import sqlite3
import subprocess
from contextlib import closing
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def default_retrieval_db_path(root: Path) -> Path:
    """Return the canonical SQLite database path for the given repository root."""
    return root / ".ethos" / "state" / "retrieval.sqlite"


def current_timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 form."""
    return datetime.now(UTC).isoformat()


def sha256_bytes(payload: bytes) -> str:
    """Return the lowercase SHA-256 hex digest for bytes."""
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    """Return the lowercase SHA-256 hex digest for UTF-8 text."""
    return sha256_bytes(payload.encode("utf-8"))


def context_index_files(db_path: Path) -> tuple[Path, ...]:
    """Return the SQLite database and sidecar WAL/SHM files."""
    return (
        db_path,
        db_path.with_suffix(".sqlite-wal"),
        db_path.with_suffix(".sqlite-shm"),
    )


def git_head(root: Path) -> str:
    """Return the current HEAD commit SHA for the given git repository root.

    Returns ``"untracked"`` if the root is not a git repository or HEAD cannot
    be resolved.
    """
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "untracked"


def latest_manifest_id(db_path: Path) -> str:
    """Return the most recently created manifest ID from the index database.

    Returns ``"manifest:none"`` if no manifest exists yet.
    """
    with closing(sqlite3.connect(db_path)) as connection:
        row = connection.execute(
            "select id from index_manifests order by created_at desc limit 1"
        ).fetchone()
    return str(row[0]) if row else "manifest:none"


def latest_manifest_head(db_path: Path) -> str:
    """Return the HEAD SHA recorded in the most recently created manifest.

    Returns ``"untracked"`` if no manifest exists yet.
    """
    with closing(sqlite3.connect(db_path)) as connection:
        row = connection.execute(
            "select head from index_manifests order by created_at desc limit 1"
        ).fetchone()
    return str(row[0]) if row else "untracked"
