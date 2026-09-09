"""Observe and apply exact idempotent Git worktree effects."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.runtime.filesystem import is_junction

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

    from ethos.contracts.semantic import Attestation


def _fail(message: str) -> None:
    raise ValueError(message)


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
        _fail("worktree_effect_path_collision")
    if branch != "detached" and ref_head(root, branch, environment=environment) != head:
        _fail("worktree_effect_ref_stale")
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
    admit: Callable[[], object] | None = None,
    dispose: Callable[[], None] | None = None,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> Attestation:
    """Remove an exact binding after caller admission, or recognize its absence."""
    if path.is_symlink() or is_junction(path):
        _fail("worktree_effect_binding_stale")
    target = path.resolve()
    record = worktree_record(root, target, environment=environment, runner=runner)
    if not record:
        if os.path.lexists(target):
            _fail("worktree_effect_path_ownership_unknown")
        effect = _effect("remove", target, branch, head)
        return _attestation(root, "recognized", effect, {}, {}, environment)
    absent = not os.path.lexists(target)
    _require_binding(
        record, target=target, branch=branch, head=head, absent=absent, reviewed=dispose is not None
    )
    arguments = (
        ("worktree", "remove", "--force", target.as_posix())
        if force
        else ("worktree", "remove", target.as_posix())
    )
    for callback, expected_absence in ((admit, absent), (dispose, True)):
        if callback is not None:
            callback()
            _require_binding(
                worktree_record(root, target, environment=environment, runner=runner),
                target=target,
                branch=branch,
                head=head,
                absent=expected_absence,
                reviewed=dispose is not None,
            )
    completed = runner(root, *arguments, check=False, env=environment)
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "worktree_effect_remove_failed")
    if worktree_record(root, target, environment=environment, runner=runner) or os.path.lexists(
        target
    ):
        _fail("worktree_effect_postcondition_failed")
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
    if before["head"] == head and before["tree"] == current_tree(
        root, head, environment=environment
    ):
        effect = _effect("read-tree", target, branch, head)
        return _attestation(root, "recognized", effect, before, before, environment)
    if before["head"] != head or before["tree"] != current_tree(
        root, previous, environment=environment
    ):
        _fail("worktree_effect_binding_stale")
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
    if after["head"] != head or after["tree"] != current_tree(root, head, environment=environment):
        _fail("worktree_effect_postcondition_failed")
    effect = _effect("read-tree", target, branch, head)
    return _attestation(root, "applied", effect, before, after, environment)


def restore_rejected_checkout_projection(
    root: Path,
    *,
    target_head: str,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> bool:
    """Restore a clean Git porcelain projection whose ref transaction was rejected."""
    current_head = runner(root, "rev-parse", "HEAD", check=False, env=environment).stdout.strip()
    target_tree = current_tree(root, target_head, environment=environment)
    indexed = runner(root, "write-tree", check=False, env=environment)
    dirty = runner(root, "diff-files", "--quiet", check=False, env=environment)
    if (
        not current_head
        or not target_tree
        or indexed.returncode
        or indexed.stdout.strip() != target_tree
        or dirty.returncode
    ):
        return False
    restored = runner(
        root,
        "read-tree",
        "--reset",
        "-u",
        current_head,
        check=False,
        env=environment,
    )
    if restored.returncode:
        return False
    indexed = runner(root, "write-tree", check=False, env=environment)
    dirty = runner(root, "diff-files", "--quiet", check=False, env=environment)
    return (
        not indexed.returncode
        and indexed.stdout.strip() == current_tree(root, current_head, environment=environment)
        and not dirty.returncode
    )


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
        _fail("worktree_effect_binding_stale")
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
        or indexed.stdout.strip() != current_tree(root, head, environment=environment)
        or dirty.returncode
    ):
        _fail("worktree_effect_binding_stale")
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
    target = path.resolve()
    matches = [
        record
        for record in raw_worktree_records(root, environment=environment, runner=runner)
        if record.get("worktree") and Path(record["worktree"]).resolve() == target
    ]
    if len(matches) > 1:
        _fail("worktree_effect_observation_ambiguous")
    return matches[0] if matches else {}


def raw_worktree_records(
    root: Path,
    *,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> tuple[dict[str, str], ...]:
    """Observe native worktree records, preserving flags and observation failures."""
    completed = runner(root, "worktree", "list", "--porcelain", check=False, env=environment)
    if completed.returncode:
        _fail("worktree_effect_observation_failed")
    return tuple(
        dict(line.partition(" ")[::2] for line in block.splitlines() if line)
        for block in completed.stdout.split("\n\n")
        if block.strip()
    )


def _require_binding(
    record: dict[str, str],
    *,
    target: Path,
    branch: str,
    head: str,
    absent: bool = False,
    reviewed: bool = False,
) -> None:
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
        or "locked" in record
        or ("prunable" in record and not (absent or reviewed))
        or target.is_symlink()
        or (os.path.lexists(target) if absent else not target.is_dir())
    ):
        _fail("worktree_effect_binding_stale")


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
        _fail("worktree_effect_binding_stale")
    return {
        "path": target.as_posix(),
        "branch": observed_branch,
        "head": record.get("HEAD", ""),
        "tree": indexed.stdout.strip(),
    }


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
    repository = repository_identity(root, tree_ref="HEAD", environment=environment)
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
        commitment_digest=None,
        repository_id=repository,
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
