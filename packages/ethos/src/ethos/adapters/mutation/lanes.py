from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import default_candidate_path
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_lifecycle.core import slug
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.lifecycle.effects import update_lease_payload
from ethos.adapters.store.state.lease.projection import active_leases
from ethos.adapters.store.state.lease.projection import integer_value
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.coordination import HolderRef


def start_work_lane(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    root: Path,
    name: str,
    path: Path | None = None,
    holder_ref: str,
    claim_id: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = repo_root(root)
    policy = load_branch_role_policy(repo)
    lane_slug = slug(name)
    branch = policy.work_branch(lane_slug)
    # Default the lane home to the canonical sibling of the accepted root
    # (repo-<branch-slug>) so lanes stop scattering into /tmp; callers may
    # still pin an explicit path.
    target = (path or default_candidate_path(repo, branch)).resolve()

    def blocked(*gaps: str, **extra: object) -> dict[str, object]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            **extra,
            "required_gaps": list(gaps),
        }

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
        return {
            "ok": True,
            "state": "planned",
            "branch": branch,
            "path": target.as_posix(),
            "runner_bootstrap": _runner_bootstrap(target),
            "required_gaps": [],
        }
    status = workspace_status(repo)
    if status["role"] != ROLE_ACCEPTED_ROOT or status["dirty"]:
        return blocked(
            "lane_start_requires_clean_accepted_root",
            role=status["role"],
            dirty=status["dirty"],
        )
    candidate = cast("dict[str, object]", status["candidate"])
    if not candidate["exists"]:
        return blocked("candidate_branch_missing")
    if not candidate["worktree_exists"]:
        return blocked("candidate_worktree_missing")
    candidate_path = Path(str(candidate["worktree_path"]))
    if changed_paths(candidate_path):
        return blocked("candidate_worktree_dirty")
    if gap := _lane_start_carrier_gap(repo, target=target, branch=branch):
        return blocked(gap)
    database = repo / ".ethos" / "state" / "state.sqlite"
    try:
        lease = acquire_lease(
            database,
            subject=branch,
            holder_ref=normalized_holder_ref,
            payload={
                "path": target.as_posix(),
                "branch": branch,
                "claim_id": claim_id or "",
                "expected_head": str(candidate["head"]),
            },
        )
    except (RuntimeError, ValueError) as exc:
        return blocked(str(exc))
    if gap := _lane_start_carrier_gap(repo, target=target, branch=branch):
        return blocked(
            "lane_creation_compensation_failed",
            f"{gap.removesuffix('_exists')}_ownership_unknown",
            lease_state="retained",
        )
    completed = run_git(
        repo,
        "worktree",
        "add",
        "-b",
        branch,
        target.as_posix(),
        str(candidate["head"]),
        check=False,
    )
    if completed.returncode != 0 or not _exact_worktree(
        repo, target=target, branch=branch, head=str(candidate["head"])
    ):
        return _abort_lane_start(
            repo,
            target=target,
            branch=branch,
            lease=lease,
            completed=completed,
        )
    return {
        "ok": True,
        "state": "started",
        "branch": branch,
        "base": policy.candidate_branch,
        "base_head": str(candidate["head"]),
        "path": target.as_posix(),
        "worktree": _started_worktree(branch=branch, path=target),
        "holder_ref": normalized_holder_ref,
        "claim_id": claim_id or "",
        "lease": lease,
        "runner_bootstrap": _runner_bootstrap(target),
        "required_gaps": [],
    }


