"""Exact worktree recovery for one partial linked-lane retirement."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.worktree_effects import add_worktree
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import BranchRolePolicy


def recovery_lane(
    repo: Path,
    *,
    policy: BranchRolePolicy,
    worktrees: list[dict[str, object]],
    leases: dict[str, dict[str, object]],
    branch: str,
    path: str,
    head: str,
) -> dict[str, object]:
    """Compile one exact unbound-ref recovery target without filesystem mutation."""
    if not path:
        return {}
    target = Path(path)
    lease = leases.get(branch, {})
    lease_state = str(lease.get("lease_state") or "missing")
    gaps = _path_gaps(target, worktrees)
    gaps.extend(
        gap
        for failed, gap in (
            (policy.role_for_branch(branch) != ROLE_WORK_LANE, "superseded_retire_not_work_lane"),
            (not head, "superseded_retire_branch_not_found"),
            (
                lease_state == "unknown",
                f"work_lane_lease_unknown:{branch}",
            ),
            (
                lease_state == "expired",
                f"work_lane_lease_expired:{branch}",
            ),
            (
                lease_state not in {"valid", "unknown", "expired"},
                f"work_lane_missing_lease:{branch}",
            ),
            (
                lease_state == "valid" and str(lease.get("expected_head") or "") != head,
                "lease_head_stale",
            ),
        )
        if failed
    )
    if lease_state == "valid":
        try:
            load_lease_bound_commitment(repo, lease=lease)
        except ValueError as error:
            gaps.append(str(error))
    return {
        "branch": branch,
        "path": target.as_posix(),
        "head": head,
        "lease": {key: value for key, value in lease_generation(lease).items() if key != "branch"}
        | {"mints_authority": False},
        "lease_state": lease_state,
        "recovery_required": True,
        "retire_ready": not gaps,
        "required_gaps": sorted(set(gaps)),
    }


def recover_worktree(control_root: Path, lane: dict[str, object]) -> dict[str, object]:
    """Recreate one exact Lease-bound linked worktree before retirement."""
    hooks = hook_runtime_binding(control_root)
    if hooks["required_gaps"]:
        return {
            "verdict": "block",
            "state": "blocked",
            "required_gaps": ["retirement_recovery_hook_runtime_invalid"],
        }
    try:
        target = Path(str(lane["path"]))
        attestation = add_worktree(
            control_root,
            target,
            branch=str(lane["branch"]),
            head=str(lane["head"]),
        )
    except (KeyError, OSError, ValueError) as error:
        detail = str(error).strip() or error.__class__.__name__
        return {
            "verdict": "block",
            "state": "blocked",
            "required_gaps": [f"retirement_recovery_failed:{detail.partition(':')[0]}"],
            "stderr": detail,
        }
    return {
        "verdict": "pass",
        "state": "recovered_for_retirement",
        "required_gaps": [],
        "effect": cast("dict[str, object]", attestation.model_dump(mode="json")),
        "hook_runtime": hook_runtime_binding(target),
    }


def _path_gaps(target: Path, worktrees: list[dict[str, object]]) -> list[str]:
    if not target.is_absolute():
        return ["retirement_recovery_path_not_absolute"]
    if os.path.lexists(target):
        return ["retirement_recovery_path_collision"]
    resolved = target.resolve()
    registered = any(
        path and Path(path).resolve() == resolved
        for row in worktrees
        if (path := str(row.get("path") or ""))
    )
    return ["retirement_recovery_path_registered"] if registered else []
