"""Select the canonical package build identity for one repository runtime."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.profile import load_repository_profile
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import packaged_build_identity
from ethos.repository.release.identity import source_build_identity


def runtime_build_identity(source: Path) -> BuildIdentity:
    """Resolve one checkout or installed package to its canonical build identity."""
    if (source / "pyproject.toml").is_file() and (source / "VERSION").is_file():
        return source_build_identity(source)
    return packaged_build_identity()


def expected_runtime_build(root: Path) -> tuple[BuildIdentity, Path | None]:
    """Return the accepted self-hosted build or the invoking package build."""
    package_source = Path(__file__).resolve().parents[5]
    try:
        repo = repository_root(root)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError):
        return runtime_build_identity(package_source), None
    profile = load_repository_profile(repo)
    if profile.declaration is None or profile.declaration.profile_id != "ethos":
        return runtime_build_identity(package_source), None
    policy = load_branch_role_policy(repo)
    commit = ref_head(repo, policy.accepted_branch)
    tree = current_tree(repo, commit)
    accepted_root = _accepted_worktree(repo, policy.accepted_branch)
    identity = source_build_identity(accepted_root, channel="accepted")
    if identity.source_commit != commit or identity.source_tree != tree:
        message = "hook_runtime_accepted_build_identity_unavailable"
        raise ValueError(message)
    return identity, accepted_root


def _accepted_worktree(repo: Path, branch: str) -> Path:
    expected_ref = f"refs/heads/{branch}"
    for block in git_stdout(repo, "worktree", "list", "--porcelain").split("\n\n"):
        record = dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        if record.get("branch") == expected_ref and record.get("worktree"):
            return Path(record["worktree"]).resolve()
    return repo.resolve()
