"""Build-isolation-safe observation of one source build identity."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ethos.adapters.repo.git import run_git
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import load_build_identity_bytes
from ethos.repository.release.identity import product_version

_SOURCE_BUILD_IDENTITY = Path("src/ethos/data/build/identity.json")
_HEX = frozenset("0123456789abcdef")


def source_build_identity(root: Path, *, include_overlay: bool = True) -> BuildIdentity:
    """Compile the current Git checkout into its exact build identity."""
    commit, tree = source_git_identity(root, include_overlay=include_overlay)
    return build_identity(
        product=product_version(root),
        source_commit=commit,
        source_tree=tree,
    )


def build_input_identity(root: Path) -> BuildIdentity:
    """Resolve a Git checkout or its carried sdist build identity."""
    if (root / ".git").exists():
        return source_build_identity(root)
    try:
        return load_build_identity_bytes((root / _SOURCE_BUILD_IDENTITY).read_bytes())
    except OSError as error:
        message = "package_build_identity_missing"
        raise ValueError(message) from error


def source_distribution_version() -> str:
    """Hatch dynamic-version source for the current checkout."""
    return build_input_identity(Path(__file__).resolve().parents[5]).distribution_version


def source_git_identity(root: Path, *, include_overlay: bool = True) -> tuple[str, str]:
    """Return exact HEAD and the effective non-ignored source-build overlay."""
    commit = _git(root, "rev-parse", "HEAD")
    if not include_overlay:
        return commit, _git(root, "rev-parse", "HEAD^{tree}")
    with tempfile.TemporaryDirectory(prefix="ethos-source-index-") as directory:
        environment = {"GIT_INDEX_FILE": str(Path(directory) / "index")}
        _git(root, "read-tree", "HEAD", env=environment)
        _git(root, "add", "-A", env=environment)
        tree = _git(root, "write-tree", env=environment)
    if not _valid_git_identity(commit) or not _valid_git_identity(tree):
        message = "build_source_identity_invalid"
        raise ValueError(message)
    return commit, tree


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    completed = run_git(root, *args, env=env, check=False)
    if completed.returncode:
        message = "build_source_identity_unavailable"
        raise ValueError(message)
    return completed.stdout.strip()


def _valid_git_identity(value: str) -> bool:
    return len(value) in {40, 64} and not set(value) - _HEX
