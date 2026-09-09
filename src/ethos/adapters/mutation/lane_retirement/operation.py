"""Receipt-backed execution of one monotonic Work Lane retirement."""

from __future__ import annotations

import hashlib
import os
import shlex
import sqlite3
from contextlib import closing
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.mutation.lane_retirement.content import remove_reviewed_content
from ethos.adapters.mutation.lane_retirement.content import verify_reviewed_content
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import process_file_identities
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.runtime.filesystem import is_junction
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.worktree_effects import raw_worktree_records
from ethos.adapters.repo.worktree_effects import remove_worktree
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease_from_connection
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.lease.projection import observe_lease_from_connection
from ethos.adapters.store.state.schema import local_state_root
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.retirement import CarrierState
from ethos.contracts.retirement import RetirementObservation
from ethos.contracts.retirement import RetirementOperation
from ethos.contracts.retirement import RetirementProgress
from ethos.contracts.semantic import canonical_json_bytes
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from collections.abc import Mapping


def _fail(reason: str) -> None:
    raise ValueError(reason)


def retirement_failure(error: Exception) -> dict[str, object]:
    """Preserve failure evidence independently of observable retirement progress."""
    gap = (
        "lane_retirement_in_progress"
        if isinstance(error, Timeout)
        else getattr(error, "code", "") or str(error).partition(":")[0] or type(error).__name__
    )
    result: dict[str, object] = {"required_gaps": [str(gap)], "stderr": str(error)}
    if isinstance(error, ProcessExecutionError):
        result["process_failure"] = error.evidence()
    return result


def _receipt(store: Path, value: object, *, collision: str) -> dict[str, object]:
    payload = canonical_json_bytes(value)
    digest = hashlib.sha256(payload).hexdigest()
    path = write_content_addressed(store / f"{digest}.json", payload, collision=collision)
    return {
        "path": path.as_posix(),
        "sha256": f"sha256:{digest}",
        "size_bytes": len(payload),
        "media_type": "application/json",
    }


def operation_store(root: Path) -> Path:
    """Return the sole immutable request store for lane retirement."""
    return local_state_root(root) / "requests" / "lane-retirement"


def persist_operation(root: Path, request: RetirementOperation) -> dict[str, object]:
    """Persist the exact operation before any destructive effect."""
    return _receipt(
        operation_store(root),
        request.model_dump(mode="json"),
        collision="lane_retirement_receipt_collision",
    )


def _load_bytes(store: Path, path: str, sha256: str) -> bytes:
    candidate = Path(path).expanduser().resolve()
    digest = sha256.removeprefix("sha256:")
    if (
        len(digest) != 64
        or set(digest) - set("0123456789abcdef")
        or candidate.parent != store.resolve()
        or candidate.name != f"{digest}.json"
    ):
        _fail("lane_retirement_receipt_path_invalid")
    try:
        payload = candidate.read_bytes()
    except OSError as error:
        message = "lane_retirement_receipt_missing"
        raise ValueError(message) from error
    if hashlib.sha256(payload).hexdigest() != digest:
        _fail("lane_retirement_receipt_sha256_mismatch")
    return payload


def load_operation(root: Path, path: str, sha256: str) -> RetirementOperation:
    """Load one current receipt only from this repository's operation store."""
    try:
        return RetirementOperation.model_validate_json(
            _load_bytes(operation_store(root), path, sha256)
        )
    except ValueError as error:
        if str(error).startswith("lane_retirement_receipt_"):
            raise
        message = "lane_retirement_receipt_invalid"
        raise ValueError(message) from error


def persist_progress(
    root: Path, request: RetirementOperation, progress: RetirementProgress
) -> dict[str, object]:
    """Persist one immutable observed progress snapshot."""
    store = local_state_root(root) / "operations" / "lane-retirement" / request.digest()
    return _receipt(
        store,
        progress.model_dump(mode="json"),
        collision="lane_retirement_progress_collision",
    )


def persist_terminal_receipt(
    root: Path, request: RetirementOperation, progress: RetirementProgress
) -> dict[str, object]:
    """Persist the self-contained terminal result for one retirement."""
    return _receipt(
        local_state_root(root) / "receipts" / "lane-retirement",
        {
            "schema_version": 1,
            "kind": "lane-retirement-receipt",
            "request": request.model_dump(mode="json"),
            "progress": progress.model_dump(mode="json"),
        },
        collision="lane_retirement_terminal_receipt_collision",
    )


