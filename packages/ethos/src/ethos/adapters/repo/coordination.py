from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.state.invalid import invalid_state_projection

if TYPE_CHECKING:
    from pathlib import Path

FOREIGN_WORK_LANE_ALLOWED_ACTIONS = ("observe",)
FOREIGN_WORK_LANE_FORBIDDEN_ACTIONS = ("write", "land", "retire")
FOREIGN_WORK_LANE_WRITE_POLICY = "owner_only"
FOREIGN_WORK_LANE_RETIRE_POLICY = "owner_handoff_or_maintainer_break_glass"
FOREIGN_WORK_LANE_HANDOFF_REQUIRED = True
LANDED_DIRTY_RESIDUE_STATE = "unpreserved_worktree_delta"
CLEAN_RESIDUE_STATE = "clean_or_none"
LANDED_DIRTY_NEXT_ACTION = (
    "owner must preserve or intentionally discard dirty worktree delta before retirement"
)
CLEAN_RESIDUE_NEXT_ACTION = "observe lane state; use owner-bound lifecycle command when ready"


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
    relation_to_accepted: str = "",
    dirty_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    branch = str(worktree["branch"])
    committed_scope, committed_state = branch_path_scope(
        root, branch=branch, candidate_branch=candidate_branch
    )
    path_scope = tuple(dict.fromkeys((*committed_scope, *dirty_paths)))
    scope_state = _combined_scope_state(committed_state, path_scope)
    owner = str(lease.get("owner") or "")
    disposition = closeout_disposition(
        lease_state="leased" if owner else "missing",
        claim_binding="bound" if claim_id else "missing",
        relation_to_accepted=relation_to_accepted,
        dirty=bool(dirty_paths),
    )
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
        "relation_to_accepted": relation_to_accepted,
        "closeout_disposition": disposition,
        "residue_state": residue_state(disposition),
        "next_action": lane_next_action(
            disposition,
            branch=branch,
            head=str(worktree["head"]),
        ),
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
        **foreign_work_lane_capability(),
    }


def residue_state(disposition: str) -> str:
    if disposition == "landed_dirty":
        return LANDED_DIRTY_RESIDUE_STATE
    return CLEAN_RESIDUE_STATE


def lane_next_action(disposition: str, *, branch: str = "", head: str = "") -> str:
    if disposition == "landed_dirty":
        return LANDED_DIRTY_NEXT_ACTION
    if disposition == "retire_ready" and branch and head:
        return (
            "retire clean absorbed Work Lane with "
            f"ethos lane retire-landed --branch {branch} "
            f"--expect-head {head} --apply --json"
        )
    return CLEAN_RESIDUE_NEXT_ACTION


