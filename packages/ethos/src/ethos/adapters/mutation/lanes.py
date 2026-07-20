from __future__ import annotations

from pathlib import Path
from typing import cast

from ethos.adapters.mutation.lane_lifecycle.core import default_candidate_path
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.lane_lifecycle.core import slug
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status.bindings import accepted_worktree_root
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.lease.lifecycle.effects import update_lease_payload
from ethos.adapters.store.state.lease.projection import active_leases
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

    def blocked(gap: str, **extra: object) -> dict[str, object]:
        return {
            "ok": False,
            "state": "blocked",
            "branch": branch,
            "path": target.as_posix(),
            **extra,
            "required_gaps": [gap],
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
    if _branch_exists(repo, branch):
        return blocked("branch_already_exists")
    completed = run_git(
        repo,
        "worktree",
        "add",
        "-b",
        branch,
        target.as_posix(),
        policy.candidate_branch,
        check=False,
    )
    if completed.returncode != 0:
        return blocked("worktree_add_failed", stderr=completed.stderr.strip())
    lease = acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject=branch,
        holder_ref=normalized_holder_ref,
        payload={
            "path": target.as_posix(),
            "branch": branch,
            "claim_id": claim_id or "",
            "expected_head": str(candidate["head"]),
        },
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
    lane = _status_work_lane(status, target_branch)
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
        subject=target_branch,
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


def _status_work_lane(
    status: dict[str, object],
    branch: str,
) -> dict[str, object] | None:
    worktrees = status.get("worktrees")
    if not isinstance(worktrees, list):
        return None
    for worktree in worktrees:
        if not isinstance(worktree, dict):
            continue
        payload = cast("dict[str, object]", worktree)
        if payload.get("branch") == branch and payload.get("role") == ROLE_WORK_LANE:
            return payload
    return None


def _active_lease(db_path: Path, subject: str) -> dict[str, object] | None:
    for lease in active_leases(db_path):
        if lease["subject"] == subject:
            return lease
    return None


def _branch_exists(root: Path, branch: str) -> bool:
    completed = run_git(
        root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False
    )
    return completed.returncode == 0


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
