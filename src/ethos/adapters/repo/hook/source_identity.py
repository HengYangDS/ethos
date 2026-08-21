"""Exact ETHOS source identities for package and accepted hook runtimes."""

from __future__ import annotations

import json
import shlex
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.profile import load_repository_profile

_BUILD_IDENTITY_RESOURCE = "data/build/source-identity.json"


@dataclass(frozen=True, slots=True)
class RuntimeSourceIdentity:
    """One exact Git commit/tree pair carried by an ETHOS wheel."""

    commit: str
    tree: str


def runtime_source_identity(source: Path) -> RuntimeSourceIdentity:
    """Resolve source identity from a checkout or the installed wheel resource."""
    if (source / "pyproject.toml").is_file():
        try:
            root = repository_root(source)
        except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError):
            pass
        else:
            commit = git_stdout(root, "rev-parse", "HEAD")
            tree = _source_tree(root)
            if _valid_identity(commit, tree):
                return RuntimeSourceIdentity(commit=commit, tree=tree)
    try:
        raw = resources.files("ethos").joinpath(_BUILD_IDENTITY_RESOURCE).read_bytes()
    except (FileNotFoundError, OSError) as error:
        message = "hook_runtime_source_identity_missing"
        raise ValueError(message) from error
    try:
        return _identity_from_json(raw, invalid="hook_runtime_source_identity_invalid")
    except (TypeError, ValueError) as error:
        message = "hook_runtime_source_identity_invalid"
        raise ValueError(message) from error


def wheel_source_identity(wheel: Path) -> RuntimeSourceIdentity:
    """Read the immutable build identity carried inside one ETHOS wheel."""
    try:
        with zipfile.ZipFile(wheel) as archive:
            payload = archive.read(f"ethos/{_BUILD_IDENTITY_RESOURCE}")
    except (KeyError, OSError, zipfile.BadZipFile) as error:
        message = "hook_runtime_wheel_source_identity_missing"
        raise ValueError(message) from error
    try:
        return _identity_from_json(
            payload,
            invalid="hook_runtime_wheel_source_identity_invalid",
        )
    except (TypeError, ValueError) as error:
        message = "hook_runtime_wheel_source_identity_invalid"
        raise ValueError(message) from error


def expected_runtime_source(root: Path) -> tuple[RuntimeSourceIdentity, Path | None]:
    """Return the accepted ETHOS identity, or the invoking package identity."""
    package_source = Path(__file__).resolve().parents[5]
    try:
        repo = repository_root(root)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError):
        return runtime_source_identity(package_source), None
    profile = load_repository_profile(repo)
    if profile.declaration is not None and profile.declaration.profile_id == "ethos":
        policy = load_branch_role_policy(repo)
        commit = ref_head(repo, policy.accepted_branch)
        tree = current_tree(repo, commit)
        if not _valid_identity(commit, tree):
            message = "hook_runtime_accepted_source_identity_unavailable"
            raise ValueError(message)
        return (
            RuntimeSourceIdentity(commit=commit, tree=tree),
            _accepted_worktree(repo, policy.accepted_branch),
        )
    return runtime_source_identity(package_source), None


def hook_runtime_repair_action(root: Path, source_root: Path | None) -> str:
    """Render the one fully bound hook repair command for this repository."""
    repo = root.resolve()
    prefix = (
        f"cd {shlex.quote(source_root.as_posix())} && uv run " if source_root is not None else ""
    )
    return f"{prefix}ethos hook install --root {shlex.quote(repo.as_posix())} --json"


def _source_tree(root: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="ethos-source-index-") as directory:
        environment = {"GIT_INDEX_FILE": str(Path(directory) / "index")}
        read = run_git(root, "read-tree", "HEAD", check=False, env=environment)
        add = run_git(root, "add", "-A", check=False, env=environment)
        write = run_git(root, "write-tree", check=False, env=environment)
    failed = read.returncode or add.returncode or write.returncode
    return "" if failed else write.stdout.strip()


def _accepted_worktree(repo: Path, branch: str) -> Path:
    expected_ref = f"refs/heads/{branch}"
    for block in git_stdout(repo, "worktree", "list", "--porcelain").split("\n\n"):
        record = dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        if record.get("branch") == expected_ref and record.get("worktree"):
            return Path(record["worktree"]).resolve()
    return repo.resolve()


def _identity_from_json(raw: bytes, *, invalid: str) -> RuntimeSourceIdentity:
    try:
        text = raw.decode("utf-8")
        payload = json.loads(text)
    except (UnicodeError, TypeError, ValueError) as error:
        raise ValueError(invalid) from error
    if not isinstance(payload, dict):
        raise TypeError(invalid)
    commit = str(payload.get("source_commit") or "")
    tree = str(payload.get("source_tree") or "")
    if payload.get("schema_version") != 1 or not _valid_identity(commit, tree):
        raise ValueError(invalid)
    return RuntimeSourceIdentity(commit=commit, tree=tree)


def _valid_identity(commit: str, tree: str) -> bool:
    return all(
        len(value) in {40, 64} and not set(value) - set("0123456789abcdef")
        for value in (commit, tree)
    )
