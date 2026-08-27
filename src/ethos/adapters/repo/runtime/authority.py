"""Select the canonical package build identity for one repository runtime."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.source import source_build_identity
from ethos.adapters.repo.runtime.source import source_head_build_identity
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.profile import load_repository_profile
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import packaged_build_identity


def runtime_build_identity(source: Path) -> BuildIdentity:
    """Resolve one checkout or installed package to its canonical build identity."""
    if (source / "VERSION").is_file():
        return source_build_identity(source)
    return packaged_build_identity()


def invoking_build_identity() -> BuildIdentity:
    """Resolve the invoking source checkout or installed package identity."""
    source = Path(__file__).resolve().parents[5]
    return runtime_build_identity(source)


def expected_runtime_build(root: Path) -> tuple[BuildIdentity, Path | None]:
    """Return the accepted self-hosted build or the invoking package build."""
    package_source = Path(__file__).resolve().parents[5]
    source_authority = (
        package_source
        if (package_source / "pyproject.toml").is_file() and (package_source / "VERSION").is_file()
        else None
    )
    try:
        repo = repository_root(root)
        profile = load_repository_profile(repo).declaration
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError):
        return runtime_build_identity(package_source), source_authority
    if profile is None or profile.profile_id != "ethos":
        return runtime_build_identity(package_source), source_authority
    policy = load_branch_role_policy(repo)
    commit = ref_head(repo, policy.accepted_branch)
    tree = current_tree(repo, commit)
    if accepted_version_migration_pending(repo, accepted_commit=commit):
        return source_head_build_identity(package_source), source_authority
    accepted_root = _accepted_worktree(repo, policy.accepted_branch)
    identity = source_build_identity(accepted_root, channel="accepted")
    if identity.source_commit != commit or identity.source_tree != tree:
        message = "hook_runtime_accepted_build_identity_unavailable"
        raise ValueError(message)
    return identity, accepted_root


def expected_runtime_source(root: Path) -> tuple[str, str]:
    """Return the exact source coordinates of the accepted runtime authority."""
    package_source = Path(__file__).resolve().parents[5]
    try:
        repo = repository_root(root)
        profile = load_repository_profile(repo).declaration
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError):
        build = runtime_build_identity(package_source)
        return build.source_commit, build.source_tree
    if profile is None or profile.profile_id != "ethos":
        build = runtime_build_identity(package_source)
        return build.source_commit, build.source_tree
    policy = load_branch_role_policy(repo)
    commit = ref_head(repo, policy.accepted_branch)
    if accepted_version_migration_pending(repo, accepted_commit=commit):
        identity = source_head_build_identity(package_source)
        return identity.source_commit, identity.source_tree
    return commit, current_tree(repo, commit)


def accepted_version_migration_pending(
    root: Path,
    *,
    accepted_commit: str | None = None,
) -> bool:
    """Return whether the accepted source predates the tracked VERSION authority."""
    repo = repository_root(root)
    commit = accepted_commit or ref_head(repo, load_branch_role_policy(repo).accepted_branch)
    return run_git(repo, "cat-file", "-e", f"{commit}:VERSION", check=False).returncode != 0


def _accepted_worktree(repo: Path, branch: str) -> Path:
    expected_ref = f"refs/heads/{branch}"
    records = (
        dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        for block in git_stdout(repo, "worktree", "list", "--porcelain").split("\n\n")
    )
    return next(
        (Path(record["worktree"]) for record in records if record.get("branch") == expected_ref),
        repo,
    ).resolve()