def reduce_progress(
    request: RetirementOperation, observation: RetirementObservation
) -> RetirementProgress:
    """Reduce current carrier facts into one monotonic operation state."""
    if request.worktree_initial == "unbound" and observation.worktree_state != "absent":
        _fail("retirement_operation_state_drift")
    if request.lease_state == "missing" and observation.lease_state != "absent":
        _fail("retirement_operation_state_drift")
    states = {
        "remove_worktree": observation.worktree_state,
        "delete_ref": observation.ref_state,
        "revoke_lease": observation.lease_state,
    }
    if observation.accepted_state != "expected" or any(
        states[effect] in {"moved", "unavailable"} for effect in request.effects
    ):
        _fail("retirement_operation_state_drift")
    completed = tuple(effect for effect in request.effects if states[effect] == "absent")
    remaining = tuple(effect for effect in request.effects if states[effect] == "expected")
    completion_flags = tuple(effect in completed for effect in request.effects)
    if completion_flags != tuple(sorted(completion_flags, reverse=True)):
        _fail("retirement_operation_state_drift")
    state = "terminal" if not remaining else "partial_transition" if completed else "ready"
    return RetirementProgress(
        request_digest=request.digest(),
        state=state,
        observation=observation,
        completed_effects=completed,
        remaining_effects=remaining,
    )


def _lease_outcome(root: Path, request: RetirementOperation) -> CarrierState:
    current = observe_lease(state_database(root), request.branch)
    if request.lease_state == "missing":
        return "absent" if current.state == "missing" else "moved"
    if current.state == "missing":
        return "absent"
    if current.state == "unknown":
        return "unavailable"
    return "expected" if lease_generation(current.record()) == dict(request.lease) else "moved"


def _worktree_outcome(root: Path, request: RetirementOperation) -> CarrierState:
    try:
        records = raw_worktree_records(root, runner=run_git)
    except ValueError:
        return "unavailable"
    matches = tuple(
        record
        for record in records
        if str(record.get("branch") or "").removeprefix("refs/heads/") == request.branch
    )
    if request.worktree_initial == "unbound":
        return "absent" if not matches else "moved"
    target = Path(request.worktree_path)
    if target.is_symlink() or is_junction(target):
        return "moved"
    if len(matches) != 1:
        return "moved" if matches or os.path.lexists(target) else "absent"
    record = matches[0]
    return (
        "expected"
        if Path(str(record.get("worktree") or "")).resolve() == target.resolve()
        and record.get("HEAD") == request.head
        and "locked" not in record
        and ("prunable" not in record or not os.path.lexists(target) or request.reviewed_content)
        else "moved"
    )


def _ref_outcome(root: Path, ref: str, expected: str) -> CarrierState:
    observed = run_git(root, "rev-parse", "--verify", "--quiet", ref, check=False)
    if observed.returncode == 0:
        return "expected" if observed.stdout.strip() == expected else "moved"
    return "absent" if observed.returncode == 1 else "unavailable"


def observe_operation(root: Path, request: RetirementOperation) -> RetirementObservation:
    """Observe all retirement carriers from the surviving control root."""
    control = Path(request.control_root)
    return RetirementObservation(
        worktree_state=_worktree_outcome(control, request),
        ref_state=_ref_outcome(control, f"refs/heads/{request.branch}", request.head),
        lease_state=_lease_outcome(root, request),
        accepted_state=_ref_outcome(
            control,
            f"refs/heads/{request.accepted_branch}",
            request.accepted_head,
        ),
    )


def _current_actor(request: RetirementOperation) -> bool:
    authority = cast("Mapping[str, object]", request.authority)
    return bool(authority.get("actor")) and os.environ.get("ETHOS_ACTOR", "").strip() == str(
        authority.get("actor")
    )


def _git_plan(request: RetirementOperation) -> TransitionPlan:
    return TransitionPlan.model_validate(mutable_json(request.git_plan))


