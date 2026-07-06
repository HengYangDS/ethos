"""Orientation reader view for humans and agents.

This module deliberately owns no repository truth. It derives a compact
orientation packet from the existing workspace-status and report payloads so a
human or agent can answer: where am I, what may I do, who else is present, what
is blocking, and which command should run next.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Mapping


def orientation_packet(
    *,
    status_payload: Mapping[str, Any],
    report_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact reader view from status/report truth payloads."""
    closeout = _dict(status_payload.get("closeout_support"))
    coordination = _dict(status_payload.get("coordination"))
    candidate = _dict(status_payload.get("candidate"))
    runtime = _dict(status_payload.get("runtime_binding"))
    landing = _dict(status_payload.get("landing_readiness"))
    role = str(status_payload.get("role") or "unknown")
    dirty = bool(status_payload.get("dirty"))
    changed_paths = _strings(status_payload.get("changed_paths"))
    foreign_lanes = [
        _foreign_lane_summary(cast("Mapping[str, Any]", item))
        for item in cast("list[object]", status_payload.get("foreign_work_lanes") or [])
        if isinstance(item, dict)
    ]
    unbound_refs = [
        _unbound_lane_ref_summary(cast("Mapping[str, Any]", item))
        for item in cast("list[object]", coordination.get("unbound_work_lane_refs") or [])
        if isinstance(item, dict)
    ]
    required_gaps = _strings(status_payload.get("required_gaps"))
    report_summary = _dict(report_payload.get("summary") if report_payload else None)
    report_required = _strings(report_payload.get("required_gaps") if report_payload else None)
    gaps = _dedupe([*required_gaps, *report_required])
    capability = _capability(role=role, dirty=dirty, closeout=closeout)
    next_actions = _next_actions(
        {
            "role": role,
            "dirty": dirty,
            "gaps": gaps,
            "closeout": closeout,
            "report_payload": report_payload,
        }
    )
    current_head = _current_head(status_payload, branch=str(status_payload.get("branch") or ""))
    return {
        "kind": "orientation",
        "truth_boundary": "repository-reader-view",
        "mints_truth": False,
        "source_payloads": ["status", *(["report"] if report_payload else [])],
        "where": {
            "root": str(status_payload.get("root") or ""),
            "branch": str(status_payload.get("branch") or ""),
            "role": role,
            "head": current_head,
            "dirty": dirty,
            "changed_path_count": len(changed_paths),
        },
        "capability": capability,
        "candidate": {
            "branch": str(candidate.get("branch") or ""),
            "head": str(candidate.get("head") or ""),
            "worktree_path": str(candidate.get("worktree_path") or ""),
            "worktree_exists": bool(candidate.get("worktree_exists")),
        },
        "coordination": {
            "blocking": bool(coordination.get("blocking")),
            "foreign_work_lane_count": int(coordination.get("foreign_work_lane_count") or 0),
            "unbound_work_lane_count": int(coordination.get("unbound_work_lane_count") or 0),
            "overlap_count": int(coordination.get("overlap_count") or 0),
            "advisory_items": _strings(coordination.get("advisory_gaps")),
            "required_items": _strings(coordination.get("required_gaps")),
            "next_action": str(coordination.get("next_action") or ""),
            "foreign_work_lanes": foreign_lanes,
            "unbound_work_lane_refs": unbound_refs,
        },
        "runtime_binding": {
            "state": str(runtime.get("state") or ""),
            "runner_source_root": str(runtime.get("runner_source_root") or ""),
            "schema_source_root": str(runtime.get("schema_source_root") or ""),
            "runner_matches_audit_root": bool(runtime.get("runner_matches_audit_root")),
            "schema_matches_audit_root": bool(runtime.get("schema_matches_audit_root")),
            "advisory_items": _strings(runtime.get("advisory_gaps")),
            "next_action": str(runtime.get("next_action") or ""),
        },
        "landing_readiness": {
            "state": str(landing.get("state") or ""),
            "candidate_branch": str(landing.get("candidate_branch") or ""),
            "candidate_head": str(landing.get("candidate_head") or ""),
            "required_items": _strings(landing.get("required_gaps")),
            "next_action": str(landing.get("next_action") or ""),
        },
        "readiness": {
            "status_items": required_gaps,
            "report_items": report_required,
            "governance_gap_count": int(report_summary.get("governance_gap_count") or 0),
            "parity_pending_count": int(report_summary.get("parity_pending_count") or 0),
            "score": int(report_summary.get("score") or 0),
            "max_score": int(report_summary.get("max_score") or 0),
        },
        "next_actions": next_actions,
        "human_summary": _human_summary(
            {
                "role": role,
                "dirty": dirty,
                "changed_count": len(changed_paths),
                "capability": capability,
                "foreign_count": len(foreign_lanes),
                "unbound_count": len(unbound_refs),
                "gaps": gaps,
                "next_actions": next_actions,
            }
        ),
        "agent_hints": {
            "mutation_requires_prewrite": True,
            "foreign_lanes_observe_only": bool(foreign_lanes),
            "use_json_for_evidence": True,
            "orientation_projection_only": True,
            "runner_binding_visible": bool(runtime),
            "landing_readiness_visible": bool(landing),
        },
    }


