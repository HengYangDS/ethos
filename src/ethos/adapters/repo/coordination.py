from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    from pathlib import Path

FOREIGN_WORK_LANE_FORBIDDEN_ACTIONS = ("write", "land", "retire")
FOREIGN_WORK_LANE_HANDOFF_REQUIRED = True
FOREIGN_WORK_LANE_NEXT_ACTION = (
    "observe only; request holder handoff or exact authorized Lease takeover"
)


def branch_path_scope(
    root: Path, *, branch: str, candidate_branch: str
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
    if completed.returncode:
        return (), "unknown"
    paths = tuple(filter(None, completed.stdout.splitlines()))
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
    states = {current_scope_state, foreign_scope_state}
    return next(
        (state for state in ("deferred", "unknown") if state in states),
        "overlap" if scopes_overlap(current_path_scope, foreign_path_scope) else "disjoint",
    )


@dataclass(frozen=True, slots=True)
class ForeignLaneContext:
    current_role: str
    current_path_scope: tuple[str, ...]
    current_scope_state: str
    candidate_branch: str
    lease: dict[str, object]
    root: Path
    relation_to_accepted: str = ""
    dirty_paths: tuple[str, ...] = ()


def foreign_work_lane(worktree: dict[str, str], context: ForeignLaneContext) -> dict[str, object]:
    committed, committed_state = branch_path_scope(
        context.root,
        branch=worktree["branch"],
        candidate_branch=context.candidate_branch,
    )
    path_scope = tuple(dict.fromkeys((*committed, *context.dirty_paths)))
    scope_state = _combined_scope_state(committed_state, path_scope)
    return _foreign_lane_payload(
        worktree,
        {
            "lease": context.lease,
            "relation_to_accepted": context.relation_to_accepted,
            "dirty_paths": context.dirty_paths,
            "path_scope": path_scope,
            "scope_state": scope_state,
            "coordination": coordination_state(
                current_role=context.current_role,
                current_path_scope=context.current_path_scope,
                current_scope_state=context.current_scope_state,
                foreign_path_scope=path_scope,
                foreign_scope_state=scope_state,
            ),
        },
    )


def foreign_work_lane_deferred(
    worktree: dict[str, str],
    *,
    lease: dict[str, object],
    relation_to_accepted: str = "unknown",
    dirty_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    """Project lifecycle facts without inspecting foreign history or dirty state."""
    return _foreign_lane_payload(
        worktree,
        {
            "lease": lease,
            "relation_to_accepted": relation_to_accepted,
            "dirty_paths": dirty_paths,
            "path_scope": (),
            "scope_state": "deferred",
            "coordination": "advisory",
        },
    )


def _foreign_lane_payload(
    worktree: dict[str, str], context: dict[str, object]
) -> dict[str, object]:
    branch = worktree["branch"]
    lease = cast("dict[str, object]", context["lease"])
    dirty_paths = cast("tuple[str, ...]", context["dirty_paths"])
    lease_state = str(lease.get("lease_state") or "missing")
    base_digest = str(lease.get("base_commitment_digest") or "")
    return {
        **{name: worktree[name] for name in ("path", "head", "branch", "role", "worktree_binding")},
        "lease": {key: value for key, value in lease_generation(lease).items() if key != "branch"}
        | {"mints_authority": False},
        "lease_state": lease_state,
        "base_commitment_digest": base_digest if lease_state in {"valid", "expired"} else "",
        "commitment_binding": str(lease.get("commitment_binding") or lease_state),
        "relation_to_accepted": str(context["relation_to_accepted"]),
        "next_action": FOREIGN_WORK_LANE_NEXT_ACTION,
        "dirty": None if context["scope_state"] == "deferred" else bool(dirty_paths),
        "dirty_paths": list(dirty_paths),
        "path_scope": list(cast("tuple[str, ...]", context["path_scope"])),
        "scope_state": str(context["scope_state"]),
        "coordination_state": str(context["coordination"]),
        "action_preview": AdmissionDecision.action_preview(
            action="observe",
            resource=branch,
            blocked_actions=FOREIGN_WORK_LANE_FORBIDDEN_ACTIONS,
            why=("foreign_lane_requires_handoff_or_exact_authorized_lease_takeover",),
        ),
        "handoff_required": FOREIGN_WORK_LANE_HANDOFF_REQUIRED,
    }


def _combined_scope_state(committed_state: str, path_scope: tuple[str, ...]) -> str:
    return (
        committed_state
        if committed_state in {"deferred", "unknown"}
        else "bounded"
        if path_scope
        else "empty"
    )


def coordination_gaps(
    foreign_work_lanes: list[dict[str, object]],
    *,
    current_role: str,
    current_scope_state: str,
) -> tuple[list[str], list[str]]:
    required = (
        ["coordination_gap:current_scope_unknown"]
        if current_role == ROLE_WORK_LANE and current_scope_state == "unknown"
        else []
    )
    advisory = ["foreign_work_lane_present"] if foreign_work_lanes else []
    for lane in foreign_work_lanes:
        branch = str(lane["branch"])
        if lane["lease_state"] == "missing":
            advisory.append(f"work_lane_missing_lease:{branch}")
        elif lane["lease_state"] == "unknown":
            advisory.append(f"work_lane_lease_unknown:{branch}")
        elif lane["lease_state"] == "expired":
            advisory.append(f"work_lane_lease_expired:{branch}")
        if current_role != ROLE_WORK_LANE:
            continue
        state = str(lane.get("coordination_state") or "unknown")
        if state == "unknown":
            advisory.append(f"coordination_gap:foreign_scope_unknown:{branch}")
        elif state == "overlap":
            advisory.append(f"coordination_gap:scope_overlap:{branch}")
    return required, advisory


def collaboration_competition_projection(
    foreign_work_lanes: list[dict[str, object]],
    *,
    commitment_digest: str,
    risks: tuple[str, ...],
    proof_cost: int,
    proof_capacity: int | None,
) -> dict[str, object]:
    """Derive collaboration or competition from current resource facts."""
    branches = [str(lane.get("branch") or "") for lane in foreign_work_lanes]
    overlap = [lane for lane in foreign_work_lanes if lane.get("coordination_state") == "overlap"]
    unknown = [
        lane
        for lane in foreign_work_lanes
        if lane.get("coordination_state") in {"deferred", "unknown"}
    ]
    alternatives = [
        lane
        for lane in overlap
        if commitment_digest and lane.get("base_commitment_digest") == commitment_digest
    ]
    conflicts = [lane for lane in overlap if lane not in alternatives]
    costs = [lane.get("proof_cost") for lane in alternatives]
    total_cost = proof_cost + sum(cost for cost in costs if isinstance(cost, int))
    if not foreign_work_lanes:
        state, reason = "independent", "no_peer_work_lanes"
    elif unknown:
        state, reason = "await_facts", "peer_scope_unknown"
    elif conflicts:
        state, reason = "collaborate", "overlapping_intents_require_coordination"
    elif not alternatives:
        state, reason = "independent", "peer_scopes_disjoint"
    elif not risks:
        state, reason = "collaborate", "competition_has_no_declared_risk_basis"
    elif proof_capacity is None or any(not isinstance(cost, int) for cost in costs):
        state, reason = "await_facts", "proof_capacity_or_cost_missing"
    elif total_cost > proof_capacity:
        state, reason = "collaborate", "proof_capacity_below_alternative_cost"
    else:
        state, reason = "compete", "alternative_realizations_admitted"
    return {
        "state": state,
        "reason": reason,
        "proof_capacity": proof_capacity,
        "proof_cost": total_cost,
        "risk_count": len(risks),
        "peer_count": len(foreign_work_lanes),
        "alternative_count": len(alternatives),
        "conflict_count": len(conflicts),
        "unknown_count": len(unknown),
        "branches": branches,
    }


def scopes_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return any(path_overlaps(a, b) for a in left for b in right)


def path_overlaps(left: str, right: str) -> bool:
    left_parts, right_parts = [tuple(filter(None, path.split("/"))) for path in (left, right)]
    common = min(len(left_parts), len(right_parts))
    return bool(common) and left_parts[:common] == right_parts[:common]


def workspace_required_gaps(closeout_gaps: list[str], *, candidate: dict[str, object]) -> list[str]:
    gaps = [
        gap
        for gap in closeout_gaps
        if gap.startswith(("work_lane_missing_lease:", "coordination_gap:"))
    ]
    missing = (
        "candidate_branch_missing"
        if not candidate["exists"]
        else ("candidate_worktree_missing" if not candidate["worktree_exists"] else "")
    )
    if missing:
        gaps.append(missing)
    return gaps