def _admit_reviewed_content(root: Path, request: RetirementOperation) -> None:
    expected = request.reviewed_content
    nodes = (expected["root"], expected["index"], *expected["entries"].values())
    identities = {(int(node["identity"][0]), int(node["identity"][1])) for node in nodes}
    if identities & process_file_identities(root):
        _fail("retirement_content_in_use")
    verify_reviewed_content(
        Path(request.worktree_path), cast("dict[str, object]", mutable_json(expected))
    )


def preflight_operation(root: Path, request: RetirementOperation) -> RetirementProgress:
    """Return observed progress after validating process and authority coordinates."""
    if not _current_actor(request):
        _fail("foreign_work_lane_retire_authority_required")
    control = Path(request.control_root)
    execution_root = Path(request.execution_root)
    if request.worktree_path and execution_root.resolve() == Path(request.worktree_path).resolve():
        _fail("retirement_execution_root_is_target")
    for role, path in (("control", control), ("execution", execution_root)):
        unavailable = f"retirement_{role}_root_unavailable"
        if not path.is_absolute() or not path.is_dir() or path.is_symlink() or is_junction(path):
            _fail(unavailable)
        observed = run_git(
            path,
            "rev-parse",
            "--path-format=absolute",
            "--show-toplevel",
            "--git-common-dir",
            check=False,
        )
        coordinates = observed.stdout.splitlines()
        if observed.returncode or len(coordinates) != 2 or Path(coordinates[0]) != path.resolve():
            _fail(unavailable)
        if Path(coordinates[1]).resolve().as_posix() != request.repository_common_dir:
            _fail(
                "lane_retirement_receipt_repository_mismatch" if role == "control" else unavailable
            )
    if (
        request.repository_identity
        and repository_identity(control, tree_ref=request.accepted_head)
        != request.repository_identity
    ):
        _fail("lane_retirement_receipt_repository_mismatch")
    progress = reduce_progress(request, observe_operation(root, request))
    if "delete_ref" in progress.remaining_effects:
        admit_git_effect(execution_root, _git_plan(request))
    if request.reviewed_content and "remove_worktree" in progress.remaining_effects:
        _admit_reviewed_content(control, request)
    return progress


def remove_operation_worktree(root: Path, request: RetirementOperation) -> None:
    """Remove or recognize the exact target worktree from the surviving root."""
    remove_worktree(
        Path(request.control_root),
        Path(request.worktree_path),
        branch=request.branch,
        head=request.head,
        admit=partial(preflight_operation, root, request),
        dispose=(
            partial(
                remove_reviewed_content,
                Path(request.worktree_path),
                cast("dict[str, object]", mutable_json(request.reviewed_content)),
            )
            if request.reviewed_content
            else None
        ),
    )


def delete_operation_ref(_root: Path, request: RetirementOperation) -> None:
    """Delete or recognize the exact target ref through its admitted Git plan."""
    authority = cast("Mapping[str, object]", request.authority)
    execute_git_effect(
        Path(request.execution_root),
        _git_plan(request),
        issuer=str(authority["actor"]),
    )


def revoke_operation_lease(root: Path, request: RetirementOperation) -> None:
    """Revoke only the exact Lease after Git has reached terminal state."""
    lease = cast("Mapping[str, object]", request.lease)
    operation = LeaseOperationRequest(
        operation="revoke",
        branch=request.branch,
        holder_ref=str(lease["holder_ref"]),
        generation=int(str(lease["generation"])),
        expires_at=str(lease["expires_at"]),
        apply=True,
    )
    database = state_database(root)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("pragma foreign_keys = on")
        connection.execute("begin immediate")
        current = observe_lease_from_connection(connection, request.branch)
        if current.state == "missing":
            connection.rollback()
            return
        revoke_lease_from_connection(connection, request=operation)
        connection.commit()


def _recovery_command(root: Path, receipt: Mapping[str, object]) -> str:
    return " ".join(
        (
            "ethos lane retire recover",
            "--receipt",
            shlex.quote(str(receipt.get("path") or "")),
            "--receipt-sha256",
            shlex.quote(str(receipt.get("sha256") or "")),
            "--authorize --apply --root",
            shlex.quote(root.as_posix()),
            "--json",
        )
    )


