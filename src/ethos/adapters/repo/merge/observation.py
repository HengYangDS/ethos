"""Observe exact native merge state without inventing persistent workflow state."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISREG

from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.dirty.change_provenance import untracked_content_sha256
from ethos.adapters.repo.git import run_git
from ethos.contracts.semantic import canonical_json_digest

MERGE_METADATA = (
    "MERGE_HEAD",
    "MERGE_MSG",
    "MERGE_MODE",
    "MERGE_AUTOSTASH",
    "AUTO_MERGE",
    "ORIG_HEAD",
)


def git_path(root: Path, name: str) -> Path:
    """Resolve one worktree-local native metadata path through Git."""
    return Path(
        run_git(root, "rev-parse", "--path-format=absolute", "--git-path", name).stdout.strip()
    )


def metadata_bytes(path: Path) -> bytes | None:
    """Read one regular native metadata file without following symlinks."""
    try:
        named_before = path.stat(follow_symlinks=False)
        if not S_ISREG(named_before.st_mode):
            message = "merge_metadata_unsafe"
            raise ValueError(message)
        descriptor = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        )
    except FileNotFoundError:
        return None
    try:
        before = os.fstat(descriptor)
        if not S_ISREG(before.st_mode):
            message = "merge_metadata_unsafe"
            raise ValueError(message)
        if not os.path.samestat(named_before, before):
            message = "merge_metadata_changed"
            raise ValueError(message)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            content = stream.read()
        if _content_identity(before) != _content_identity(
            os.fstat(descriptor)
        ) or _content_identity(named_before) != _content_identity(path.stat(follow_symlinks=False)):
            message = "merge_metadata_changed"
            raise ValueError(message)
        return content
    finally:
        os.close(descriptor)


def _content_identity(observed: os.stat_result) -> tuple[int, ...]:
    """Bind replacement/content metadata, excluding read-induced access time."""
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_mode,
        observed.st_uid,
        observed.st_gid,
        observed.st_size,
        observed.st_mtime_ns,
        observed.st_ctime_ns,
    )


@dataclass(frozen=True, slots=True)
class MergeObservation:
    """One immutable observation, not a reusable permission or operation record."""

    head: str
    branch: str
    parents: tuple[str, ...]
    conflicts: tuple[str, ...]
    metadata: dict[str, str]
    index_digest: str
    content_digest: str
    untracked_digest: str
    competing: tuple[str, ...]

    def projection(self) -> dict[str, object]:
        """Expose the exact coordinates compared before an effect."""
        return {
            "head": self.head,
            "branch": self.branch,
            "parents": list(self.parents),
            "conflicts": list(self.conflicts),
            "metadata": self.metadata,
            "index_digest": self.index_digest,
            "content_digest": self.content_digest,
            "untracked_digest": self.untracked_digest,
            "competing": list(self.competing),
        }

    @property
    def digest(self) -> str:
        """Bind the complete semantic native observation."""
        return canonical_json_digest(self.projection())


def observe_merge(root: Path) -> MergeObservation:
    """Observe parents, stages and affected content with native Git readers."""
    head = run_git(root, "rev-parse", "HEAD", observation=True).stdout.strip()
    branch = run_git(root, "branch", "--show-current", observation=True).stdout.strip()
    raw = {name: metadata_bytes(git_path(root, name)) for name in MERGE_METADATA}
    parents = tuple((raw["MERGE_HEAD"] or b"").decode("ascii").split())
    for parent in parents:
        checked = run_git(
            root, "rev-parse", "--verify", f"{parent}^{{commit}}", check=False, observation=True
        )
        if checked.returncode or checked.stdout.strip() != parent:
            message = "merge_parent_invalid"
            raise ValueError(message)
    stages = run_git(root, "ls-files", "--stage", "-z", observation=True, text=False).stdout
    unmerged = run_git(
        root, "diff", "--name-only", "--diff-filter=U", "-z", observation=True
    ).stdout
    competing = tuple(
        name
        for name in ("rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD", "sequencer")
        if git_path(root, name).exists()
    )
    return MergeObservation(
        head,
        branch,
        parents,
        tuple(filter(None, unmerged.split("\0"))),
        {
            name: hashlib.sha256(content).hexdigest()
            for name, content in raw.items()
            if content is not None
        },
        hashlib.sha256(stages).hexdigest(),
        dirty_content_sha256(root),
        untracked_content_sha256(root),
        competing,
    )


def pending_merge_heads(root: Path) -> tuple[str, ...]:
    """Read only native merge parents for lightweight status and intent selection."""
    return tuple((metadata_bytes(git_path(root, "MERGE_HEAD")) or b"").decode("ascii").split())
