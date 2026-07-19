"""Repository orientation reader view for humans and agents."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos_core.normalization.core import string_sequence

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

# fmt: off

_FOREIGN_SPEC = (
    "branch:s path:s head:s lease:d lease_state:s claim_id:s claim_binding:s "
    "closeout_disposition:s residue_state:s next_action:s coordination_state:s "
    "action_preview:d path_scope:l dirty:o"
)
_UNBOUND_SPEC = "branch:s head:s claim_id:s claim_binding:s relation_to_accepted:s next_action:s"
_RESIDUE_SPEC = "branch:s closeout_disposition:s residue_state:s dirty:b"


def orientation_packet(
    *, status_payload: Mapping[str, Any], report_payload: Mapping[str, Any] | None = None,
    command_prefix: str = "",
) -> dict[str, Any]:
    """Derive the compact orientation contract from status and report truth."""
    closeout, coordination = _dict(status_payload.get("closeout_support")), _dict(
        status_payload.get("coordination")
    )
    coordination_detail_state = str(coordination.get("detail_state") or "exact")
    candidate, runtime = _dict(status_payload.get("candidate")), _dict(
        status_payload.get("runtime_binding")
    )
    landing = _dict(status_payload.get("landing_readiness"))
    role, dirty = str(status_payload.get("role") or "unknown"), bool(status_payload.get("dirty"))
    changed_paths = string_sequence(status_payload.get("changed_paths"))
    foreign_lanes = _summaries(status_payload.get("foreign_work_lanes"), _FOREIGN_SPEC)
    unbound_refs = _summaries(coordination.get("unbound_work_lane_refs"), _UNBOUND_SPEC)
    required_gaps = string_sequence(status_payload.get("required_gaps"))
    report_summary = _dict(report_payload.get("summary") if report_payload else None)
    report_required = string_sequence(
        report_payload.get("required_gaps") if report_payload else None
    )
    report_advisory = _report_values(report_payload, "advisory_gaps")
    advisory_actions = _report_values(report_payload, "next_actions")
    gaps = _dedupe([*required_gaps, *report_required])
    temporary_probes = _temporary_probes(status_payload)
    capability = _capability(
        role=role, dirty=dirty, closeout=closeout,
        temporary_probe_count=int(temporary_probes["count"]),
    )
    next_actions = _bound_actions(
        _next_actions({
            "role": role, "dirty": dirty, "gaps": gaps, "closeout": closeout,
            "report_payload": report_payload, "advisory_next_actions": advisory_actions,
            "temporary_probe_count": temporary_probes["count"],
        }),
        command_prefix=command_prefix,
    )
    dirty_foreign = _coordination_count(
        coordination, "dirty_foreign_work_lane_count",
        fallback=sum(lane.get("dirty") is True for lane in foreign_lanes),
    )
    advisory_count = int(report_summary.get("advisory_gap_count") or len(report_advisory))
    coordination_view = _project(
        coordination,
        "blocking:b foreign_work_lane_count:i unbound_work_lane_count:i missing_lease_count:i "
        "advisory_items:l:advisory_gaps required_items:l:required_gaps next_action:s",
    )
    coordination_view.update({
        "detail_state": coordination_detail_state,
        "dirty_foreign_work_lane_count": dirty_foreign,
        "overlap_count": _coordination_count(coordination, "overlap_count"),
        "closeout_residue_count": _coordination_count(coordination, "closeout_residue_count"),
        "dirty_closeout_residue_count": _coordination_count(
            coordination, "dirty_closeout_residue_count"
        ),
        "closeout_residue_lanes": _summaries(
            coordination.get("closeout_residue_lanes"), _RESIDUE_SPEC
        ),
        "foreign_work_lanes": foreign_lanes, "unbound_work_lane_refs": unbound_refs,
    })
    readiness = _project(
        report_summary, "governance_gap_count:i parity_pending_count:i score:i max_score:i"
    )
    readiness.update({
        "status_items": required_gaps, "report_items": report_required,
        "advisory_gap_count": advisory_count, "advisory_items": report_advisory,
        "advisory_next_actions": advisory_actions,
    })
    summary_context = {
        "role": role, "dirty": dirty, "changed_count": len(changed_paths),
        "capability": capability, "foreign_count": len(foreign_lanes),
        "unbound_count": len(unbound_refs),
        "missing_lease_count": coordination_view["missing_lease_count"],
        "coordination_detail_state": coordination_detail_state,
        "dirty_foreign_count": dirty_foreign,
        "closeout_residue_count": coordination_view["closeout_residue_count"],
        "gaps": gaps, "advisory_count": advisory_count, "next_actions": next_actions,
    }
    return {
        "kind": "orientation", "truth_boundary": "repository-reader-view", "mints_truth": False,
        "source_payloads": ["status", *(["report"] if report_payload else [])],
        "where": {
            "root": str(status_payload.get("root") or ""),
            "branch": str(status_payload.get("branch") or ""), "role": role,
            "head": _current_head(status_payload, branch=str(status_payload.get("branch") or "")),
            "dirty": dirty, "changed_path_count": len(changed_paths),
        },
        "capability": capability, "temporary_probes": temporary_probes,
        "candidate": _project(candidate, "branch:s head:s worktree_path:s worktree_exists:b"),
        "coordination": coordination_view,
        "runtime_binding": _project(
            runtime, "state:s runner_source_root:s schema_source_root:s "
            "runner_matches_audit_root:b schema_matches_audit_root:b "
            "advisory_items:l:advisory_gaps next_action:s"
        ),
        "landing_readiness": _project(
            landing, "state:s candidate_branch:s candidate_head:s "
            "required_items:l:required_gaps next_action:s"
        ),
        "readiness": readiness, "next_actions": next_actions,
        "human_summary": _human_summary(summary_context),
        "agent_hints": {
            "mutation_requires_prewrite": True, "foreign_lanes_observe_only": bool(foreign_lanes),
            "use_json_for_evidence": True, "orientation_projection_only": True,
            "runner_binding_visible": bool(runtime), "landing_readiness_visible": bool(landing),
        },
    }


def human_orientation_lines(packet: Mapping[str, Any]) -> tuple[str, ...]:
    """Render a concise terminal orientation without hiding the JSON surface."""
    where, readiness = _dict(packet.get("where")), _dict(packet.get("readiness"))
    coordination, capability = _dict(packet.get("coordination")), _dict(packet.get("capability"))
    runtime, landing = _dict(packet.get("runtime_binding")), _dict(packet.get("landing_readiness"))
    head = str(where.get("head") or "")
    lines = [
        str(packet.get("human_summary") or "orientation"),
        f"where: {where.get('role')} on {where.get('branch')}"
        f"{f' @ {head[:12]}' if head else ''} ({where.get('changed_path_count')} changed paths)",
        f"can: {capability.get('candidate_action')} — {capability.get('reason')}",
    ]
    max_score = int(readiness.get("max_score") or 0)
    if max_score:
        advisory_count = int(readiness.get("advisory_gap_count") or 0)
        lines.append(
            f"readiness: score {readiness.get('score')}/{max_score}, "
            f"governance gaps {readiness.get('governance_gap_count')}, "
            f"parity pending {readiness.get('parity_pending_count')}"
            f"{f', advisory signals {advisory_count}' if advisory_count else ''}"
        )
    else:
        lines.append("readiness: status-only view; run ethos report --json for scorecard")
    for label, section, item_key in (
        ("runtime", runtime, "advisory_items"), ("landing", landing, "required_items")
    ):
        if string_sequence(section.get(item_key)):
            lines.append(f"{label}: {section.get('state')}; {section.get('next_action')}")
    if coordination_line := _coordination_line(coordination):
        lines.append(coordination_line)
    if actions := string_sequence(packet.get("next_actions")):
        lines.append("next: " + " | ".join(actions))
    return tuple(lines)


def _coordination_line(coordination: Mapping[str, Any]) -> str:
    foreign_count, unbound_count = (
        int(coordination.get(name) or 0)
        for name in ("foreign_work_lane_count", "unbound_work_lane_count")
    )
    detail = _lane_detail(
        coordination, deferred_label="detail deferred; run ethos lane status --json"
    )
    parts = [f"{foreign_count} foreign lane(s){detail}"] if foreign_count else []
    if unbound_count:
        parts.append(f"{unbound_count} unbound ref(s)")
    if bool(coordination.get("blocking")) or string_sequence(coordination.get("required_items")):
        parts.append("blocking")
    action = str(coordination.get("next_action") or "")
    return f"coordination: {', '.join(parts)}{f'; {action}' if action else ''}" if parts else ""


def _project(value: object, spec: str) -> dict[str, Any]:
    source, result = _dict(value), {}
    converters: dict[str, Callable[[object], Any]] = {
        "s": lambda item: str(item or ""), "b": bool,
        "i": lambda item: int(cast("int | str", item or 0)),
        "o": lambda item: item if isinstance(item, bool) else None,
        "l": string_sequence, "d": _dict,
    }
    for token in spec.split():
        output, kind, *source_name = token.split(":")
        result[output] = converters[kind](source.get(source_name[0] if source_name else output))
    return result


def _summaries(value: object, spec: str) -> list[dict[str, Any]]:
    return [
        _project(item, spec)
        for item in cast("list[object]", value or []) if isinstance(item, dict)
    ]


def _coordination_count(
    coordination: Mapping[str, Any], key: str, *, fallback: int = 0,
) -> int | None:
    if str(coordination.get("detail_state") or "exact") == "deferred":
        return None
    value = coordination.get(key)
    return fallback if value is None else int(cast("int | str", value))


def _report_values(report_payload: Mapping[str, Any] | None, key: str) -> list[str]:
    if not isinstance(report_payload, dict):
        return []
    data = _dict(report_payload.get("data"))
    layered = _dict(_dict(data.get("gap_layers")).get("advisory_signals"))
    return string_sequence(layered.get(key)) or string_sequence(
        _dict(data.get("advisory_signals")).get(key)
    )


def _dict(value: object) -> dict[str, Any]:
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


def _temporary_probes(status_payload: Mapping[str, Any]) -> dict[str, Any]:
    summary = _dict(_dict(status_payload.get("dirty_provenance")).get("temporary_probes"))
    return {
        "count": _nonnegative_int(summary.get("count")),
        "paths": string_sequence(summary.get("paths")),
        "truncated": bool(summary.get("truncated")), "automated_cleanup": False,
    }


def _nonnegative_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, int(cast("int | str", value)))
    except (TypeError, ValueError):
        return 0


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(filter(None, values)))


def _current_head(status_payload: Mapping[str, Any], *, branch: str) -> str:
    if head := str(status_payload.get("head") or ""):
        return head
    return next((
        str(item.get("head") or "")
        for item in cast("list[object]", status_payload.get("branch_bindings") or [])
        if isinstance(item, dict) and str(item.get("branch") or "") == branch
    ), "")


def _capability(
    *, role: str, dirty: bool, closeout: Mapping[str, Any], temporary_probe_count: int
) -> dict[str, Any]:
    if temporary_probe_count and role in {"accepted_root", "candidate"}:
        action, mutate, reason = (
            "remove_or_migrate_temporary_probe", False,
            "temporary test probe detected; remove it or migrate it into an owned Work Lane; "
            "no automated cleanup",
        )
    elif dirty:
        action, mutate, reason = (
            "repair_or_commit_current_changes", role == "work_lane",
            "checkout is dirty; inspect dirty provenance before new work",
        )
    elif role == "work_lane":
        action, mutate, reason = (
            "write_lane", True, "owned Work Lane; run prewrite before tracked mutation"
        )
    elif role in {"accepted_root", "candidate", "release_root"}:
        action, mutate, reason = "observe", False, f"{role} is protected for normal edits"
    else:
        action, mutate, reason = "unknown", False, "checkout role is not admitted for mutation"
    return {
        "candidate_action": action, "can_mutate_tracked_files": mutate,
        "can_land": bool(closeout.get("supported")) if action == "write_lane" else False,
        "reason": reason,
    }


def _next_actions(context: Mapping[str, Any]) -> list[str]:
    role, closeout = str(context["role"]), _dict(context.get("closeout"))
    gaps, report_payload = string_sequence(context.get("gaps")), context.get("report_payload")
    actions = ["ethos status --json"]
    temporary_probe = _nonnegative_int(context.get("temporary_probe_count"))
    if temporary_probe and role in {"accepted_root", "candidate"}:
        actions = [
            "remove the temporary probe or migrate it into an owned Work Lane; "
            "no automatic cleanup",
            "inspect dirty_provenance.temporary_probes in ethos status --json",
        ]
    elif context.get("dirty") is True:
        actions.append("git status --short")
    elif gaps:
        actions = [f"ethos explain {gaps[0]} --json", "ethos report --json"]
    elif role == "work_lane":
        actions = ([
            "ethos plan --changed --json",
            "ethos prove --execute --expect-head $(git rev-parse HEAD) --json",
            "ethos land --json",
        ] if closeout.get("supported") is True else [
            "ethos lane bind-claim --claim-id <claim> --apply --json"
        ])
    elif role == "accepted_root":
        actions = [
            "ethos lane start <name> --path <path> "
            "--holder-ref <kind:namespace:instance-kind:id> --apply --json"
        ]
    elif role == "candidate":
        actions = ["ethos land --closeout --json"]
    elif isinstance(report_payload, dict):
        actions = string_sequence(report_payload.get("next_actions")) or actions
    return _dedupe([*actions, *string_sequence(context.get("advisory_next_actions"))])


def _bound_actions(actions: list[str], *, command_prefix: str) -> list[str]:
    if not command_prefix:
        return actions
    checkout = command_prefix.removeprefix("cd ").split(" && ", 1)[0]
    return [
        f"{command_prefix} {action.removeprefix('ethos ')}"
        if action.startswith("ethos ") else f"cd {checkout} && {action}"
        for action in actions
    ]


def _lane_detail(values: Mapping[str, Any], *, deferred_label: str = "detail deferred") -> str:
    detail_state = str(
        values.get("detail_state") or values.get("coordination_detail_state") or "exact"
    )
    if detail_state == "deferred":
        return f" ({deferred_label})"
    details = [
        f"{values.get(key)} {label}"
        for key, label in (
            ("missing_lease_count", "missing lease"),
            ("dirty_foreign_work_lane_count", "dirty"),
            ("closeout_residue_count", "closeout residue"),
        ) if int(values.get(key) or 0)
    ]
    return f" ({', '.join(details)})" if details else ""


def _human_summary(context: Mapping[str, Any]) -> str:
    dirty, gaps = bool(context["dirty"]), string_sequence(context.get("gaps"))
    capability, next_actions = _dict(context["capability"]), string_sequence(
        context.get("next_actions")
    )
    foreign_count, unbound_count = int(context["foreign_count"]), int(context["unbound_count"])
    state = "dirty" if dirty else "gapped" if gaps else "ready"
    lane_detail = {
        "coordination_detail_state": context.get("coordination_detail_state"),
        "missing_lease_count": context.get("missing_lease_count"),
        "dirty_foreign_work_lane_count": context.get("dirty_foreign_count"),
        "closeout_residue_count": context.get("closeout_residue_count"),
    }
    foreign = (
        f", {foreign_count} foreign lane(s) visible{_lane_detail(lane_detail)}"
        if foreign_count else ""
    )
    unbound = f", {unbound_count} unbound ref(s) visible" if unbound_count else ""
    advisory_count = int(context.get("advisory_count") or 0)
    advisory = f", {advisory_count} advisory signal(s)" if advisory_count else ""
    next_action = f"; next: {next_actions[0]}" if next_actions else ""
    return (
        f"{state}: {context['role']}, {context['changed_count']} changed path(s), "
        f"capability={capability.get('candidate_action')}{foreign}{unbound}{advisory}{next_action}"
    )
# fmt: on