def _report(
    root: Path,
    request: RetirementOperation,
    request_receipt: Mapping[str, object],
    progress: RetirementProgress | None,
    *,
    failure: Mapping[str, object] | None = None,
    progress_receipt: Mapping[str, object] | None = None,
    terminal_receipt: Mapping[str, object] | None = None,
) -> dict[str, object]:
    partial = progress is not None and progress.state == "partial_transition"
    state = progress.state if progress is not None else "ready"
    if state == "terminal":
        state = "retired"
    elif failure and not partial:
        state = "blocked"
    result: dict[str, object] = {
        "verdict": "block" if failure or partial else "pass",
        "state": state,
        "branch": request.branch,
        "head": request.head,
        "receipt": dict(request_receipt),
        "required_gaps": ["lane_retirement_partial"] if partial else [],
        "next_action": (
            _recovery_command(root, request_receipt)
            if progress is None or progress.remaining_effects
            else f"ethos status --root {root.as_posix()} --json"
        ),
        "user_decision_required": progress is None or bool(progress.remaining_effects),
        **dict(failure or {}),
    }
    if progress is not None:
        result.update(
            progress_receipt=dict(progress_receipt or {}),
            terminal_receipt=dict(terminal_receipt or {}),
            observed=progress.observation.model_dump(mode="json"),
            completed_effects=list(progress.completed_effects),
            remaining_effects=list(progress.remaining_effects),
        )
    return result


def apply_operation(
    request: RetirementOperation,
    *,
    request_receipt: Mapping[str, object],
    apply: bool = True,
) -> dict[str, object]:
    """Converge one exact retirement under its repository-scoped lock."""
    control_root = Path(request.control_root)
    lock = local_state_root(control_root) / "operations" / "lane-retirement.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        acquired = FileLock(str(lock)).acquire(timeout=0)
    except Timeout as error:
        return _report(
            control_root, request, request_receipt, None, failure=retirement_failure(error)
        )
    with acquired:
        failure: dict[str, object] = {}
        terminal_receipt: dict[str, object] = {}
        try:
            progress = preflight_operation(control_root, request)
            if not apply:
                return _report(
                    control_root,
                    request,
                    request_receipt,
                    progress,
                )
            progress_receipt = persist_progress(control_root, request, progress)
            actions = {
                "remove_worktree": remove_operation_worktree,
                "delete_ref": delete_operation_ref,
                "revoke_lease": revoke_operation_lease,
            }
            for effect in progress.remaining_effects:
                actions[effect](control_root, request)
                progress = reduce_progress(request, observe_operation(control_root, request))
                progress_receipt = persist_progress(control_root, request, progress)
            terminal_receipt = (
                persist_terminal_receipt(control_root, request, progress)
                if progress.state == "terminal"
                else {}
            )
        except (GitExecutionError, OSError, RuntimeError, TypeError, ValueError) as error:
            failure = retirement_failure(error)
            try:
                progress = reduce_progress(request, observe_operation(control_root, request))
                progress_receipt = persist_progress(control_root, request, progress)
            except (GitExecutionError, OSError, RuntimeError, TypeError, ValueError):
                return _report(control_root, request, request_receipt, None, failure=failure)
        return _report(
            control_root,
            request,
            request_receipt,
            progress,
            failure=failure,
            progress_receipt=progress_receipt,
            terminal_receipt=terminal_receipt,
        )


def execute_retirement_operation(
    *,
    root: Path,
    receipt_path: str,
    receipt_sha256: str,
    apply: bool,
    authorized: bool,
    expected_mode: Literal["landed", "superseded", "abandon"] | None = None,
) -> dict[str, object]:
    """Apply or resume one receipt after authority and command-mode admission."""
    repo = root.resolve()
    receipt = {"path": receipt_path, "sha256": receipt_sha256}
    try:
        if apply and not authorized:
            _fail("authorization_required")
        request = load_operation(repo, receipt_path, receipt_sha256)
        if expected_mode is not None and request.mode != expected_mode:
            _fail("lane_retirement_receipt_mode_invalid")
        if not _current_actor(request):
            _fail("foreign_work_lane_retire_authority_required")
        return apply_operation(request, request_receipt=receipt, apply=apply)
    except (GitExecutionError, OSError, RuntimeError, TypeError, ValueError) as error:
        return {
            "verdict": "block",
            "state": "blocked",
            **retirement_failure(error),
            "receipt": receipt,
            "next_action": "",
            "user_decision_required": False,
        }