def _abort_lane_start(
    repo: Path,
    *,
    target: Path,
    branch: str,
    lease: dict[str, object],
    completed,
) -> dict[str, object]:
    """Compensate only the exact carrier and lease created by this start saga."""
    expected_head = str(lease["expected_head"])
    worktree = _exact_worktree(repo, target=target, branch=branch, head=expected_head)
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
            "lease_state": "retained",
            "required_gaps": ["lane_creation_compensation_failed", gap],
        }

    current_head = ref_head(repo, branch)
    if (completed.returncode != 0 and (target_exists or worktree)) or (
        target_exists and not worktree
    ):
        gap = "lane_start_target_path_ownership_unknown"
    elif completed.returncode != 0 and current_head:
        gap = "lane_start_target_ref_ownership_unknown"
    elif worktree:
        arguments = (
            ("worktree", "remove", target.as_posix())
            if target_exists
            else ("worktree", "remove", "--force", target.as_posix())
        )
        cleaned = run_git(repo, *arguments, check=False)
        worktree_removed = (
            cleaned.returncode == 0
            and not os.path.lexists(target)
            and not _exact_worktree(repo, target=target, branch=branch, head=expected_head)
        )
        if not worktree_removed:
            gap = "lane_start_worktree_cleanup_failed"
    current_head = ref_head(repo, branch) if not gap else current_head
    if not gap and current_head and current_head != expected_head:
        gap = "lane_start_ref_changed"
    ref_removed = not current_head if not gap else False
    if not gap and current_head:
        deleted = run_git(
            repo, "update-ref", "-d", f"refs/heads/{branch}", expected_head, check=False
        )
        ref_removed = deleted.returncode == 0 and not ref_head(repo, branch)
    if not ref_removed:
        gap = gap or "lane_start_ref_cleanup_failed"
    try:
        if not gap:
            revoke_lease(
                repo / ".ethos" / "state" / "state.sqlite",
                subject=branch,
                holder_ref=str(lease["holder_ref"]),
                expected_lease_id=str(lease["lease_id"]),
                expected_epoch=integer_value(lease["epoch"]),
                expected_head=str(lease["expected_head"]),
                expected_expires_at=str(lease["expires_at"]),
                expected_payload_sha256=str(lease["payload_sha256"]),
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
        "lease_state": "revoked",
        "required_gaps": ["worktree_add_failed"],
    }


def _lane_start_carrier_gap(repo: Path, *, target: Path, branch: str) -> str:
    if os.path.lexists(target):
        return "lane_start_target_path_exists"
    return "lane_start_target_ref_exists" if ref_head(repo, branch) else ""


def _exact_worktree(repo: Path, *, target: Path, branch: str, head: str) -> bool:
    worktrees = workspace_status(repo).get("worktrees", ())
    if not isinstance(worktrees, list):
        return False
    return any(
        Path(str(item.get("path") or "")).resolve() == target
        and item.get("branch") == branch
        and item.get("head") == head
        for item in worktrees
        if isinstance(item, dict) and item.get("path")
    )


def bind_work_lane_claim(
    *,
    root: Path,
    claim_id: str,
    branch: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    repo = repo_root(root)
    status = workspace_status(repo)
    target_branch = branch or str(status["branch"])
    gaps: list[str] = []
    if not claim_id.strip():
        gaps.append("missing_claim_id")
    lane = next(
        (
            payload
            for payload in cast("list[dict[str, object]]", status["worktrees"])
            if payload.get("branch") == target_branch and payload.get("role") == ROLE_WORK_LANE
        ),
        None,
    )
    if lane is None:
        gaps.append(f"work_lane_not_found:{target_branch}")
    state_db = accepted_worktree_root(status.get("worktrees"), repo) / ".ethos/state/state.sqlite"
    lease = _active_lease(state_db, target_branch)
    if lease is None:
        gaps.append(f"work_lane_missing_lease:{target_branch}")
    if gaps:
        return {
            "ok": False,
            "state": "blocked",
            "branch": target_branch,
            "claim_id": claim_id,
            "holder_ref": str(lease.get("holder_ref") or "") if lease else "",
            "required_gaps": sorted(set(gaps)),
        }
    holder_ref = str(cast("dict[str, object]", lease)["holder_ref"])
    if not apply:
        return {
            "ok": True,
            "state": "planned",
            "branch": target_branch,
            "claim_id": claim_id,
            "holder_ref": holder_ref,
            "required_gaps": [],
        }
    updated = update_lease_payload(
        state_db,
        candidate=cast("dict[str, object]", lease),
        payload={"claim_id": claim_id.strip()},
    )
    return {
        "ok": bool(updated),
        "state": "bound" if updated else "blocked",
        "branch": target_branch,
        "claim_id": claim_id.strip() if updated else "",
        "holder_ref": str(updated.get("holder_ref") or holder_ref),
        "lease": updated,
        "required_gaps": [] if updated else [f"work_lane_missing_lease:{target_branch}"],
    }


def _active_lease(db_path: Path, subject: str) -> dict[str, object] | None:
    for lease in active_leases(db_path):
        if lease["subject"] == subject:
            return lease
    return None


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
