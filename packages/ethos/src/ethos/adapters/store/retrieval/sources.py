"""Source discovery, filtering, and manifest digest for the retrieval index.

Determines which tracked files in the repository are allowed to be indexed,
checks for dirty (locally-modified) allowed sources, and computes the
source-manifest digest used to detect staleness.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ethos.adapters.store.retrieval.common import _sha256_text


def tracked_files(root: Path) -> list[Path]:
    """Return all files tracked by git at HEAD in the given repository root.

    Returns an empty list if *root* is not a git repository or HEAD cannot be
    resolved.
    """
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [root / line for line in completed.stdout.splitlines() if line.strip()]


def _tracked_source_paths(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in tracked_files(root)}


def allowed_sources(root: Path) -> list[Path]:
    """Return sorted list of tracked repository files eligible for indexing.

    Filters the full git-tracked file list through :func:`is_allowed_source_rel`
    and returns only files that pass.
    """
    allowed: list[Path] = []
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if is_allowed_source_rel(rel):
            allowed.append(path)
    return sorted(allowed)


def is_allowed_source_rel(rel: str) -> bool:
    """Return ``True`` if the repository-relative path is eligible for indexing.

    Allowed paths include top-level docs, openspec, evidence/claims, schemas,
    curated root files, package README files, and all Python source files under
    ``packages/``. Paths under ``.ethos/state/`` are always excluded.
    """
    if rel.startswith(".ethos/state/"):
        return False
    if rel in {"AGENTS.md", "CONTRIBUTING.md", "README.md", "pyproject.toml"}:
        return True
    if rel.endswith("/README.md") and rel.startswith("packages/"):
        return True
    if rel.startswith(("docs/", "openspec/", "evidence/claims/", "schemas/")):
        return True
    return rel.startswith("packages/") and Path(rel).suffix == ".py"


def dirty_allowed_sources(root: Path) -> list[str]:
    """Return repository-relative paths of allowed sources that are dirty.

    Dirty means locally modified (staged or unstaged) according to git porcelain
    status. Returns an empty list when *root* is not a git repository.
    """
    allowed_paths = {source.relative_to(root).as_posix() for source in allowed_sources(root)}
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    dirty: list[str] = []
    for line in completed.stdout.splitlines():
        for rel in porcelain_paths(line[3:].strip()):
            if rel in allowed_paths or is_allowed_source_rel(rel):
                dirty.append(rel)
    return sorted(dirty)


def porcelain_paths(pathspec: str) -> tuple[str, ...]:
    """Parse a git porcelain status pathspec into individual relative paths.

    Handles rename entries (``old -> new``) and quoted path names.
    """
    paths = pathspec.split(" -> ") if " -> " in pathspec else [pathspec]
    return tuple(path.strip().strip('"') for path in paths if path.strip())


def _source_manifest_digest(root: Path, sources: list[Path], head: str) -> str:
    source_manifest = {
        "head": head,
        "sources": [source.relative_to(root).as_posix() for source in sources],
    }
    return _sha256_text(json.dumps(source_manifest, sort_keys=True))


def unsafe_source_reason(root: Path, source: Path) -> str:
    """Return a non-empty reason string if *source* must not be indexed.

    Returns ``""`` when the source is safe to index. Possible reason strings:
    ``"missing_path"``, ``"path_outside_repository"``, ``"symlink_source"``.
    """
    if not source.exists():
        return "missing_path"
    resolved = source.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return "path_outside_repository"
    if source.is_symlink():
        return "symlink_source"
    return ""
