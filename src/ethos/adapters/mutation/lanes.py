from __future__ import annotations

import os
import re
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.lane_start_carrier import LaneStartContext
from ethos.adapters.mutation.lane_start_carrier import create_lane_start_carrier
from ethos.adapters.mutation.lane_start_carrier import runner_bootstrap
from ethos.adapters.mutation.lane_start_carrier import tree_entries
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.openspec.profile import active_change_names_in_ref
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git import same_git_repository
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import HolderRef


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
    """Return the current UTC timestamp for repository-family lane identities."""
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
    """Plan or create one leased Work Lane from an active source carrier."""
    repo = repository_root(root)
    policy = load_branch_role_policy(repo)
    branch, target, profile_block = lane_start_target(repo, policy, name=name, path=path)
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
        return planned_lane_start(branch=branch, target=target)
    candidate, admission_block = admit_lane_start(repo, branch=branch, target=target)
    if admission_block:
        return admission_block
    source, contract_block = lane_start_contract(
        repo, branch=branch, target=target, source_root=source_root
    )
    if contract_block:
        return contract_block
    source_root, source_change_id, base_digest, source_head, source_branch = source
    return create_lane_start_carrier(
        LaneStartContext(
            repo=repo,
            policy=policy,
            branch=branch,
            target=target,
            holder_ref=normalized_holder_ref,
            base_commitment_digest=base_digest,
            candidate=candidate,
            source_root=source_root,
            source_change_id=source_change_id,
            source_head=source_head,
            source_branch=source_branch,
            run=run_git,
            acquire=acquire_lease,
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
    active_changes = active_change_names_in_ref(repo, candidate_branch)
    return (
        ("candidate_active_change_carrier_present", {"candidate_active_changes": active_changes})
        if active_changes
        else ("", {})
    )


def lane_start_target(
    repo: Path, policy: BranchRolePolicy, *, name: str, path: Path | None
) -> tuple[str, Path, dict[str, object] | None]:
    """Resolve the only branch and target path admitted for a lane start."""
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


def lane_start_contract(
    repo: Path,
    *,
    branch: str,
    target: Path,
    source_root: Path | None,
) -> tuple[tuple[Path, str, str, str, str], dict[str, object] | None]:
    """Bind lane start to one exact active Commitment in a source Work Lane."""
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
            contract = load_openspec_commitment(source, tree_ref=source_head)
        except ValueError as exc:
            gap = str(exc)
        else:
            change_id = contract.id.removeprefix("change:")
            contract_digest = str(source_lease.get("base_commitment_digest") or "")
    if (
        not gap
        and tree_entries(source, source_head, f"openspec/changes/{change_id}", run=run_git) is None
    ):
        gap = "source_change_carrier_missing"
    source_contract = (source, change_id, contract_digest, source_head, source_branch)
    return (
        ((Path(), "", "", "", ""), blocked_lane_start(branch, target, gap))
        if gap
        else (source_contract, None)
    )


def lane_start_carrier_gap(repo: Path, *, target: Path, branch: str) -> str:
    """Return a target collision gap before lane-start effects begin."""
    if os.path.lexists(target):
        return "lane_start_target_path_exists"
    return "lane_start_target_ref_exists" if ref_head(repo, branch) else ""


def planned_lane_start(*, branch: str, target: Path) -> dict[str, object]:
    """Build the no-effect lane-start plan receipt."""
    return {
        "ok": True,
        "state": "planned",
        "branch": branch,
        "path": target.as_posix(),
        "runner_bootstrap": runner_bootstrap(target),
        "required_gaps": [],
    }


def blocked_lane_start(branch: str, target: Path, *gaps: str, **extra: object) -> dict[str, object]:
    """Build a blocked lane-start receipt with all verified gaps."""
    return {
        "ok": False,
        "state": "blocked",
        "branch": branch,
        "path": target.as_posix(),
        **extra,
        "required_gaps": list(gaps),
    }
