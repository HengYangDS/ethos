from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos_core.contracts.branch_roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    from pathlib import Path


def branch_path_scope(
    root: Path,
    *,
    branch: str,
    candidate_branch: str,
) -> tuple[tuple[str, ...], str]:
    if not branch or branch == "detached":
        return (), "unknown"
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{candidate_branch}...{branch}"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return (), "unknown"
    paths = tuple(path for path in completed.stdout.splitlines() if path)
    return paths, "bounded" if paths else "empty"


def coordination_state(
    *,
    current_role: str,
    current_path_scope: tuple[str, ...],
    current_scope_state: str,
    foreign_path_scope: tuple[str, ...],
    foreign_scope_state: str,
) -> str:
    if current_role != ROLE_WORK_LANE:
        return "advisory"
    if current_scope_state == "unknown" or foreign_scope_state == "unknown":
        return "unknown"
    if scopes_overlap(current_path_scope, foreign_path_scope):
        return "overlap"
    return "disjoint"


def foreign_work_lane(
    worktree: dict[str, str],
    *,
    current_role: str,
    current_path_scope: tuple[str, ...],
    current_scope_state: str,
    candidate_branch: str,
    lease: dict[str, object],
    root: Path,
    claim_id: str,
    dirty_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    branch = str(worktree["branch"])
    committed_scope, committed_state = branch_path_scope(
        root, branch=branch, candidate_branch=candidate_branch
    )
    path_scope = tuple(dict.fromkeys((*committed_scope, *dirty_paths)))
    scope_state = _combined_scope_state(committed_state, path_scope)
    owner = str(lease.get("owner") or "")
    return {
        "path": worktree["path"],
        "head": worktree["head"],
        "branch": branch,
        "role": worktree["role"],
        "worktree_binding": worktree["worktree_binding"],
        "lease_owner": owner,
        "lease_state": "leased" if owner else "missing",
        "claim_id": claim_id,
        "claim_binding": "bound" if claim_id else "missing",
        "dirty": bool(dirty_paths),
        "dirty_paths": list(dirty_paths),
        "path_scope": list(path_scope),
        "scope_state": scope_state,
        "coordination_state": coordination_state(
            current_role=current_role,
            current_path_scope=current_path_scope,
            current_scope_state=current_scope_state,
            foreign_path_scope=path_scope,
            foreign_scope_state=scope_state,
        ),
    }


def _combined_scope_state(committed_state: str, path_scope: tuple[str, ...]) -> str:
    if committed_state == "unknown":
        return "unknown"
    return "bounded" if path_scope else "empty"


def coordination_gaps(
    foreign_work_lanes: list[dict[str, object]],
    *,
    current_role: str,
    current_scope_state: str,
) -> tuple[list[str], list[str]]:
    required: list[str] = []
    advisory: list[str] = []
    if foreign_work_lanes:
        advisory.append("foreign_work_lane_present")
    if current_role == ROLE_WORK_LANE and current_scope_state == "unknown":
        required.append("coordination_gap:current_scope_unknown")
    for lane in foreign_work_lanes:
        branch = str(lane["branch"])
        if lane["lease_state"] == "missing":
            advisory.append(f"work_lane_missing_lease:{branch}")
        if current_role != ROLE_WORK_LANE:
            continue
        state = str(lane.get("coordination_state") or "unknown")
        if state == "unknown":
            required.append(f"coordination_gap:foreign_scope_unknown:{branch}")
        elif state == "overlap":
            required.append(f"coordination_gap:scope_overlap:{branch}")
    return required, advisory


def coordination_package(
    foreign_work_lanes: list[dict[str, object]],
    *,
    required_gaps: list[str],
    advisory_gaps: list[str],
) -> dict[str, object]:
    overlap_lanes = [
        lane for lane in foreign_work_lanes if lane.get("coordination_state") == "overlap"
    ]
    return {
        "kind": "work_lane_coordination",
        "blocking": bool(required_gaps),
        "required_gaps": list(required_gaps),
        "advisory_gaps": list(advisory_gaps),
        "foreign_work_lane_count": len(foreign_work_lanes),
        "missing_lease_count": sum(
            1 for lane in foreign_work_lanes if lane["lease_state"] == "missing"
        ),
        "overlap_count": len(overlap_lanes),
        "unknown_scope_count": sum(
            1 for lane in foreign_work_lanes if lane.get("coordination_state") == "unknown"
        ),
        "next_action": (
            "resolve overlapping or unknown Work Lane scope before candidate integration"
        ),
        "migration_recommendations": [_migration_recommendation(lane) for lane in overlap_lanes],
    }


def _migration_recommendation(lane: dict[str, object]) -> dict[str, object]:
    branch = str(lane.get("branch") or "")
    owner = str(lane.get("lease_owner") or "")
    return {
        "kind": "overlap_resolution",
        "overlapping_branch": branch,
        "owner": owner,
        "recommendation": "preserve_legitimate_lane_and_replay_or_move_verified_head",
        "next_actions": [
            "do not land a temporary overlapping lane directly",
            (
                f"refresh or move the leased lane {branch} after review"
                if branch
                else "refresh the leased lane after review"
            ),
            "delete the temporary lane after the legitimate lane carries the verified head",
        ],
    }


def scopes_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return any(path_overlaps(a, b) for a in left for b in right)


def path_overlaps(left: str, right: str) -> bool:
    left_parts = tuple(part for part in left.split("/") if part)
    right_parts = tuple(part for part in right.split("/") if part)
    if not left_parts or not right_parts:
        return False
    common = min(len(left_parts), len(right_parts))
    return left_parts[:common] == right_parts[:common]


def workspace_required_gaps(
    closeout_gaps: list[str],
    *,
    candidate: dict[str, object],
) -> list[str]:
    gaps = [
        gap
        for gap in closeout_gaps
        if str(gap).startswith(("work_lane_missing_lease:", "coordination_gap:"))
    ]
    if not candidate["exists"]:
        gaps.append("candidate_branch_missing")
    elif not candidate["worktree_exists"]:
        gaps.append("candidate_worktree_missing")
    return gaps
