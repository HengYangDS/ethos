"""Observe and apply exact idempotent Git worktree effects."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

    from ethos.contracts.semantic import Attestation


def add_worktree(
    root: Path,
    path: Path,
    *,
    head: str,
    branch: str = "detached",
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> Attestation:
    """Add or recognize one exact bound or detached worktree."""
    target = path.resolve()
    record = worktree_record(root, target, environment=environment, runner=runner)
    if record:
        _require_binding(record, target=target, branch=branch, head=head)
        effect = _effect("add", target, branch, head)
        return _attestation(root, "recognized", effect, record, record, environment)
    if os.path.lexists(target):
        raise ValueError("worktree_effect_path_collision")
    if branch != "detached" and ref_head(root, branch, environment=environment) != head:
        raise ValueError("worktree_effect_ref_stale")
    arguments = (
        ("worktree", "add", "--detach", target.as_posix(), head)
        if branch == "detached"
        else ("worktree", "add", target.as_posix(), branch)
    )
    completed = runner(root, *arguments, check=False, env=environment)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "worktree_effect_add_failed")
    record = worktree_record(root, target, environment=environment, runner=runner)
    _require_binding(record, target=target, branch=branch, head=head)
    return _attestation(
        root, "applied", _effect("add", target, branch, head), {}, record, environment
    )


def remove_worktree(
    root: Path,
    path: Path,
    *,
    head: str,
    branch: str,
    force: bool = False,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> Attestation:
    """Remove or recognize absence of one exact worktree binding."""
    target = path.resolve()
    record = worktree_record(root, target, environment=environment, runner=runner)
    if not record:
        if os.path.lexists(target):
            raise ValueError("worktree_effect_path_ownership_unknown")
        effect = _effect("remove", target, branch, head)
        return _attestation(root, "recognized", effect, {}, {}, environment)
    _require_binding(record, target=target, branch=branch, head=head)
    arguments = (
        ("worktree", "remove", "--force", target.as_posix())
        if force
        else ("worktree", "remove", target.as_posix())
    )
    completed = runner(root, *arguments, check=False, env=environment)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "worktree_effect_remove_failed")
    if worktree_record(root, target, environment=environment, runner=runner) or os.path.lexists(
        target
    ):
        raise ValueError("worktree_effect_postcondition_failed")
    effect = _effect("remove", target, branch, head)
    return _attestation(root, "applied", effect, record, {}, environment)


def sync_worktree(
    root: Path,
    path: Path,
    *,
    branch: str,
    previous: str,
    head: str,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> Attestation:
    """Synchronize or recognize one exact clean linked-worktree index effect."""
    target = path.resolve()
    before = _sync_observation(root, target, branch, environment=environment, runner=runner)
    if before["head"] == head and before["tree"] == _commit_tree(root, head, environment):
        effect = _effect("read-tree", target, branch, head)
        return _attestation(root, "recognized", effect, before, before, environment)
    if before["head"] != head or before["tree"] != _commit_tree(root, previous, environment):
        raise ValueError("worktree_effect_binding_stale")
    completed = runner(
        target,
        "read-tree",
        "-u",
        "-m",
        previous,
        head,
        check=False,
        env=environment,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "worktree_effect_sync_failed")
    after = _sync_observation(root, target, branch, environment=environment, runner=runner)
    if after["head"] != head or after["tree"] != _commit_tree(root, head, environment):
        raise ValueError("worktree_effect_postcondition_failed")
    effect = _effect("read-tree", target, branch, head)
    return _attestation(root, "applied", effect, before, after, environment)


def attach_worktree(
    root: Path,
    path: Path,
    *,
    branch: str,
    head: str,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> Attestation:
    """Attach or recognize one exact linked-worktree branch binding."""
    target = path.resolve()
    record = worktree_record(root, target, environment=environment, runner=runner)
    if ref_head(root, branch, environment=environment) != head:
        raise ValueError("worktree_effect_binding_stale")
    effect = _effect("switch", target, branch, head)
    observed_branch = record.get("branch", "").removeprefix("refs/heads/")
    if observed_branch == branch:
        _require_binding(record, target=target, branch=branch, head=head)
        return _attestation(root, "recognized", effect, record, record, environment)
    indexed = runner(target, "write-tree", check=False, env=environment)
    dirty = runner(target, "diff-files", "--quiet", check=False, env=environment)
    if (
        "detached" not in record
        or indexed.returncode
        or indexed.stdout.strip() != _commit_tree(root, head, environment)
        or dirty.returncode
    ):
        raise ValueError("worktree_effect_binding_stale")
    completed = runner(target, "switch", branch, check=False, env=environment)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "worktree_effect_attach_failed")
    after = worktree_record(root, target, environment=environment, runner=runner)
    _require_binding(after, target=target, branch=branch, head=head)
    return _attestation(root, "applied", effect, record, after, environment)


def worktree_record(
    root: Path,
    path: Path,
    *,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> dict[str, str]:
    """Return the sole raw Git record for one exact worktree path."""
    completed = runner(root, "worktree", "list", "--porcelain", check=False, env=environment)
    if completed.returncode:
        raise ValueError("worktree_effect_observation_failed")
    target = path.resolve()
    matches = [
        record
        for block in completed.stdout.split("\n\n")
        if block.strip()
        for record in (_record(block),)
        if record.get("worktree") and Path(record["worktree"]).resolve() == target
    ]
    if len(matches) > 1:
        raise ValueError("worktree_effect_observation_ambiguous")
    return matches[0] if matches else {}


def _record(block: str) -> dict[str, str]:
    return {
        parts[0]: parts[1] if len(parts) > 1 else ""
        for line in block.splitlines()
        if line
        for parts in (line.split(" ", 1),)
    }


def _require_binding(record: dict[str, str], *, target: Path, branch: str, head: str) -> None:
    observed_branch = (
        record.get("branch", "").removeprefix("refs/heads/")
        if "branch" in record
        else "detached"
        if "detached" in record
        else ""
    )
    if (
        not record
        or Path(record.get("worktree", "")).resolve() != target
        or record.get("HEAD") != head
        or observed_branch != branch
        or any(flag in record for flag in ("locked", "prunable"))
        or target.is_symlink()
        or not target.is_dir()
    ):
        raise ValueError("worktree_effect_binding_stale")


def _sync_observation(
    root: Path,
    target: Path,
    branch: str,
    *,
    environment: Mapping[str, str] | None,
    runner: Callable[..., Any],
) -> dict[str, str]:
    record = worktree_record(root, target, environment=environment, runner=runner)
    observed_branch = record.get("branch", "").removeprefix("refs/heads/")
    indexed = runner(target, "write-tree", check=False, env=environment)
    if (
        not record
        or observed_branch != branch
        or indexed.returncode
        or target.is_symlink()
        or not target.is_dir()
    ):
        raise ValueError("worktree_effect_binding_stale")
    return {
        "path": target.as_posix(),
        "branch": observed_branch,
        "head": record.get("HEAD", ""),
        "tree": indexed.stdout.strip(),
    }


def _commit_tree(root: Path, head: str, environment: Mapping[str, str] | None) -> str:
    completed = run_git(root, "rev-parse", f"{head}^{{tree}}", check=False, env=environment)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _attestation(
    root: Path,
    state: str,
    effect: Mapping[str, str],
    before: Mapping[str, str],
    after: Mapping[str, str],
    environment: Mapping[str, str] | None,
) -> Attestation:
    operation, path, branch, head = (
        effect["operation"],
        Path(effect["path"]),
        effect["branch"],
        effect["head"],
    )
    predicate = "effect:git-worktree-index" if operation == "read-tree" else "effect:git-worktree"
    input_observation = _canonical_observation(path, branch, head, before)
    output_observation = _canonical_observation(path, branch, head, after)
    repository = load_repository_commitment(
        root,
        tree_ref=head,
        environment=dict(environment or {}),
    )
    return issue_native_effect(
        root,
        effect=NativeEffect(
            predicate=predicate,
            operation=f"git.worktree.{operation}",
            command=(
                ("git", "read-tree", "-u", "-m")
                if operation == "read-tree"
                else ("git", "switch")
                if operation == "switch"
                else ("git", "worktree", operation)
            ),
            subject=effect,
            before=input_observation,
            after=output_observation,
        ),
        state=state,
        commitment_digest=repository.digest(),
        repository_id=repository.id,
    )


def _effect(operation: str, path: Path, branch: str, head: str) -> dict[str, str]:
    return {
        "operation": operation,
        "path": path.as_posix(),
        "branch": branch,
        "head": head,
    }


def _canonical_observation(
    path: Path,
    branch: str,
    head: str,
    observation: Mapping[str, str],
) -> dict[str, object]:
    present = bool(observation)
    return {
        "path": path.as_posix(),
        "branch": branch,
        "head": str(observation.get("head") or observation.get("HEAD") or head),
        "tree": str(observation.get("tree") or ""),
        "present": present,
    }
