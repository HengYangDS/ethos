from __future__ import annotations

import os
import re
import subprocess
from datetime import UTC
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.carriers import openspec_carrier_gaps
from ethos.adapters.mutation.lane_start_carrier import LaneStartContext
from ethos.adapters.mutation.lane_start_carrier import create_lane_start_carrier
from ethos.adapters.mutation.lane_start_receipt import runner_bootstrap
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git import same_git_repository
from ethos.adapters.repo.hook_runtime_install import require_runtime_wheel_provenance
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import replace_lease_authority
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.semantic import load_commitment_file


def slug(name: str) -> str:
    """Normalize one human lane name into its branch/path component."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip().lower()).strip("-") or "work"


def canonical_lane_identity(name: str, *, observed_at: datetime) -> tuple[str, str]:
    """Return the canonical sibling lane id and Work Lane branch."""
    lane_id = f"{observed_at.astimezone(UTC):%Y%m%d}-{slug(name)}"
    return lane_id, f"work/{lane_id}"


def canonical_lane_path(repo: Path, lane_id: str) -> Path:
    """Return the canonical linked-worktree path for one lane id."""
    return repo.parent / f"{repo.name}-worktrees" / lane_id


def default_candidate_path(repo: Path, candidate_branch: str) -> Path:
    """Return the default local worktree path for a branch role."""
    return repo.with_name(f"{repo.name}-{slug(candidate_branch)}")


def utc_now() -> datetime:
    """Return the current UTC timestamp for canonical sibling lane identities."""
    return datetime.now(UTC)


def start_work_lane(
    *,
    root: Path,
    name: str,
    source_root: Path | None = None,
    commitment_path: Path | None = None,
    path: Path | None = None,
    holder_ref: str,
    apply: bool = False,
) -> dict[str, object]:
    """Plan or create one leased Work Lane from an active source carrier."""
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    branch, target, profile_block = lane_start_target(repo, policy, name=name, path=path)
    holder_block: dict[str, object] | None = None
    try:
        normalized_holder_ref = HolderRef.parse(holder_ref).serialize()
    except ValueError:
        normalized_holder_ref = ""
        holder_block = {
            "verdict": "block",
            "state": "blocked",
            "branch": branch,
            "required_gaps": ["holder_ref_invalid"],
        }
    if block := profile_block or holder_block:
        return block
    candidate, admission_block = admit_lane_start(repo, branch=branch, target=target)
    if admission_block:
        return admission_block
    source, commitment_block = lane_start_commitment(
        repo,
        name=name,
        branch=branch,
        target=target,
        holder_ref=normalized_holder_ref,
        source_root=source_root,
        commitment_path=commitment_path,
    )
    if commitment_block:
        return commitment_block
    try:
        require_runtime_wheel_provenance()
    except ValueError as error:
        return blocked_lane_start(branch, target, str(error))
    if not apply:
        return planned_lane_start(branch=branch, target=target)
    guard = local_state_mutation_guard(repo)
    if guard["required_gaps"]:
        commitment_block = blocked_lane_start(
            branch,
            target,
            *cast("list[str]", guard["required_gaps"]),
            next_action=guard["next_action"],
        )
    return commitment_block or _create_started_lane(
        repo=repo,
        policy=policy,
        branch=branch,
        target=target,
        holder_ref=normalized_holder_ref,
        candidate=candidate,
        source=source,
    )


def _create_started_lane(
    *,
    repo: Path,
    policy: BranchRolePolicy,
    branch: str,
    target: Path,
    holder_ref: str,
    candidate: dict[str, object],
    source: tuple[Path, str, str, str, str, str, dict[str, object]],
) -> dict[str, object]:
    (
        source_root,
        source_change_id,
        carrier,
        base_digest,
        source_head,
        source_branch,
        source_lease,
    ) = source
    acquire = (
        partial(
            replace_lease_authority,
            request=lease_operation_request(source_lease),
        )
        if source_lease
        else acquire_lease
    )
    return create_lane_start_carrier(
        LaneStartContext(
            repo=repo,
            policy=policy,
            branch=branch,
            target=target,
            holder_ref=holder_ref,
            base_commitment_digest=base_digest,
            candidate=candidate,
            source_root=source_root,
            source_change_id=source_change_id,
            source_commitment_path=carrier,
            source_head=source_head,
            source_branch=source_branch,
            source_lease=source_lease,
            run=run_git,
            acquire=acquire,
        )
    )


def admit_lane_start(
    repo: Path, *, branch: str, target: Path
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Require a clean accepted root, clean candidate, and absent carrier."""
    status = workspace_status(repo)
    if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]:
        return {}, blocked_lane_start(
            branch,
            target,
            "lane_start_requires_clean_accepted_root",
            role=status["role"],
            dirty=status["dirty"],
        )
    candidate = cast("dict[str, object]", status["candidate"])
    gap, extra = candidate_lane_start_gap(repo, candidate)
    if gap:
        return {}, blocked_lane_start(branch, target, gap, **extra)
    if gap := lane_start_carrier_gap(repo, target=target, branch=branch):
        return {}, blocked_lane_start(branch, target, gap)
    return candidate, None


