from __future__ import annotations

import os
import re
import subprocess
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import NamedTuple
from typing import cast

from ethos.adapters.repo.change_contract import load_change_contract
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git import same_git_repository
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.repository.openspec.audit import active_change_names_in_ref


class _LaneStartContext(NamedTuple):
    """Immutable inputs whose equality defines one lane-start saga."""

    repo: Path
    policy: BranchRolePolicy
    branch: str
    target: Path
    holder_ref: str
    base_change_contract_digest: str
    candidate: dict[str, object]
    source_root: Path
    source_change_id: str
    source_head: str
    source_branch: str


def slug(name: str) -> str:
    """Normalize one human lane name into its branch/path component."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip().lower()).strip("-") or "work"


def canonical_lane_identity(name: str, *, observed_at: datetime) -> tuple[str, str]:
    """Return the repository-family lane id and Work Lane branch."""
    lane_id = f"{observed_at.astimezone(UTC):%Y%m%d}-{slug(name)}"
    return lane_id, f"work/{lane_id}"


def canonical_lane_path(repo: Path, lane_id: str) -> Path:
    """Return the canonical linked-worktree path for one lane id."""
    return repo.parent / f"{repo.name}-worktrees" / lane_id


def default_candidate_path(repo: Path, candidate_branch: str) -> Path:
    """Return the default local worktree path for a branch role."""
    return repo.with_name(f"{repo.name}-{slug(candidate_branch)}")


def utc_now() -> datetime:
    return datetime.now(UTC)


def start_work_lane(
    *,
    root: Path,
    name: str,
    source_root: Path | None = None,
    path: Path | None = None,
    holder_ref: str,
    apply: bool = False,
) -> dict[str, object]:
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    branch, target, profile_block = _lane_start_target(repo, policy, name=name, path=path)
    if profile_block:
        return profile_block
    try:
        normalized_holder_ref = HolderRef.parse(holder_ref).serialize()
    except ValueError:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "required_gaps": ["holder_ref_invalid"],
        }
    if not apply:
        return _planned_lane_start(branch=branch, target=target)
    candidate, admission_block = _admit_lane_start(repo, branch=branch, target=target)
    if admission_block:
        return admission_block
    source, contract_block = _lane_start_contract(
        repo, branch=branch, target=target, source_root=source_root
    )
    if contract_block:
        return contract_block
    source_root, source_change_id, base_digest, source_head, source_branch = source
    return _create_lane_start_carrier(
        _LaneStartContext(
            repo=repo,
            policy=policy,
            branch=branch,
            target=target,
            holder_ref=normalized_holder_ref,
            base_change_contract_digest=base_digest,
            candidate=candidate,
            source_root=source_root,
            source_change_id=source_change_id,
            source_head=source_head,
            source_branch=source_branch,
        )
    )


def _admit_lane_start(
    repo: Path, *, branch: str, target: Path
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Require a clean accepted root, clean candidate, and absent carrier."""
    status = workspace_status(repo)
    if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]:
        return {}, _blocked_lane_start(
            branch,
            target,
            "lane_start_requires_clean_accepted_root",
            role=status["role"],
            dirty=status["dirty"],
        )
    candidate = cast("dict[str, object]", status["candidate"])
    gap, extra = _candidate_lane_start_gap(repo, candidate)
    if gap:
        return {}, _blocked_lane_start(branch, target, gap, **extra)
    if gap := _lane_start_carrier_gap(repo, target=target, branch=branch):
        return {}, _blocked_lane_start(branch, target, gap)
    return candidate, None