def foreign_work_lane_capability() -> dict[str, object]:
    return {
        "current_actor_capability": "observe",
        "allowed_actions": list(FOREIGN_WORK_LANE_ALLOWED_ACTIONS),
        "forbidden_actions": list(FOREIGN_WORK_LANE_FORBIDDEN_ACTIONS),
        "write_policy": FOREIGN_WORK_LANE_WRITE_POLICY,
        "retire_policy": FOREIGN_WORK_LANE_RETIRE_POLICY,
        "handoff_required": FOREIGN_WORK_LANE_HANDOFF_REQUIRED,
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
        if _is_closeout_residue(lane) and "work_lane_closeout_residue_present" not in advisory:
            advisory.append("work_lane_closeout_residue_present")
        if current_role != ROLE_WORK_LANE:
            continue
        state = str(lane.get("coordination_state") or "unknown")
        if state == "unknown":
            advisory.append(f"coordination_gap:foreign_scope_unknown:{branch}")
        elif state == "overlap":
            # Same-file conflict only (path_overlaps is a same-file/ancestor oracle:
            # two different files in one directory do NOT overlap). Git's ff-only land
            # already refuses a genuine same-file conflict, so this is advisory, not a
            # blocking gate — surfacing the contention (万象昭幽) without serializing
            # every concurrent lane that merely shares a directory.
            advisory.append(f"coordination_gap:scope_overlap:{branch}")
    return required, advisory


def closeout_disposition(
    *,
    lease_state: str,
    claim_binding: str,
    relation_to_accepted: str,
    dirty: bool,
) -> str:
    """Classify closeout state without authorizing foreign lane mutation."""
    if relation_to_accepted == "unknown":
        return "unknown"
    if relation_to_accepted == "ancestor_of_accepted" and dirty:
        return "landed_dirty"
    if (
        relation_to_accepted == "ancestor_of_accepted"
        and lease_state == "leased"
        and claim_binding == "bound"
    ):
        return "retire_ready"
    if relation_to_accepted == "descendant_of_accepted":
        return "unlanded"
    if relation_to_accepted == "diverged_from_accepted":
        return "diverged"
    return "none"


def _is_closeout_residue(lane: dict[str, object]) -> bool:
    return str(lane.get("closeout_disposition") or "") not in {"", "none"}


def coordination_package(
    foreign_work_lanes: list[dict[str, object]],
    *,
    required_gaps: list[str],
    advisory_gaps: list[str],
    unbound_work_lane_refs: list[dict[str, object]] | None = None,
    unbound_work_lane_count: int = 0,
) -> dict[str, object]:
    overlap_lanes = [
        lane for lane in foreign_work_lanes if lane.get("coordination_state") == "overlap"
    ]
    closeout_residue_lanes = [lane for lane in foreign_work_lanes if _is_closeout_residue(lane)]
    unknown_scope_count = sum(
        1 for lane in foreign_work_lanes if lane.get("coordination_state") == "unknown"
    )
    missing_lease_count = sum(1 for lane in foreign_work_lanes if lane["lease_state"] == "missing")
    dirty_closeout_residue_count = sum(1 for lane in closeout_residue_lanes if lane.get("dirty"))
    unbound_refs = list(unbound_work_lane_refs or ())
    if not unbound_refs and unbound_work_lane_count:
        unbound_refs = [_unknown_unbound_ref() for _ in range(unbound_work_lane_count)]
    return {
        "kind": "work_lane_coordination",
        "blocking": bool(required_gaps),
        "required_gaps": list(required_gaps),
        "advisory_gaps": list(advisory_gaps),
        "invalid_states": invalid_state_projection([*required_gaps, *advisory_gaps]),
        "foreign_work_lane_count": len(foreign_work_lanes),
        "unbound_work_lane_count": len(unbound_refs),
        "unbound_work_lane_refs": unbound_refs,
        "missing_lease_count": missing_lease_count,
        "overlap_count": len(overlap_lanes),
        "unknown_scope_count": unknown_scope_count,
        "closeout_residue_count": len(closeout_residue_lanes),
        "dirty_closeout_residue_count": dirty_closeout_residue_count,
        "closeout_residue_lanes": [
            _closeout_residue_summary(lane) for lane in closeout_residue_lanes
        ],
        "next_action": coordination_next_action(
            required_gaps=required_gaps,
            overlap_count=len(overlap_lanes),
            unknown_scope_count=unknown_scope_count,
            missing_lease_count=missing_lease_count,
            foreign_work_lane_count=len(foreign_work_lanes),
            unbound_work_lane_count=len(unbound_refs),
        ),
        "migration_recommendations": [_migration_recommendation(lane) for lane in overlap_lanes],
    }


def _closeout_residue_summary(lane: dict[str, object]) -> dict[str, object]:
    return {
        "branch": str(lane.get("branch") or ""),
        "closeout_disposition": str(lane.get("closeout_disposition") or ""),
        "residue_state": str(lane.get("residue_state") or ""),
        "dirty": bool(lane.get("dirty")),
    }


def _unknown_unbound_ref() -> dict[str, object]:
    return {
        "branch": "",
        "head": "",
        "claim_id": "",
        "claim_binding": "unbound",
        "relation_to_accepted": "unknown",
        "next_action": "inspect unbound Work Lane ref before cleanup",
    }


def coordination_next_action(
    *,
    required_gaps: list[str],
    overlap_count: int,
    unknown_scope_count: int,
    missing_lease_count: int,
    foreign_work_lane_count: int,
    unbound_work_lane_count: int,
) -> str:
    if required_gaps:
        return "resolve required Work Lane coordination gaps before candidate integration"
    if unknown_scope_count:
        return "inspect unknown Work Lane scope before candidate integration"
    if overlap_count:
        return "review overlapping Work Lane scope before candidate integration"
    if missing_lease_count:
        return "bind or inspect Work Lane leases before candidate integration"
    if foreign_work_lane_count:
        return "review advisory Work Lane coordination signals before candidate integration"
    if unbound_work_lane_count:
        return "inspect or retire unbound Work Lane refs during coordination cleanup"
    return "no Work Lane coordination action required"


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