def human_orientation_lines(packet: Mapping[str, Any]) -> tuple[str, ...]:
    """Render a concise terminal orientation without hiding the JSON surface."""
    where = _dict(packet.get("where"))
    readiness = _dict(packet.get("readiness"))
    coordination = _dict(packet.get("coordination"))
    capability = _dict(packet.get("capability"))
    runtime = _dict(packet.get("runtime_binding"))
    landing = _dict(packet.get("landing_readiness"))
    head = str(where.get("head") or "")
    head_text = f" @ {head[:12]}" if head else ""
    lines = [
        str(packet.get("human_summary") or "orientation"),
        (
            f"where: {where.get('role')} on {where.get('branch')}{head_text} "
            f"({where.get('changed_path_count')} changed paths)"
        ),
        f"can: {capability.get('current_actor_capability')} — {capability.get('reason')}",
    ]
    max_score = int(readiness.get("max_score") or 0)
    if max_score:
        lines.append(
            "readiness: "
            f"score {readiness.get('score')}/{max_score}, "
            f"governance gaps {readiness.get('governance_gap_count')}, "
            f"parity pending {readiness.get('parity_pending_count')}"
        )
    else:
        lines.append("readiness: status-only view; run ethos report --json for scorecard")
    runtime_items = _strings(runtime.get("advisory_items"))
    if runtime_items:
        lines.append(f"runtime: {runtime.get('state')}; {runtime.get('next_action')}")
    landing_items = _strings(landing.get("required_items"))
    if landing_items:
        lines.append(f"landing: {landing.get('state')}; {landing.get('next_action')}")
    coordination_line = _coordination_line(coordination)
    if coordination_line:
        lines.append(coordination_line)
    next_actions = _strings(packet.get("next_actions"))
    if next_actions:
        lines.append("next: " + " | ".join(next_actions))
    return tuple(lines)


def _coordination_line(coordination: Mapping[str, Any]) -> str:
    parts: list[str] = []
    foreign_count = int(coordination.get("foreign_work_lane_count") or 0)
    unbound_count = int(coordination.get("unbound_work_lane_count") or 0)
    required_items = _strings(coordination.get("required_items"))
    if foreign_count:
        parts.append(f"{foreign_count} foreign lane(s)")
    if unbound_count:
        parts.append(f"{unbound_count} unbound ref(s)")
    if bool(coordination.get("blocking")) or required_items:
        parts.append("blocking")
    if not parts:
        return ""
    next_action = str(coordination.get("next_action") or "")
    suffix = f"; {next_action}" if next_action else ""
    return f"coordination: {', '.join(parts)}{suffix}"


def _dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return cast("dict[str, Any]", value)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value]


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))


def _current_head(status_payload: Mapping[str, Any], *, branch: str) -> str:
    direct_head = str(status_payload.get("head") or "")
    if direct_head:
        return direct_head
    for item in cast("list[object]", status_payload.get("branch_bindings") or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("branch") or "") == branch:
            return str(item.get("head") or "")
    return ""