def _candidate_lane_start_gap(
    repo: Path, candidate: dict[str, object]
) -> tuple[str, dict[str, object]]:
    """Return the first candidate fact that makes lane start unsafe."""
    exists = bool(candidate["exists"])
    worktree_exists = bool(candidate["worktree_exists"])
    if not exists or not worktree_exists:
        gap = "candidate_branch_missing" if not exists else "candidate_worktree_missing"
        return gap, {}
    candidate_path = Path(str(candidate["worktree_path"]))
    candidate_branch = str(candidate["branch"])
    candidate_head = str(candidate["head"])
    checks = (
        ("candidate_worktree_dirty", bool(changed_paths(candidate_path))),
        (
            "candidate_head_changed_during_lane_start",
            ref_head(repo, candidate_branch) != candidate_head,
        ),
        (
            "candidate_worktree_head_changed_during_lane_start",
            run_git(candidate_path, "rev-parse", "HEAD", check=False).stdout.strip()
            != candidate_head,
        ),
    )
    if gap := next((name for name, failed in checks if failed), ""):
        return gap, {}
    active_changes = active_change_names_in_ref(repo, candidate_branch)
    return (
        ("candidate_active_change_carrier_present", {"candidate_active_changes": active_changes})
        if active_changes
        else ("", {})
    )


def _create_lane_start_carrier(context: _LaneStartContext) -> dict[str, object]:
    """Initialize detached content, acquire its Lease, then bind the lane ref."""
    candidate_head = str(context.candidate["head"])
    prepared, final_head = _prepare_lane_start_carrier(context)
    if prepared is not None:
        failure_gap = (
            "worktree_add_failed"
            if not os.path.lexists(context.target)
            else prepared.stderr.strip() or "lane_start_initialization_failed"
        )
        return _abort_lane_start(
            context,
            ownership=("detached", candidate_head, ""),
            completed=prepared,
            failure_gap=failure_gap,
        )
    try:
        issued_at = datetime.now(UTC)
        lease = acquire_lease(
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
                base_change_contract_digest=context.base_change_contract_digest,
                path_scope=(),
            ),
        )
    except (RuntimeError, ValueError) as exc:
        return _abort_lane_start(
            context,
            ownership=("detached", candidate_head, ""),
            completed=_failed_process(str(exc)),
            failure_gap=str(exc),
        )
    created_ref = run_git(
        context.repo,
        "update-ref",
        f"refs/heads/{context.branch}",
        final_head,
        "",
        check=False,
        env={"ETHOS_ACTOR": context.holder_ref},
    )
    if created_ref.returncode != 0 or ref_head(context.repo, context.branch) != final_head:
        owned_ref_head = final_head if created_ref.returncode == 0 else ""
        return _abort_lane_start(
            context,
            ownership=("detached", candidate_head, owned_ref_head),
            lease=lease,
            completed=created_ref,
            failure_gap="lane_start_ref_creation_failed",
        )
    attached = run_git(
        context.target,
        "symbolic-ref",
        "HEAD",
        f"refs/heads/{context.branch}",
        check=False,
    )
    if attached.returncode != 0:
        return _abort_lane_start(
            context,
            ownership=("detached", candidate_head, final_head),
            lease=lease,
            completed=attached,
            failure_gap="lane_start_worktree_binding_failed",
        )
    if not _exact_worktree(
        context.repo,
        target=context.target,
        branch=context.branch,
        head=final_head,
    ):
        return _abort_lane_start(
            context,
            ownership=(context.branch, final_head, final_head),
            lease=lease,
            completed=_failed_process("lane_start_worktree_binding_mismatch"),
            failure_gap="lane_start_worktree_binding_mismatch",
        )
    return _started_lane_report(
        context,
        base_head=candidate_head,
        head=final_head,
        lease=lease,
    )


