from __future__ import annotations

import os
import subprocess
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable

import ethos.adapters.mutation.lane_start_rollback as rollback
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.openspec.profile import active_change_names_in_ref
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease


class LaneStartContext(NamedTuple):
    """Immutable inputs whose equality defines one lane-start saga."""

    repo: Path
    policy: BranchRolePolicy
    branch: str
    target: Path
    holder_ref: str
    base_commitment_digest: str
    candidate: dict[str, object]
    source_root: Path
    source_change_id: str
    source_head: str
    source_branch: str
    run: Callable[..., subprocess.CompletedProcess[str]]
    acquire: Callable[..., dict[str, object]]


def create_lane_start_carrier(context: LaneStartContext) -> dict[str, object]:
    """Initialize detached content, acquire its Lease, then bind the lane ref."""
    candidate_head = str(context.candidate["head"])
    prepared, final_head = prepare_lane_start_carrier(context)
    if prepared is not None:
        failure_gap = (
            "worktree_add_failed"
            if not os.path.lexists(context.target)
            else prepared.stderr.strip() or "lane_start_initialization_failed"
        )
        return rollback.rollback_lane_start(
            rollback.LaneStartRollback(
                repo=context.repo,
                target=context.target,
                branch=context.branch,
                ownership=("detached", candidate_head, ""),
                completed=prepared,
                run=context.run,
                lease=None,
                failure_gap=failure_gap,
            )
        )
    try:
        issued_at = datetime.now(UTC)
        lease = context.acquire(
            state_database(context.repo),
            lease=LaneLease(
                lane_incarnation_id=f"lane-incarnation:{uuid.uuid4()}",
                lease_id=f"lease:{uuid.uuid4()}",
                lane_ref=context.branch,
                holder_ref=HolderRef.parse(context.holder_ref),
                epoch=1,
                issued_at=issued_at,
                renewed_at=issued_at,
                expires_at=issued_at + timedelta(days=1),
                expected_head=final_head,
                base_commitment_digest=context.base_commitment_digest,
                path_scope=(),
            ),
        )
    except (RuntimeError, ValueError) as exc:
        return rollback.rollback_lane_start(
            rollback.LaneStartRollback(
                repo=context.repo,
                target=context.target,
                branch=context.branch,
                ownership=("detached", candidate_head, ""),
                completed=failed_process(str(exc)),
                run=context.run,
                lease=None,
                failure_gap=str(exc),
            )
        )
    created_ref = context.run(
        context.repo,
        "update-ref",
        f"refs/heads/{context.branch}",
        final_head,
        "",
        check=False,
        env={"ETHOS_ACTOR": context.holder_ref},
    )
    if created_ref.returncode != 0 or ref_head(context.repo, context.branch) != final_head:
        return rollback.rollback_lane_start(
            rollback.LaneStartRollback(
                repo=context.repo,
                target=context.target,
                branch=context.branch,
                ownership=(
                    "detached",
                    candidate_head,
                    final_head if created_ref.returncode == 0 else "",
                ),
                completed=created_ref,
                run=context.run,
                lease=lease,
                failure_gap="lane_start_ref_creation_failed",
            )
        )
    attached = context.run(
        context.target,
        "symbolic-ref",
        "HEAD",
        f"refs/heads/{context.branch}",
        check=False,
    )
    if attached.returncode != 0:
        return rollback.rollback_lane_start(
            rollback.LaneStartRollback(
                repo=context.repo,
                target=context.target,
                branch=context.branch,
                ownership=("detached", candidate_head, final_head),
                completed=attached,
                run=context.run,
                lease=lease,
                failure_gap="lane_start_worktree_binding_failed",
            )
        )
    if not rollback.exact_worktree(
        context.repo,
        target=context.target,
        branch=context.branch,
        head=final_head,
        run=context.run,
    ):
        return rollback.rollback_lane_start(
            rollback.LaneStartRollback(
                repo=context.repo,
                target=context.target,
                branch=context.branch,
                ownership=(context.branch, final_head, final_head),
                completed=failed_process("lane_start_worktree_binding_mismatch"),
                run=context.run,
                lease=lease,
                failure_gap="lane_start_worktree_binding_mismatch",
            )
        )
    return started_lane_report(context, base_head=candidate_head, head=final_head, lease=lease)