def candidate_lane_start_gap(
    repo: Path, candidate: dict[str, object]
) -> tuple[str, dict[str, object]]:
    """Return the first candidate fact that makes lane start unsafe."""
    exists = bool(candidate["exists"])
    worktree_exists = bool(candidate["worktree_exists"])
    if not exists or not worktree_exists:
        return ("candidate_branch_missing" if not exists else "candidate_worktree_missing"), {}
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
    gaps = openspec_carrier_gaps(candidate_path, ROLE_CANDIDATE)
    return (gaps[0], {}) if gaps else ("", {})


def lane_start_target(
    repo: Path, policy: BranchRolePolicy, *, name: str, path: Path | None
) -> tuple[str, Path, dict[str, object] | None]:
    """Resolve the only branch and target path admitted for a lane start."""
    if not getattr(policy, "canonical_sibling_worktrees", False):
        branch = policy.work_branch(slug(name))
        return branch, (path or default_candidate_path(repo, branch)).resolve(), None
    lane_id, branch = canonical_lane_identity(name, observed_at=utc_now())
    if policy.work_branch_prefix != "work/":
        return (
            branch,
            Path(),
            {
                "verdict": "block",
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
                "verdict": "block",
                "state": "blocked",
                "branch": branch,
                "path": path.resolve().as_posix(),
                "required_gaps": ["work_lane_path_not_canonical"],
            },
        )
    return branch, target, None


def lane_start_commitment(
    repo: Path,
    *,
    name: str,
    branch: str,
    target: Path,
    holder_ref: str,
    source_root: Path | None,
    commitment_path: Path | None,
) -> tuple[
    tuple[Path, str, str, str, str, str, dict[str, object]],
    dict[str, object] | None,
]:
    """Bind lane start to one exact active Commitment in a source Work Lane."""
    if source_root is not None and commitment_path is not None:
        return blocked_commitment(branch, target, "lane_start_intent_ambiguous")
    if commitment_path is not None:
        return fresh_lane_start_commitment(
            name=name,
            branch=branch,
            target=target,
            commitment_path=commitment_path,
        )
    if source_root is None:
        return blocked_commitment(branch, target, "lane_start_commitment_required")
    return source_lane_start_commitment(
        repo,
        branch=branch,
        target=target,
        holder_ref=holder_ref,
        source_root=source_root,
    )


def fresh_lane_start_commitment(
    *,
    name: str,
    branch: str,
    target: Path,
    commitment_path: Path,
) -> tuple[
    tuple[Path, str, str, str, str, str, dict[str, object]],
    dict[str, object] | None,
]:
    """Validate one explicit Commitment for a fresh atomic Change."""
    change_id = slug(name)
    try:
        commitment = load_commitment_file(commitment_path)
    except (OSError, ValueError):
        return blocked_commitment(branch, target, "lane_start_commitment_invalid")
    if commitment.id != f"change:{change_id}":
        return blocked_commitment(branch, target, "lane_start_commitment_identity_mismatch")
    if commitment.predecessors or commitment.selected_attestations or commitment.dependencies:
        return blocked_commitment(
            branch,
            target,
            "lane_start_successor_commitment_requires_start_change",
        )
    return (
        (
            commitment_path.resolve(),
            change_id,
            f"openspec/changes/{change_id}/commitment.toml",
            commitment.digest(),
            "",
            "",
            {},
        ),
        None,
    )