def _foreign_lane_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "branch": str(item.get("branch") or ""),
        "path": str(item.get("path") or ""),
        "head": str(item.get("head") or ""),
        "claim_id": str(item.get("claim_id") or ""),
        "coordination_state": str(item.get("coordination_state") or ""),
        "current_actor_capability": str(item.get("current_actor_capability") or "observe"),
        "allowed_actions": _strings(item.get("allowed_actions")),
        "forbidden_actions": _strings(item.get("forbidden_actions")),
        "path_scope": _strings(item.get("path_scope")),
    }


def _unbound_lane_ref_summary(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "branch": str(item.get("branch") or ""),
        "head": str(item.get("head") or ""),
        "claim_id": str(item.get("claim_id") or ""),
        "claim_binding": str(item.get("claim_binding") or ""),
        "relation_to_accepted": str(item.get("relation_to_accepted") or ""),
        "next_action": str(item.get("next_action") or ""),
    }


def _capability(*, role: str, dirty: bool, closeout: Mapping[str, Any]) -> dict[str, Any]:
    capability = {
        "current_actor_capability": "unknown",
        "can_mutate_tracked_files": False,
        "can_land": False,
        "reason": "checkout role is not admitted for mutation",
    }
    if dirty:
        capability = {
            "current_actor_capability": "repair_or_commit_current_changes",
            "can_mutate_tracked_files": role == "work_lane",
            "can_land": False,
            "reason": "checkout is dirty; inspect dirty provenance before new work",
        }
    elif role == "work_lane":
        capability = {
            "current_actor_capability": "write_lane",
            "can_mutate_tracked_files": True,
            "can_land": bool(closeout.get("supported")),
            "reason": "owned Work Lane; run prewrite before tracked mutation",
        }
    elif role in {"accepted_root", "candidate", "release_root"}:
        capability = {
            "current_actor_capability": "observe",
            "can_mutate_tracked_files": False,
            "can_land": False,
            "reason": f"{role} is protected for normal edits",
        }
    return capability


def _next_actions(context: Mapping[str, Any]) -> list[str]:
    role = str(context["role"])
    closeout = _dict(context.get("closeout"))
    gaps = _strings(context.get("gaps"))
    report_payload = context.get("report_payload")
    actions = ["ethos status --json"]
    if context.get("dirty") is True:
        actions = ["ethos status --json", "git status --short"]
    elif gaps:
        actions = [f"ethos explain {gaps[0]} --json", "ethos report --json"]
    elif role == "work_lane" and closeout.get("supported") is True:
        actions = [
            "ethos plan --changed --json",
            "ethos prove --execute --expect-head $(git rev-parse HEAD) --json",
            "ethos land --json",
        ]
    elif role == "work_lane":
        actions = ["ethos lane bind-claim --claim-id <claim> --apply --json"]
    elif role == "accepted_root":
        actions = ["ethos lane start <name> --path <path> --owner <owner> --apply --json"]
    elif role == "candidate":
        actions = ["ethos land --closeout --json"]
    elif isinstance(report_payload, dict):
        actions = _strings(report_payload.get("next_actions")) or actions
    return actions


def _human_summary(context: Mapping[str, Any]) -> str:
    dirty = bool(context["dirty"])
    gaps = _strings(context.get("gaps"))
    capability = _dict(context["capability"])
    next_actions = _strings(context.get("next_actions"))
    state = "dirty" if dirty else "gapped" if gaps else "ready"
    actor = capability.get("current_actor_capability")
    foreign_count = int(context["foreign_count"])
    unbound_count = int(context["unbound_count"])
    foreign = f", {foreign_count} foreign lane(s) visible" if foreign_count else ""
    unbound = f", {unbound_count} unbound ref(s) visible" if unbound_count else ""
    next_action = f"; next: {next_actions[0]}" if next_actions else ""
    return (
        f"{state}: {context['role']}, {context['changed_count']} changed path(s), "
        f"capability={actor}{foreign}{unbound}{next_action}"
    )