def prepare_lane_start_carrier(
    context: LaneStartContext,
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    """Create and initialize the detached carrier without minting a lane ref."""
    candidate_head = str(context.candidate["head"])
    if gap := lane_start_drift_gap(
        repo=context.repo,
        candidate=context.candidate,
        source_root=context.source_root,
        source_branch=context.source_branch,
        source_head=context.source_head,
        run=context.run,
    ):
        return failed_process(gap), candidate_head
    completed = context.run(
        context.repo,
        "worktree",
        "add",
        "--detach",
        context.target.as_posix(),
        candidate_head,
        check=False,
    )
    if completed.returncode != 0 or not rollback.exact_worktree(
        context.repo,
        target=context.target,
        branch="detached",
        head=candidate_head,
        run=context.run,
    ):
        return completed, candidate_head
    return initialize_lane_carrier(context)


def initialize_lane_carrier(
    context: LaneStartContext,
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    """Materialize and validate one deterministic initialization HEAD."""
    candidate_head = str(context.candidate["head"])
    failure, tree = materialize_source_carrier(
        target=context.target,
        source_root=context.source_root,
        source_head=context.source_head,
        change_id=context.source_change_id,
        run=context.run,
    )
    if failure is None:
        gap = lane_start_drift_gap(
            repo=context.repo,
            candidate=context.candidate,
            source_root=context.source_root,
            source_branch=context.source_branch,
            source_head=context.source_head,
            run=context.run,
        )
        failure = failed_process(gap) if gap else None
    metadata = (
        commit_metadata(context.repo, context.source_head, run=context.run)
        if failure is None
        else None
    )
    if failure is None and metadata is None:
        failure = failed_process("lane_start_source_commit_metadata_unreadable")
    final_head = candidate_head
    if failure is None:
        committed = context.run(
            context.target,
            "commit-tree",
            tree,
            "-p",
            candidate_head,
            "-m",
            f"materialize {context.source_change_id} carrier",
            check=False,
            env=metadata,
        )
        failure = committed if committed.returncode != 0 else None
        final_head = committed.stdout.strip() if failure is None else candidate_head
    if failure is None and not final_head:
        failure = failed_process("lane_start_final_head_missing")
    if failure is None:
        gap = lane_start_drift_gap(
            repo=context.repo,
            candidate=context.candidate,
            source_root=context.source_root,
            source_branch=context.source_branch,
            source_head=context.source_head,
            run=context.run,
        )
        failure = failed_process(gap) if gap else None
    if failure is None and active_change_names_in_ref(context.target, final_head) != [
        context.source_change_id
    ]:
        failure = failed_process("lane_start_active_change_carrier_mismatch")
    if failure is None:
        failure = lane_start_commitment_failure(
            target=context.target,
            final_head=final_head,
            source_change_id=context.source_change_id,
        )
    return failure, final_head


def materialize_source_carrier(
    *,
    target: Path,
    source_root: Path,
    source_head: str,
    change_id: str,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    """Copy one safe source Change carrier into a detached target tree."""
    relative = f"openspec/changes/{change_id}"
    entries = tree_entries(source_root, source_head, relative, run=run)
    if entries is None:
        return failed_process("source_change_carrier_missing"), ""
    if any(
        mode not in {"100644", "100755"} or kind != "blob" for mode, kind, _oid, _path in entries
    ):
        return failed_process("source_change_carrier_unsafe"), ""
    restored = run(target, "checkout", source_head, "--", relative, check=False)
    if restored.returncode != 0:
        return restored, ""
    target_tree = run(target, "write-tree", check=False)
    if target_tree.returncode != 0:
        return target_tree, ""
    if tree_entries(target, target_tree.stdout.strip(), relative, run=run) != entries:
        return failed_process("source_change_carrier_materialization_mismatch"), ""
    return None, target_tree.stdout.strip()


def lane_start_commitment_failure(
    *, target: Path, final_head: str, source_change_id: str
) -> subprocess.CompletedProcess[str] | None:
    """Return a failure when the materialized Commitment is not exact."""
    try:
        commitment = load_openspec_commitment(
            target,
            change_id=source_change_id,
            tree_ref=final_head,
        )
    except ValueError as exc:
        return failed_process(str(exc))
    if commitment.id != f"change:{source_change_id}":
        return failed_process("lane_start_commitment_identity_mismatch")
    return None


def lane_start_drift_gap(
    *,
    repo: Path,
    candidate: dict[str, object],
    source_root: Path,
    source_branch: str,
    source_head: str,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    """Return the first observed source or candidate movement during lane start."""
    candidate_branch = str(candidate["branch"])
    candidate_head = str(candidate["head"])
    if ref_head(repo, candidate_branch) != candidate_head:
        return "candidate_head_changed_during_lane_start"
    candidate_path = Path(str(candidate["worktree_path"]))
    if run(candidate_path, "rev-parse", "HEAD", check=False).stdout.strip() != candidate_head:
        return "candidate_worktree_head_changed_during_lane_start"
    if ref_head(source_root, source_branch) != source_head:
        return "source_head_changed_during_lane_start"
    if run(source_root, "rev-parse", "HEAD", check=False).stdout.strip() != source_head:
        return "source_worktree_head_changed_during_lane_start"
    return ""


def failed_process(message: str) -> subprocess.CompletedProcess[str]:
    """Build one synthetic failed process for a pre-command lane-start check."""
    return subprocess.CompletedProcess(("materialize",), 1, "", message)


def commit_metadata(
    repo: Path, commit: str, *, run: Callable[..., subprocess.CompletedProcess[str]]
) -> dict[str, str] | None:
    """Return exact source metadata for a deterministic initialization commit."""
    metadata = run(
        repo,
        "show",
        "-s",
        "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI",
        commit,
        check=False,
    )
    if metadata.returncode != 0:
        return None
    try:
        author, author_email, authored_at, committer, committer_email, committed_at = (
            metadata.stdout.rstrip("\n").split("\0")
        )
    except ValueError:
        return None
    return {
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_AUTHOR_DATE": authored_at,
        "GIT_COMMITTER_NAME": committer,
        "GIT_COMMITTER_EMAIL": committer_email,
        "GIT_COMMITTER_DATE": committed_at,
    }


def tree_entries(
    root: Path,
    tree_ref: str,
    relative: str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[tuple[str, str, str, str], ...] | None:
    """Return the exact blobs beneath one tree-relative carrier path."""
    completed = run(root, "ls-tree", "-r", "-z", tree_ref, "--", relative, check=False)
    if completed.returncode != 0:
        return None
    entries: list[tuple[str, str, str, str]] = []
    for record in completed.stdout.split("\0"):
        if not record:
            continue
        try:
            metadata, path = record.split("\t", 1)
            mode, kind, oid = metadata.split()
        except ValueError:
            return None
        entries.append((mode, kind, oid, path))
    return tuple(entries) or None


def started_lane_report(
    context: LaneStartContext,
    *,
    base_head: str,
    head: str,
    lease: dict[str, object],
) -> dict[str, object]:
    """Build the receipt for an exact, leased, linked Work Lane."""
    return {
        "ok": True,
        "state": "started",
        "branch": context.branch,
        "base": context.policy.candidate_branch,
        "base_head": base_head,
        "head": head,
        "path": context.target.as_posix(),
        "source_root": context.source_root.resolve().as_posix(),
        "source_head": context.source_head,
        "source_change_id": context.source_change_id,
        "source_commitment_digest": context.base_commitment_digest,
        "materialized_carrier": f"openspec/changes/{context.source_change_id}",
        "worktree": started_worktree(branch=context.branch, path=context.target, run=context.run),
        "holder_ref": context.holder_ref,
        "base_commitment_digest": context.base_commitment_digest,
        "lease": lease,
        "runner_bootstrap": runner_bootstrap(context.target),
        "required_gaps": [],
    }


def started_worktree(
    *, branch: str, path: Path, run: Callable[..., subprocess.CompletedProcess[str]]
) -> dict[str, str]:
    """Return the linked-worktree receipt for a started lane."""
    head = run(path, "rev-parse", "HEAD").stdout.strip()
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": head,
        "role": ROLE_WORK_LANE,
        "worktree_binding": "linked",
    }


def runner_bootstrap(target: Path) -> dict[str, str]:
    """Return the non-mutating source-bound runner contract for a new lane."""
    resolved = target.resolve().as_posix()
    return {
        "command": "tools/ci/scripts/run-ethos-lane.sh",
        "project_environment": "build/runtime/venv",
        "environment_scope": "checkout",
        "uv_cache": "host_or_ci_content_addressed",
        "cache_scope": "host_or_ci",
        "next_action": f"cd {resolved} && tools/ci/scripts/run-ethos-lane.sh status --json",
    }