def _prepare_lane_start_carrier(
    context: _LaneStartContext,
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    """Create and initialize the detached carrier without minting a lane ref."""
    candidate_head = str(context.candidate["head"])
    if gap := _lane_start_drift_gap(
        repo=context.repo,
        candidate=context.candidate,
        source_root=context.source_root,
        source_branch=context.source_branch,
        source_head=context.source_head,
    ):
        return _failed_process(gap), candidate_head
    completed = _create_detached_worktree(
        context.repo,
        target=context.target,
        candidate_head=candidate_head,
    )
    if completed.returncode != 0 or not _exact_worktree(
        context.repo,
        target=context.target,
        branch="detached",
        head=candidate_head,
    ):
        return completed, candidate_head
    return _initialize_lane_carrier(
        target=context.target,
        source_root=context.source_root,
        source_head=context.source_head,
        source_change_id=context.source_change_id,
        candidate=context.candidate,
        source_branch=context.source_branch,
        repo=context.repo,
    )


def _create_detached_worktree(
    repo: Path, *, target: Path, candidate_head: str
) -> subprocess.CompletedProcess[str]:
    """Create a detached destination without exposing an unleased Work Lane ref."""
    return run_git(
        repo,
        "worktree",
        "add",
        "--detach",
        target.as_posix(),
        candidate_head,
        check=False,
    )


def _initialize_lane_carrier(
    *,
    repo: Path,
    target: Path,
    source_root: Path,
    source_head: str,
    source_change_id: str,
    candidate: dict[str, object],
    source_branch: str,
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    """Materialize and validate one deterministic initialization HEAD."""
    candidate_head = str(candidate["head"])
    final_head = candidate_head
    failure, tree = _materialize_source_carrier(
        target=target,
        source_root=source_root,
        source_head=source_head,
        change_id=source_change_id,
    )
    if failure is None:
        gap = _lane_start_drift_gap(
            repo=repo,
            candidate=candidate,
            source_root=source_root,
            source_branch=source_branch,
            source_head=source_head,
        )
        failure = _failed_process(gap) if gap else None
    metadata = _commit_metadata(repo, source_head) if failure is None else None
    if failure is None and metadata is None:
        failure = _failed_process("lane_start_source_commit_metadata_unreadable")
    if failure is None:
        committed = run_git(
            target,
            "commit-tree",
            tree,
            "-p",
            candidate_head,
            "-m",
            f"materialize {source_change_id} carrier",
            check=False,
            env=metadata,
        )
        failure = committed if committed.returncode != 0 else None
        final_head = committed.stdout.strip() if failure is None else candidate_head
    if failure is None and not final_head:
        failure = _failed_process("lane_start_final_head_missing")
    if failure is None:
        gap = _lane_start_drift_gap(
            repo=repo,
            candidate=candidate,
            source_root=source_root,
            source_branch=source_branch,
            source_head=source_head,
        )
        failure = _failed_process(gap) if gap else None
    if failure is None and active_change_names_in_ref(target, final_head) != [source_change_id]:
        failure = _failed_process("lane_start_active_change_carrier_mismatch")
    if failure is None:
        failure = _lane_start_contract_failure(
            target=target,
            final_head=final_head,
            source_change_id=source_change_id,
        )
    return failure, final_head


def _lane_start_contract_failure(
    *, target: Path, final_head: str, source_change_id: str
) -> subprocess.CompletedProcess[str] | None:
    try:
        contract = load_change_contract(target, tree_ref=final_head, require_active=True)
    except ValueError as exc:
        return _failed_process(str(exc))
    if contract.id != f"change:{source_change_id}":
        return _failed_process("lane_start_change_contract_identity_mismatch")
    return None


def _materialize_source_carrier(
    *, target: Path, source_root: Path, source_head: str, change_id: str
) -> tuple[subprocess.CompletedProcess[str] | None, str]:
    relative = f"openspec/changes/{change_id}"
    entries = _tree_entries(source_root, source_head, relative)
    if entries is None:
        return _failed_process("source_change_carrier_missing"), ""
    if any(
        mode not in {"100644", "100755"} or kind != "blob" for mode, kind, _oid, _path in entries
    ):
        return _failed_process("source_change_carrier_unsafe"), ""
    restored = run_git(target, "checkout", source_head, "--", relative, check=False)
    if restored.returncode != 0:
        return restored, ""
    target_tree = run_git(target, "write-tree", check=False)
    if target_tree.returncode != 0:
        return target_tree, ""
    if _tree_entries(target, target_tree.stdout.strip(), relative) != entries:
        return _failed_process("source_change_carrier_materialization_mismatch"), ""
    return None, target_tree.stdout.strip()


def _commit_metadata(repo: Path, commit: str) -> dict[str, str] | None:
    """Return exact source metadata for a deterministic initialization commit."""
    metadata = run_git(
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


def _tree_entries(
    root: Path, tree_ref: str, relative: str
) -> tuple[tuple[str, str, str, str], ...] | None:
    completed = run_git(root, "ls-tree", "-r", "-z", tree_ref, "--", relative, check=False)
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


def _lane_start_drift_gap(
    *,
    repo: Path,
    candidate: dict[str, object],
    source_root: Path,
    source_branch: str,
    source_head: str,
) -> str:
    candidate_branch = str(candidate["branch"])
    candidate_head = str(candidate["head"])
    if ref_head(repo, candidate_branch) != candidate_head:
        return "candidate_head_changed_during_lane_start"
    candidate_path = Path(str(candidate["worktree_path"]))
    if run_git(candidate_path, "rev-parse", "HEAD", check=False).stdout.strip() != candidate_head:
        return "candidate_worktree_head_changed_during_lane_start"
    if ref_head(source_root, source_branch) != source_head:
        return "source_head_changed_during_lane_start"
    if run_git(source_root, "rev-parse", "HEAD", check=False).stdout.strip() != source_head:
        return "source_worktree_head_changed_during_lane_start"
    return ""


def _failed_process(message: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(("materialize",), 1, "", message)


def _started_lane_report(
    context: _LaneStartContext,
    *,
    base_head: str,
    head: str,
    lease: dict[str, object],
) -> dict[str, object]:
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
        "source_change_contract_digest": context.base_change_contract_digest,
        "materialized_carrier": f"openspec/changes/{context.source_change_id}",
        "worktree": _started_worktree(branch=context.branch, path=context.target),
        "holder_ref": context.holder_ref,
        "base_change_contract_digest": context.base_change_contract_digest,
        "lease": lease,
        "runner_bootstrap": _runner_bootstrap(context.target),
        "required_gaps": [],
    }


def _planned_lane_start(*, branch: str, target: Path) -> dict[str, object]:
    return {
        "ok": True,
        "state": "planned",
        "branch": branch,
        "path": target.as_posix(),
        "runner_bootstrap": _runner_bootstrap(target),
        "required_gaps": [],
    }


def _blocked_lane_start(
    branch: str, target: Path, *gaps: str, **extra: object
) -> dict[str, object]:
    return {
        "ok": False,
        "state": "blocked",
        "branch": branch,
        "path": target.as_posix(),
        **extra,
        "required_gaps": list(gaps),
    }


def _lane_start_target(
    repo: Path, policy: BranchRolePolicy, *, name: str, path: Path | None
) -> tuple[str, Path, dict[str, object] | None]:
    if not getattr(policy, "repository_family_worktrees", False):
        branch = policy.work_branch(slug(name))
        return branch, (path or default_candidate_path(repo, branch)).resolve(), None
    lane_id, branch = canonical_lane_identity(name, observed_at=utc_now())
    if policy.work_branch_prefix != "work/":
        return (
            branch,
            Path(),
            {
                "ok": False,
                "state": "blocked",
                "branch": branch,
                "required_gaps": ["repository_family_profile_requires_work_branch_prefix"],
            },
        )
    target = canonical_lane_path(repo, lane_id).resolve()
    if path is not None and path.resolve() != target:
        return (
            branch,
            target,
            {
                "ok": False,
                "state": "blocked",
                "branch": branch,
                "path": path.resolve().as_posix(),
                "required_gaps": ["work_lane_path_not_canonical"],
            },
        )
    return branch, target, None


def _abort_lane_start(
    context: _LaneStartContext,
    *,
    ownership: tuple[str, str, str],
    completed: subprocess.CompletedProcess[str],
    lease: dict[str, object] | None = None,
    failure_gap: str = "worktree_add_failed",
) -> dict[str, object]:
    """Compensate only the exact carrier and lease created by this start saga."""
    repo, target, branch = context.repo, context.target, context.branch
    worktree_branch, worktree_head, owned_ref_head = ownership
    observed_worktree = _worktree_at(repo, target=target, branch=worktree_branch)
    worktree = observed_worktree is not None and observed_worktree == worktree_head
    target_exists = os.path.lexists(target)
    worktree_removed = not worktree and not target_exists
    ref_removed = False
    gap = ""

    def retained(gap: str) -> dict[str, object]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            "stderr": completed.stderr.strip() or "lane_start_postcondition_failed",
            "carrier_cleanup": {
                "worktree_removed": worktree_removed,
                "ref_removed": ref_removed,
            },
            "lease_state": "retained" if lease else "not_acquired",
            "required_gaps": ["lane_creation_compensation_failed", gap],
        }

    current_head = ref_head(repo, branch)
    path_ownership_unknown = target_exists and observed_worktree is None
    gap = (
        "lane_start_target_path_ownership_unknown"
        if path_ownership_unknown
        else "lane_start_target_ref_ownership_unknown"
        if observed_worktree is None and current_head
        else ""
    )
    if worktree and not gap:
        worktree_removed = _remove_lane_start_worktree(
            repo,
            target=target,
            branch=worktree_branch,
            head=worktree_head,
        )
        if not worktree_removed:
            gap = "lane_start_worktree_cleanup_failed"
    current_head = ref_head(repo, branch) if not gap else current_head
    if not gap and current_head and current_head != owned_ref_head:
        gap = "lane_start_ref_changed"
    ref_removed = not current_head if not gap else False
    if not gap and current_head:
        deleted = run_git(
            repo, "update-ref", "-d", f"refs/heads/{branch}", owned_ref_head, check=False
        )
        ref_removed = deleted.returncode == 0 and not ref_head(repo, branch)
    if not ref_removed:
        gap = gap or "lane_start_ref_cleanup_failed"
    try:
        if not gap and lease:
            revoke_lease(
                state_database(repo),
                request=LeaseOperationRequest(
                    operation="lane_start_compensation",
                    branch=branch,
                    holder_ref=str(lease["holder_ref"]),
                    lease_id=str(lease["lease_id"]),
                    expected_epoch=integer_value(lease["epoch"]),
                    expect_head=str(lease["expected_head"]),
                    expected_expires_at=str(lease["expires_at"]),
                    expected_payload_sha256=str(lease["payload_sha256"]),
                    apply=True,
                ),
            )
    except (RuntimeError, ValueError) as exc:
        gap = str(exc)
    if gap:
        return retained(gap)
    return {
        "ok": False,
        "state": "blocked",
        "branch": branch,
        "path": target.as_posix(),
        "stderr": completed.stderr.strip() or "lane_start_postcondition_failed",
        "carrier_cleanup": {"worktree_removed": True, "ref_removed": True},
        "lease_state": "revoked" if lease else "not_acquired",
        "required_gaps": [failure_gap],
    }


def _remove_lane_start_worktree(repo: Path, *, target: Path, branch: str, head: str) -> bool:
    """Remove only the exact detached or bound carrier created by lane start."""
    if os.path.lexists(target):
        restored = run_git(target, "reset", "--hard", head, check=False)
        cleaned = run_git(target, "clean", "-fd", check=False)
        if restored.returncode != 0 or cleaned.returncode != 0:
            return False
    removed = run_git(repo, "worktree", "remove", "--force", target.as_posix(), check=False)
    return (
        removed.returncode == 0
        and not os.path.lexists(target)
        and not _exact_worktree(repo, target=target, branch=branch, head=head)
    )


def _lane_start_carrier_gap(repo: Path, *, target: Path, branch: str) -> str:
    if os.path.lexists(target):
        return "lane_start_target_path_exists"
    return "lane_start_target_ref_exists" if ref_head(repo, branch) else ""


def _exact_worktree(repo: Path, *, target: Path, branch: str, head: str) -> bool:
    return _worktree_at(repo, target=target, branch=branch) == head


def _worktree_at(repo: Path, *, target: Path, branch: str) -> str | None:
    listed = run_git(repo, "worktree", "list", "--porcelain", check=False)
    if listed.returncode != 0:
        return None
    for block in listed.stdout.split("\n\n"):
        record = {
            parts[0]: parts[1] if len(parts) > 1 else ""
            for line in block.splitlines()
            if line
            for parts in (line.split(" ", 1),)
        }
        path = record.get("worktree", "")
        observed_branch = (
            record.get("branch", "").removeprefix("refs/heads/")
            if "branch" in record
            else "detached"
            if "detached" in record
            else ""
        )
        if path and Path(path).resolve() == target and observed_branch == branch:
            return record.get("HEAD", "")
    return None


def _lane_start_contract(
    repo: Path,
    *,
    branch: str,
    target: Path,
    source_root: Path | None,
) -> tuple[tuple[Path, str, str, str, str], dict[str, object] | None]:
    """Bind lane start to one exact active ChangeContract in a source Work Lane."""
    source = Path()
    source_branch = ""
    source_head = ""
    change_id = ""
    contract_digest = ""
    gap = "source_root_required" if source_root is None else ""
    if not gap and source_root is not None:
        try:
            source = repository_root(source_root)
        except (OSError, subprocess.CalledProcessError):
            gap = "source_work_lane_invalid"
    if not gap and (source.resolve() == repo.resolve() or not same_git_repository(repo, source)):
        gap = "source_work_lane_invalid"
    if not gap:
        source_status = workspace_status(source)
        source_branch = str(source_status.get("branch") or "")
        source_lease = leases_by_branch(source).get(source_branch, {})
        source_head = str(source_status.get("head") or "")
        checks = (
            (
                "source_work_lane_invalid",
                source_status["role"] != ROLE_WORK_LANE or bool(source_status["dirty"]),
            ),
            ("source_work_lane_invalid", source_lease.get("lease_state") != "valid"),
            (
                "source_lease_head_mismatch",
                str(source_lease.get("expected_head") or "") != source_head,
            ),
            (
                "source_lease_contract_unbound",
                str(source_lease.get("contract_binding") or "") != "bound",
            ),
        )
        gap = next((name for name, failed in checks if failed), "")
    if not gap:
        try:
            contract = load_change_contract(source, tree_ref=source_head, require_active=True)
        except ValueError as exc:
            gap = str(exc)
        else:
            change_id = contract.id.removeprefix("change:")
            contract_digest = contract.digest()
    if not gap and _tree_entries(source, source_head, f"openspec/changes/{change_id}") is None:
        gap = "source_change_carrier_missing"
    source_contract = (source, change_id, contract_digest, source_head, source_branch)
    return (
        ((Path(), "", "", "", ""), _blocked_lane_start(branch, target, gap))
        if gap
        else (source_contract, None)
    )


def _started_worktree(*, branch: str, path: Path) -> dict[str, str]:
    head = run_git(path, "rev-parse", "HEAD").stdout.strip()
    return {
        "branch": branch,
        "path": path.as_posix(),
        "head": head,
        "role": ROLE_WORK_LANE,
        "worktree_binding": "linked",
    }


def _runner_bootstrap(target: Path) -> dict[str, str]:
    """Return the non-mutating source-bound runner contract for a new lane."""
    resolved = target.resolve().as_posix()
    return {
        "command": "tools/ci/scripts/run-ethos-lane.sh",
        "project_environment": "build/runtime/venv",
        "environment_scope": "checkout",
        "uv_cache": "host_or_ci_content_addressed",
        "cache_scope": "host_or_ci",
        "next_action": (f"cd {resolved} && tools/ci/scripts/run-ethos-lane.sh status --json"),
    }
