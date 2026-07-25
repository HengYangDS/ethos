# ruff: noqa: E501 - source-budget closeout keeps equivalent projections compact.
from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.store.state.lease.projection import integer_value
from ethos.contracts.admission import AdmissionDecision
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.state.invalid import invalid_state_projection

if TYPE_CHECKING:
    from pathlib import Path

# fmt: off

FOREIGN_WORK_LANE_FORBIDDEN_ACTIONS = ("write", "land", "retire")
FOREIGN_WORK_LANE_HANDOFF_REQUIRED = True
LANDED_DIRTY_RESIDUE_STATE = "unpreserved_worktree_delta"
CLEAN_RESIDUE_STATE = "clean_or_none"
LANDED_DIRTY_NEXT_ACTION = "owner must preserve or intentionally discard dirty worktree delta before retirement"
CLEAN_RESIDUE_NEXT_ACTION = "observe lane state; use owner-bound lifecycle command when ready"


def branch_path_scope(root: Path, *, branch: str, candidate_branch: str) -> tuple[tuple[str, ...], str]:
    if not branch or branch == "detached":
        return (), "unknown"
    completed = subprocess.run(["git", "diff", "--name-only", f"{candidate_branch}...{branch}"],
                               cwd=root, check=False, text=True, capture_output=True)
    if completed.returncode:
        return (), "unknown"
    paths = tuple(filter(None, completed.stdout.splitlines()))
    return paths, "bounded" if paths else "empty"


def coordination_state(
    *, current_role: str, current_path_scope: tuple[str, ...], current_scope_state: str,
    foreign_path_scope: tuple[str, ...], foreign_scope_state: str,
) -> str:
    if current_role != ROLE_WORK_LANE:
        return "advisory"
    states = {current_scope_state, foreign_scope_state}
    return next((state for state in ("deferred", "unknown") if state in states),
                "overlap" if scopes_overlap(current_path_scope, foreign_path_scope) else "disjoint")


