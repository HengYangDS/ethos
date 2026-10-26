"""Observe and apply exact idempotent Git worktree effects."""

from __future__ import annotations

import os
import subprocess
from contextlib import ExitStack
from contextlib import contextmanager
from contextlib import suppress
from pathlib import Path
from tempfile import TemporaryFile
from threading import Event
from threading import Timer
from time import monotonic
from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn

from ethos.adapters.process import CommandScope
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import command_scope
from ethos.adapters.repo.dirty.change_provenance import working_content_changed
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_environment
from ethos.adapters.repo.git import git_executable
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.runtime.filesystem import is_junction

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from collections.abc import Mapping

    from ethos.contracts.semantic import Attestation


def _fail(message: str) -> NoReturn:
    raise ValueError(message)


def _ref_assertions(root: Path, assertions: Mapping[str, str], timeout_seconds: float) -> None:
    if not assertions or timeout_seconds <= 0:
        _fail("worktree_effect_ref_binding_invalid")
    for ref, head in assertions.items():
        if (
            not head
            or set(head) - set("0123456789abcdef")
            or run_git(root, "check-ref-format", ref, check=False).returncode
        ):
            _fail("worktree_effect_ref_binding_invalid")


def _abort_ref_input(process: subprocess.Popen[bytes]) -> None:
    """Native EOF abort releases prepared locks before any forced termination."""
    with suppress(OSError, ValueError):
        if process.stdin is not None:
            process.stdin.close()


def _release_ref_transaction(scope: CommandScope, process: subprocess.Popen[bytes]) -> None:
    _abort_ref_input(process)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        scope.terminate(process)
        process.wait()


@contextmanager
def hold_worktree_refs(
    root: Path, assertions: Mapping[str, str], *, timeout_seconds: float = 120
) -> Generator[None]:
    """Hold exact native ref assertions through a worktree effect without moving refs."""
    _ref_assertions(root, assertions, timeout_seconds)
    deadline = monotonic() + timeout_seconds
    environment = git_environment()
    command = (git_executable(environment), "update-ref", "--stdin")
    with (
        command_scope(timeout_seconds=timeout_seconds) as scope,
        TemporaryFile() as errors,
        ExitStack() as resources,
    ):
        process: subprocess.Popen[bytes] = scope.start(
            command,
            resources=resources,
            cwd=root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            bufsize=0,
            **({"process_group": 0} if os.name == "posix" else {}),
        )
        expired = Event()

        def cancel() -> None:
            expired.set()
            _abort_ref_input(process)

        timer = Timer(timeout_seconds, cancel)
        timer.start()
        try:
            if process.stdin is None or process.stdout is None:
                _fail("worktree_effect_ref_lock_unavailable")
            program = (
                "start\n"
                + "".join(
                    f"update {ref} {head} {head}\n" for ref, head in sorted(assertions.items())
                )
                + "prepare\n"
            )
            process.stdin.write(program.encode())
            process.stdin.flush()
            for expected in (b"start: ok\n", b"prepare: ok\n"):
                if process.stdout.readline() != expected:
                    _release_ref_transaction(scope, process)
                    errors.seek(0)
                    failure = ProcessExecutionError(
                        "worktree_effect_ref_lock_timeout"
                        if expired.is_set()
                        else "worktree_effect_ref_preparation_failed",
                        reason="reference_transaction_preparation_failed",
                        command=command,
                        cwd=os.fspath(root),
                        cause=errors.read().decode(errors="replace").strip(),
                        observation={"returncode": process.returncode},
                    )
                    raise failure
            timer.cancel()
            timer.join()
            if expired.is_set():
                _fail("worktree_effect_ref_lock_timeout")
            yield
            if monotonic() >= deadline:
                _fail("worktree_effect_ref_lock_timeout")
            process.stdin.write(b"abort\n")
            process.stdin.flush()
            output, _ = process.communicate(timeout=timeout_seconds)
            if process.returncode or output != b"abort: ok\n":
                _fail("worktree_effect_ref_lock_release_failed")
        finally:
            timer.cancel()
            timer.join()
            _release_ref_transaction(scope, process)


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
    refreshed = runner(target, "update-index", "--refresh", check=False, env=environment)
    if refreshed.returncode:
        raise ValueError(refreshed.stderr.strip() or "worktree_effect_preimage_dirty")
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
    """Restore a clean Git porcelain projection whose ref transaction was rejected.

    Git projected the target only if another ref already contains it. A commit that only the
    rejected operation created holds the caller's own content, so its checkout is never reset.
    """
    owners = runner(
        root, "for-each-ref", "--contains", target_head, "--count=1", check=False, env=environment
    )
    if owners.returncode or not owners.stdout.strip():
        return False
    current_head = runner(root, "rev-parse", "HEAD", check=False, env=environment).stdout.strip()
    target_tree = current_tree(root, target_head, environment=environment)
    indexed = runner(root, "write-tree", check=False, env=environment)
    dirty = working_content_changed(root, environment=environment, runner=runner)
    if (
        not current_head
        or not target_tree
        or indexed.returncode
        or indexed.stdout.strip() != target_tree
        or dirty is not False
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
    dirty = working_content_changed(root, environment=environment, runner=runner)
    return (
        not indexed.returncode
        and indexed.stdout.strip() == current_tree(root, current_head, environment=environment)
        and dirty is False
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
    dirty = working_content_changed(target, environment=environment, runner=runner)
    if (
        "detached" not in record
        or indexed.returncode
        or indexed.stdout.strip() != current_tree(root, head, environment=environment)
        or dirty is not False
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