def source_lane_start_commitment(
    repo: Path,
    *,
    branch: str,
    target: Path,
    holder_ref: str,
    source_root: Path,
) -> tuple[
    tuple[Path, str, str, str, str, str, dict[str, object]],
    dict[str, object] | None,
]:
    """Read one exact active Commitment from a live source Work Lane."""
    source = Path()
    source_branch = ""
    source_head = ""
    change_id = ""
    carrier = ""
    commitment_digest = ""
    source_lease: dict[str, object] = {}
    try:
        source = repository_root(source_root)
    except (OSError, subprocess.CalledProcessError):
        return blocked_commitment(branch, target, "source_work_lane_invalid")
    gap = ""
    if source.resolve() == repo.resolve() or not same_git_repository(repo, source):
        gap = "source_work_lane_invalid"
    if not gap:
        source_branch = run_git(
            source, "symbolic-ref", "--short", "HEAD", check=False
        ).stdout.strip()
        source_head = run_git(source, "rev-parse", "HEAD", check=False).stdout.strip()
        source_lease = observe_lease(state_database(source), source_branch).record()
        checks = (
            (
                "source_work_lane_invalid",
                load_branch_role_policy(source).role_for_branch(source_branch) != ROLE_WORK_LANE
                or bool(changed_paths(source)),
            ),
            ("source_work_lane_invalid", source_lease.get("lease_state") != "valid"),
            (
                "source_lease_holder_mismatch",
                str(source_lease.get("holder_ref") or "") != holder_ref,
            ),
            ("source_lease_handoff_pending", source_lease.get("handoff") is not None),
            (
                "source_lease_head_mismatch",
                str(source_lease.get("expected_head") or "") != source_head,
            ),
        )
        gap = next((name for name, failed in checks if failed), "")
    if not gap:
        try:
            commitment = load_lease_bound_commitment(source, lease=source_lease)
        except ValueError as exc:
            gap = str(exc)
        else:
            change_id = commitment.id.removeprefix("change:")
            carrier = str(source_lease.get("base_commitment_path") or "")
            commitment_digest = commitment.digest()
    source_commitment = (
        source,
        change_id,
        carrier,
        commitment_digest,
        source_head,
        source_branch,
        source_lease,
    )
    return (
        ((Path(), "", "", "", "", "", {}), blocked_lane_start(branch, target, gap))
        if gap
        else (source_commitment, None)
    )


def blocked_commitment(
    branch: str, target: Path, gap: str
) -> tuple[
    tuple[Path, str, str, str, str, str, dict[str, object]],
    dict[str, object],
]:
    """Return one pre-effect lane-start Commitment rejection."""
    return (Path(), "", "", "", "", "", {}), blocked_lane_start(branch, target, gap)


def lease_operation_request(lease: dict[str, object]) -> LeaseOperationRequest:
    """Bind one exact source Lease generation for successor authority transfer."""
    return LeaseOperationRequest(
        operation="lane_start_successor",
        branch=str(lease["lane_ref"]),
        holder_ref=str(lease["holder_ref"]),
        lease_id=str(lease["lease_id"]),
        expected_epoch=integer_value(lease["epoch"]),
        expect_head=str(lease["expected_head"]),
        expected_expires_at=str(lease["expires_at"]),
        expected_payload_sha256=str(lease["payload_sha256"]),
        apply=True,
    )


def lane_start_carrier_gap(repo: Path, *, target: Path, branch: str) -> str:
    """Return a target collision gap before lane-start effects begin."""
    if os.path.lexists(target):
        return "lane_start_target_path_exists"
    return "lane_start_target_ref_exists" if ref_head(repo, branch) else ""


def planned_lane_start(*, branch: str, target: Path) -> dict[str, object]:
    """Build the no-effect lane-start plan receipt."""
    return {
        "verdict": "pass",
        "state": "planned",
        "branch": branch,
        "path": target.as_posix(),
        "runner_bootstrap": runner_bootstrap(target),
        "required_gaps": [],
    }


def blocked_lane_start(branch: str, target: Path, *gaps: str, **extra: object) -> dict[str, object]:
    """Build a blocked lane-start receipt with all verified gaps."""
    return {
        "verdict": "block",
        "state": "blocked",
        "branch": branch,
        "path": target.as_posix(),
        **extra,
        "required_gaps": list(gaps),
    }