def foreign_work_lane(  # noqa: PLR0913, RUF100 - exact bound-state dimensions
    worktree: dict[str, str], *, current_role: str, current_path_scope: tuple[str, ...],
    current_scope_state: str, candidate_branch: str, lease: dict[str, object], root: Path,
    claim_id: str, relation_to_accepted: str = "", dirty_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    committed, committed_state = branch_path_scope(root, branch=worktree["branch"], candidate_branch=candidate_branch)
    path_scope = tuple(dict.fromkeys((*committed, *dirty_paths)))
    scope_state = _combined_scope_state(committed_state, path_scope)
    disposition = closeout_disposition(lease_state="leased" if lease.get("holder_ref") else "missing",
                                       claim_binding="bound" if claim_id else "missing",
                                       relation_to_accepted=relation_to_accepted, dirty=bool(dirty_paths))
    return _foreign_lane_payload(worktree, {
        "lease": lease, "claim_id": claim_id, "relation_to_accepted": relation_to_accepted,
        "disposition": disposition, "dirty_paths": dirty_paths, "path_scope": path_scope,
        "scope_state": scope_state, "coordination": coordination_state(
            current_role=current_role, current_path_scope=current_path_scope,
            current_scope_state=current_scope_state, foreign_path_scope=path_scope,
            foreign_scope_state=scope_state),
    })


def foreign_work_lane_deferred(
    worktree: dict[str, str], *, lease: dict[str, object], claim_id: str,
    relation_to_accepted: str = "unknown", dirty_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    """Project lifecycle facts without inspecting foreign history or dirty state."""
    return _foreign_lane_payload(worktree, {
        "lease": lease, "claim_id": claim_id, "relation_to_accepted": relation_to_accepted,
        "disposition": "none", "dirty_paths": dirty_paths, "path_scope": (),
        "scope_state": "deferred", "coordination": "advisory",
    })


def _foreign_lane_payload(worktree: dict[str, str], context: dict[str, object]) -> dict[str, object]:
    branch, head = worktree["branch"], worktree["head"]
    lease = cast("dict[str, object]", context["lease"])
    claim_id, disposition = str(context["claim_id"]), str(context["disposition"])
    dirty_paths = cast("tuple[str, ...]", context["dirty_paths"])
    return {
        **{name: worktree[name] for name in ("path", "head", "branch", "role", "worktree_binding")},
        "lease": lease_summary(lease),
        "lease_state": "leased" if lease.get("holder_ref") else "missing",
        "claim_id": claim_id, "claim_binding": "bound" if claim_id else "missing",
        "relation_to_accepted": str(context["relation_to_accepted"]),
        "closeout_disposition": disposition, "residue_state": residue_state(disposition),
        "next_action": lane_next_action(disposition, branch=branch, head=head),
        "dirty": None if context["scope_state"] == "deferred" else bool(dirty_paths), "dirty_paths": list(dirty_paths),
        "path_scope": list(cast("tuple[str, ...]", context["path_scope"])),
        "scope_state": str(context["scope_state"]),
        "coordination_state": str(context["coordination"]),
        "action_preview": AdmissionDecision.action_preview(action="observe", resource=branch,
            blocked_actions=FOREIGN_WORK_LANE_FORBIDDEN_ACTIONS,
            why=("foreign_lane_requires_handoff_or_accepted_decision",)),
        "handoff_required": FOREIGN_WORK_LANE_HANDOFF_REQUIRED,
    }


def residue_state(disposition: str) -> str:
    return LANDED_DIRTY_RESIDUE_STATE if disposition == "landed_dirty" else CLEAN_RESIDUE_STATE


def lane_next_action(disposition: str, *, branch: str = "", head: str = "") -> str:
    if disposition == "landed_dirty":
        return LANDED_DIRTY_NEXT_ACTION
    if disposition == "retire_ready" and branch and head:
        return ("retire clean absorbed Work Lane with "
                f"ethos lane retire landed --branch {branch} --expect-head {head} --apply --json")
    return CLEAN_RESIDUE_NEXT_ACTION


def lease_summary(lease: dict[str, object]) -> dict[str, object]:
    """Project non-secret local coordination fields without minting authority."""
    result: dict[str, object] = {name: str(lease.get(name) or "") for name in
                                ("lane_incarnation_id", "lease_id", "holder_ref", "expected_head", "expires_at", "payload_sha256")}
    result.update(epoch=integer_value(lease.get("epoch")), mints_authority=False)
    return result


def _combined_scope_state(committed_state: str, path_scope: tuple[str, ...]) -> str:
    return committed_state if committed_state in {"deferred", "unknown"} else "bounded" if path_scope else "empty"


def coordination_gaps(
    foreign_work_lanes: list[dict[str, object]], *, current_role: str,
    current_scope_state: str,
) -> tuple[list[str], list[str]]:
    required = (["coordination_gap:current_scope_unknown"]
                if current_role == ROLE_WORK_LANE and current_scope_state == "unknown" else [])
    advisory = ["foreign_work_lane_present"] if foreign_work_lanes else []
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
            advisory.append(f"coordination_gap:scope_overlap:{branch}")
    return required, advisory


def closeout_disposition(
    *, lease_state: str, claim_binding: str, relation_to_accepted: str, dirty: bool
) -> str:
    """Classify closeout state without authorizing foreign lane mutation."""
    if relation_to_accepted == "unknown":
        return "unknown"
    if relation_to_accepted == "ancestor_of_accepted":
        if dirty:
            return "landed_dirty"
        return "retire_ready" if (lease_state, claim_binding) == ("leased", "bound") else "none"
    return {"descendant_of_accepted": "unlanded", "diverged_from_accepted": "diverged"}.get(relation_to_accepted, "none")


def _is_closeout_residue(lane: dict[str, object]) -> bool:
    return str(lane.get("closeout_disposition") or "") not in {"", "none"}


def coordination_package(
    foreign_work_lanes: list[dict[str, object]], *, required_gaps: list[str],
    advisory_gaps: list[str],
    defer_details: bool = False,
    unbound_work_lane_refs: list[dict[str, object]] | None = None,
    unbound_work_lane_count: int = 0,
) -> dict[str, object]:
    detail_state = "deferred" if defer_details else "exact"
    overlaps = [lane for lane in foreign_work_lanes if lane.get("coordination_state") == "overlap"]
    residues = list(filter(_is_closeout_residue, foreign_work_lanes))
    unbound_refs = list(unbound_work_lane_refs or ())
    if not unbound_refs and unbound_work_lane_count:
        unbound_refs = [_unknown_unbound_ref() for _ in range(unbound_work_lane_count)]
    counts: dict[str, int] = {
        "missing_lease_count": sum(lane["lease_state"] == "missing" for lane in foreign_work_lanes),
        "overlap_count": len(overlaps),
        "unknown_scope_count": sum(lane.get("coordination_state") == "unknown" for lane in foreign_work_lanes),
        "dirty_foreign_work_lane_count": sum(bool(lane.get("dirty")) for lane in foreign_work_lanes),
        "closeout_residue_count": len(residues),
        "dirty_closeout_residue_count": sum(bool(lane.get("dirty")) for lane in residues)}
    projected_counts = {name: value if detail_state == "exact" or name == "missing_lease_count" else None
                        for name, value in counts.items()}
    return {
        "kind": "work_lane_coordination", "detail_state": detail_state,
        "blocking": bool(required_gaps), "required_gaps": list(required_gaps),
        "advisory_gaps": list(advisory_gaps),
        "invalid_states": invalid_state_projection([*required_gaps, *advisory_gaps]),
        "foreign_work_lane_count": len(foreign_work_lanes), **projected_counts,
        "unbound_work_lane_count": len(unbound_refs), "unbound_work_lane_refs": unbound_refs,
        "closeout_residue_lanes": [_closeout_residue_summary(lane) for lane in residues],
        "next_action": coordination_next_action(required_gaps=required_gaps,
            foreign_work_lane_count=len(foreign_work_lanes), unbound_work_lane_count=len(unbound_refs),
            **{name: counts[name] for name in ("overlap_count", "unknown_scope_count", "missing_lease_count")}),
        "migration_recommendations": [_migration_recommendation(lane) for lane in overlaps],
    }


def _closeout_residue_summary(lane: dict[str, object]) -> dict[str, object]:
    return {name: str(lane.get(name) or "") for name in ("branch", "closeout_disposition", "residue_state")} | {
        "dirty": bool(lane.get("dirty"))}


def _unknown_unbound_ref() -> dict[str, object]:
    return dict.fromkeys(("branch", "head", "claim_id"), "") | {
        "claim_binding": "unbound", "relation_to_accepted": "unknown",
        "next_action": "inspect unbound Work Lane ref before cleanup"}


def coordination_next_action(  # noqa: PLR0913, RUF100 - exact public decision dimensions
    *, required_gaps: list[str], overlap_count: int, unknown_scope_count: int,
    missing_lease_count: int, foreign_work_lane_count: int, unbound_work_lane_count: int,
) -> str:
    choices = (
        (required_gaps, "resolve required Work Lane coordination gaps before candidate integration"),
        (unknown_scope_count, "inspect unknown Work Lane scope before candidate integration"),
        (overlap_count, "review overlapping Work Lane scope before candidate integration"),
        (missing_lease_count, "bind or inspect Work Lane leases before candidate integration"),
        (foreign_work_lane_count, "review advisory Work Lane coordination signals before candidate integration"),
        (unbound_work_lane_count, "inspect or retire unbound Work Lane refs during coordination cleanup"))
    return next((action for active, action in choices if active), "no Work Lane coordination action required")


def _migration_recommendation(lane: dict[str, object]) -> dict[str, object]:
    branch = str(lane.get("branch") or "")
    lease = lane.get("lease")
    holder_ref = str(lease.get("holder_ref") or "") if isinstance(lease, dict) else ""
    return {
        "kind": "overlap_resolution", "overlapping_branch": branch, "holder_ref": holder_ref,
        "recommendation": "preserve_legitimate_lane_and_replay_or_move_verified_head",
        "next_actions": [
            "do not land a temporary overlapping lane directly",
            f"refresh or move the leased lane {branch} after review" if branch else "refresh the leased lane after review",
            "delete the temporary lane after the legitimate lane carries the verified head",
        ],
    }


def scopes_overlap(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return any(path_overlaps(a, b) for a in left for b in right)


def path_overlaps(left: str, right: str) -> bool:
    left_parts, right_parts = [tuple(filter(None, path.split("/"))) for path in (left, right)]
    common = min(len(left_parts), len(right_parts))
    return bool(common) and left_parts[:common] == right_parts[:common]


def workspace_required_gaps(closeout_gaps: list[str], *, candidate: dict[str, object]) -> list[str]:
    gaps = [gap for gap in closeout_gaps if gap.startswith(("work_lane_missing_lease:", "coordination_gap:"))]
    missing = "candidate_branch_missing" if not candidate["exists"] else (
        "candidate_worktree_missing" if not candidate["worktree_exists"] else "")
    if missing:
        gaps.append(missing)
    return gaps
# fmt: on
