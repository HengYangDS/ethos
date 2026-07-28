from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.store.state.lease.projection import integer_value
from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.state.invalid import invalid_state_projection

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
        "lease": lease_summary(lease),
        "lease_state": lease_state,
        "base_commitment_digest": base_digest if lease_state in {"valid", "expired"} else "",
        "contract_binding": str(lease.get("contract_binding") or lease_state),
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


def lease_summary(lease: dict[str, object]) -> dict[str, object]:
    """Project non-secret local coordination fields without minting authority."""
    result: dict[str, object] = {
        name: str(lease.get(name) or "")
        for name in (
            "lane_incarnation_id",
            "lease_id",
            "holder_ref",
            "expected_head",
            "expires_at",
            "payload_sha256",
            "base_commitment_digest",
        )
    }
    result.update(epoch=integer_value(lease.get("epoch")), mints_authority=False)
    return result


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


def coordination_package(
    foreign_work_lanes: list[dict[str, object]],
    *,
    required_gaps: list[str],
    advisory_gaps: list[str],
    defer_details: bool = False,
    unbound_work_lane_refs: list[dict[str, object]] | None = None,
    unbound_work_lane_count: int = 0,
) -> dict[str, object]:
    detail_state = "deferred" if defer_details else "exact"
    unbound_refs = [
        {**ref, "next_action": FOREIGN_WORK_LANE_NEXT_ACTION}
        for ref in unbound_work_lane_refs or ()
    ]
    if not unbound_refs and unbound_work_lane_count:
        unbound_refs = [_unknown_unbound_ref() for _ in range(unbound_work_lane_count)]
    counts: dict[str, int] = {
        "missing_lease_count": sum(lane["lease_state"] == "missing" for lane in foreign_work_lanes),
        "overlap_count": sum(
            lane.get("coordination_state") == "overlap" for lane in foreign_work_lanes
        ),
        "unknown_scope_count": sum(
            lane.get("coordination_state") == "unknown" for lane in foreign_work_lanes
        ),
        "dirty_foreign_work_lane_count": sum(
            bool(lane.get("dirty")) for lane in foreign_work_lanes
        ),
    }
    projected_counts = {
        name: value if detail_state == "exact" or name == "missing_lease_count" else None
        for name, value in counts.items()
    }
    return {
        "kind": "work_lane_coordination",
        "detail_state": detail_state,
        "blocking": bool(required_gaps),
        "required_gaps": list(required_gaps),
        "advisory_gaps": list(advisory_gaps),
        "invalid_states": invalid_state_projection([*required_gaps, *advisory_gaps]),
        "foreign_work_lane_count": len(foreign_work_lanes),
        **projected_counts,
        "unbound_work_lane_count": len(unbound_refs),
        "unbound_work_lane_refs": unbound_refs,
        "next_action": coordination_next_action(
            required_gaps=required_gaps,
            foreign_work_lane_count=len(foreign_work_lanes),
            unbound_work_lane_count=len(unbound_refs),
            **{
                name: counts[name]
                for name in ("overlap_count", "unknown_scope_count", "missing_lease_count")
            },
        ),
    }


def _unknown_unbound_ref() -> dict[str, object]:
    return dict.fromkeys(("branch", "head", "base_commitment_digest"), "") | {
        "contract_binding": "missing",
        "lease_state": "missing",
        "relation_to_accepted": "unknown",
        "next_action": FOREIGN_WORK_LANE_NEXT_ACTION,
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
    choices = (
        (
            required_gaps,
            "resolve required current Work Lane coordination gaps before candidate integration",
        ),
        (
            foreign_work_lane_count or unbound_work_lane_count,
            FOREIGN_WORK_LANE_NEXT_ACTION,
        ),
        (unknown_scope_count, "inspect unknown Work Lane scope before candidate integration"),
        (overlap_count, "review overlapping Work Lane scope before candidate integration"),
        (missing_lease_count, "bind or inspect Work Lane leases before candidate integration"),
    )
    return next(
        (action for active, action in choices if active),
        "no Work Lane coordination action required",
    )


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
