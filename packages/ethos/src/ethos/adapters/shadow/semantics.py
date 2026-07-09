from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.shadow.planning as shadow_planning

if TYPE_CHECKING:
    from collections.abc import Iterable

SEMANTIC_DIMENSIONS = [
    "branch_role",
    "mutation_allowed",
    "changed_path_classification",
    "required_gates",
    "required_gaps",
    "assistant_boundary",
    "evidence_freshness",
    "land_readiness",
    "publish_readiness",
    "blocking_vs_advisory",
    "external_false_negative",
]

STATUS_ROLE_ALIASES = {
    "integration_candidate": "candidate",
    "isolated_lane": "work_lane",
}


def semantic_diff(*args: Any) -> dict[str, Any]:
    command, external, embedded = _semantic_args(args)
    external_projection, embedded_projection, _accepted = _normalized_semantic_projections(
        command,
        external,
        embedded,
    )
    diff = {}
    for key in sorted(set(external_projection) | set(embedded_projection)):
        external_value = external_projection.get(key)
        embedded_value = embedded_projection.get(key)
        if embedded_value != external_value:
            diff[key] = {"external": external_value, "embedded": embedded_value}
    return diff


def false_negative_gaps(
    command: tuple[str, ...],
    external: dict[str, Any],
    embedded: dict[str, Any],
) -> list[str]:
    external_projection, embedded_projection, _accepted = _normalized_semantic_projections(
        command,
        external,
        embedded,
    )
    external_required = set(_gap_list(external_projection.get("required_gaps")))
    embedded_required = set(_gap_list(embedded_projection.get("required_gaps")))
    return sorted(embedded_required - external_required)


def accepted_semantic_differences(*args: Any) -> list[dict[str, Any]]:
    command, external, embedded = _semantic_args(args)
    _external_projection, _embedded_projection, accepted = _normalized_semantic_projections(
        command,
        external,
        embedded,
    )
    return accepted


def accepted_summary(differences: Iterable[object]) -> dict[str, Any]:
    items = list(differences) if not isinstance(differences, list) else differences
    kind_counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        if not kind:
            continue
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    return {
        "total_count": sum(kind_counts.values()),
        "kind_counts": dict(sorted(kind_counts.items())),
    }


def _semantic_args(args: tuple[Any, ...]) -> tuple[tuple[str, ...], dict[str, Any], dict[str, Any]]:
    if len(args) == 3:
        command = tuple(str(item) for item in args[0])
        return command, args[1], args[2]
    if len(args) == 2:
        command_name = str(args[0].get("command") or args[1].get("command") or "")
        return tuple(command_name.split()), args[0], args[1]
    message = "semantic_diff expects external/embedded or command/external/embedded"
    raise TypeError(message)


def _normalized_semantic_projections(
    command: tuple[str, ...],
    external: dict[str, Any],
    embedded: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    external_projection = _semantic_projection(command, external)
    embedded_projection = _semantic_projection(command, embedded)
    accepted: list[dict[str, Any]] = []
    embedded_gaps = _gap_list(embedded_projection.get("required_gaps"))
    external_gaps = _gap_list(external_projection.get("required_gaps"))
    if embedded_gaps:
        missing_embedded_gaps = sorted(set(embedded_gaps) - set(external_gaps))
        external_extra_gaps = sorted(set(external_gaps) - set(embedded_gaps))
        if external_extra_gaps and not missing_embedded_gaps:
            accepted.append(
                _accepted_difference(
                    "external_required_gap_superset",
                    command=external_projection.get("command"),
                    gaps=external_extra_gaps,
                )
            )
            external_gaps = embedded_gaps
    else:
        external_gaps, repository_audit_gaps = _without_product_repository_audit_gaps(
            external,
            external_gaps,
        )
        if repository_audit_gaps:
            accepted.append(
                _accepted_difference(
                    "external_product_repository_audit_gap",
                    command=external_projection.get("command"),
                    gaps=repository_audit_gaps,
                )
            )
        external_gaps, route_gaps = _without_changed_route_noop_gaps(
            external,
            embedded,
            external_gaps,
        )
        if route_gaps:
            accepted.append(
                _accepted_difference(
                    "changed_route_noop",
                    command=external_projection.get("command"),
                    gaps=route_gaps,
                )
            )
        report_gaps = _report_parity_evidence_refresh_bootstrap_gaps(
            external,
            embedded,
            external_projection,
            embedded_projection,
        )
        if report_gaps:
            accepted.append(
                _accepted_difference(
                    "report_parity_evidence_refresh_bootstrap",
                    command=external_projection.get("command"),
                    gaps=report_gaps,
                )
            )
        plan_scope_gaps = shadow_planning.external_stricter_gaps(
            command,
            external_projection,
            embedded_projection,
        )
        if plan_scope_gaps:
            accepted.append(
                _accepted_difference(
                    "external_stricter_plan_scope",
                    command=external_projection.get("command"),
                    gaps=plan_scope_gaps,
                )
            )
            shadow_planning.normalize_external(external_projection, embedded_projection)
        external_gaps, stricter_gaps = _without_external_stricter_only_gaps(
            command,
            external_gaps,
        )
        if stricter_gaps:
            accepted.append(
                _accepted_difference(
                    "external_stricter_required_gap",
                    command=external_projection.get("command"),
                    gaps=stricter_gaps,
                )
            )
    external_projection["required_gaps"] = sorted(external_gaps)
    if accepted and not external_gaps and not embedded_gaps:
        external_projection["ok"] = True
        external_projection["state"] = _ready_state_for_command(external_projection.get("command"))
        _mark_projection_ready(external_projection)
    return external_projection, embedded_projection, accepted


def _accepted_difference(kind: str, *, command: object, gaps: list[str]) -> dict[str, Any]:
    if kind == "external_product_repository_audit_gap":
        scope = "external_product_repository_audit"
        reason = "external product repository audit gap is not an embedded adopter parity gap"
    elif kind == "changed_route_noop":
        scope = "changed_scope_route"
        reason = "changed-scope route has no changed paths to route"
    elif kind == "report_parity_evidence_refresh_bootstrap":
        scope = "parity_evidence_refresh"
        reason = "report parity freshness is being refreshed by the current shadow run"
    elif kind == "external_required_gap_superset":
        scope = "external_required_gap_superset"
        reason = "external product reports the embedded blocking gaps plus stricter required gaps"
    elif kind == "external_stricter_required_gap":
        scope = "external_stricter_required_gap"
        reason = "external product reports a stricter blocking gap allowed by shadow parity"
    elif kind == "external_stricter_plan_scope":
        scope = "external_stricter_plan_scope"
        reason = "external product plans a stricter changed-scope gate set allowed by shadow parity"
    else:
        scope = "unknown"
        reason = "unclassified accepted difference"
    return {
        "kind": kind,
        "classification": "accepted",
        "scope": scope,
        "commands": [_command_label(command)],
        "gaps": sorted(set(gaps)),
        "reason": reason,
    }


def _command_label(command: object) -> str:
    text = str(command or "").strip()
    return text if text.startswith("ethos ") else f"ethos {text}".strip()


def _semantic_projection(command: tuple[str, ...], payload: dict[str, Any]) -> dict[str, Any]:
    summary_value = payload.get("summary")
    summary = summary_value if isinstance(summary_value, dict) else {}
    data_value = payload.get("data")
    data = data_value if isinstance(data_value, dict) else {}
    command_name = _command_name(command, payload, summary)
    state = _semantic_state(payload, summary=summary, command=command_name)
    projection: dict[str, Any] = {
        "ok": payload.get("ok"),
        "command": command_name,
        "state": state,
        "required_gaps": sorted(_gap_list(payload.get("required_gaps"))),
    }
    command_root = command[0] if command else command_name.split()[0] if command_name else ""
    if command_root == "status":
        changed_paths = _first_list(data.get("changed_paths"), payload.get("changed_paths"))
        dirty = _first_present(
            data.get("dirty"),
            summary.get("dirty"),
            payload.get("dirty"),
        )
        if dirty is None and state == "ready":
            dirty = False
        role = payload.get("role") or summary.get("role") or data.get("role")
        projection.update(
            {
                "role": _canonical_status_role(role),
                "dirty": dirty,
                "changed_path_count": len(changed_paths),
            }
        )
    elif command_root == "plan":
        required_gates = _first_list(data.get("required_gates"), payload.get("required_gates"))
        projection.update(
            {
                "changed_path_count": len(
                    _first_list(data.get("changed_paths"), payload.get("changed_paths"))
                ),
                "matched_rule_ids": sorted(
                    str(rule.get("id"))
                    for rule in _first_list(data.get("matched_rules"), payload.get("matched_rules"))
                    if isinstance(rule, dict)
                ),
                "required_gate_ids": _gate_ids(required_gates),
            }
        )
    elif command_root == "prove":
        projection.update(
            {"proof_ready": bool(payload.get("ok")) and not payload.get("required_gaps")}
        )
    elif command_root == "report":
        projection.update(
            {
                "blocking_gap_count": summary.get("blocking_gap_count")
                if summary.get("blocking_gap_count") is not None
                else len(payload.get("required_gaps", [])),
            }
        )
    elif command_root == "quality":
        projection.update(
            {
                "retired_violation_count": summary.get("retired_violation_count")
                or len(_list(data.get("retired_public_root_mentions"))),
            }
        )
    elif command_root == "assistants":
        projection.update({"assistant_ready": bool(payload.get("ok"))})
    elif command_root == "playbooks":
        projection.update({"route_ready": bool(payload.get("ok"))})
    elif command_root in {"land", "publish"}:
        remote_push = data.get("remote_push") or summary.get("remote_push")
        projection.update(
            {
                "readiness": bool(payload.get("ok")) and not payload.get("required_gaps"),
                "remote_push": remote_push,
            }
        )
    return projection


def _mark_projection_ready(projection: dict[str, Any]) -> None:
    command = projection.get("command")
    if command == "prove":
        projection["proof_ready"] = True
    elif command == "report":
        projection["blocking_gap_count"] = 0
    elif command == "quality command-surface":
        projection["retired_violation_count"] = 0
    elif command == "assistants doctor":
        projection["assistant_ready"] = True
    elif command == "playbooks route":
        projection["route_ready"] = True
    elif command in {"land", "publish"}:
        projection["readiness"] = True


def _command_name(
    command: tuple[str, ...],
    payload: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    explicit = payload.get("command") or summary.get("command")
    if explicit:
        return str(explicit)
    if command[:2] == ("assistants", "doctor"):
        return "assistants doctor"
    if command[:2] == ("playbooks", "route"):
        return "playbooks route"
    if command[:2] == ("quality", "command-surface"):
        return "quality command-surface"
    return command[0] if command else ""


def _semantic_state(
    payload: dict[str, Any],
    *,
    summary: dict[str, Any],
    command: object,
) -> object:
    state = payload.get("state")
    if isinstance(state, str):
        if (
            payload.get("ok") is True
            and command == "prove"
            and state == "ready"
            and not _gap_list(payload.get("required_gaps"))
        ):
            return "proven"
        return state
    if payload.get("ok") is not True:
        return state
    if command == "status":
        dirty = payload.get("dirty", summary.get("dirty", False))
        return "dirty" if dirty else "ready"
    ready_state = _ready_state_for_command(command)
    if ready_state is not None:
        return ready_state
    return state


def _ready_state_for_command(command: object) -> str | None:
    if command == "plan":
        return "planned"
    if command == "assistants doctor":
        return "ready"
    if command == "prove":
        return "proven"
    if command == "report":
        return "ready"
    if command == "quality command-surface":
        return "clean"
    if command == "playbooks route":
        return "routed"
    if command == "land":
        return "ready_to_land"
    if command == "publish":
        return "local_publish_ready"
    return None


def _gap_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _without_product_repository_audit_gaps(
    payload: dict[str, Any],
    gaps: list[str],
) -> tuple[list[str], list[str]]:
    data_value = payload.get("data")
    data = data_value if isinstance(data_value, dict) else {}
    repository_audit_value = data.get("repository_audit")
    repository_audit = repository_audit_value if isinstance(repository_audit_value, dict) else {}
    audit_gaps = {
        gap
        for gap in _gap_list(repository_audit.get("required_gaps"))
        if _is_product_repository_audit_gap(gap)
    }
    if not audit_gaps:
        return gaps, []
    filtered = [gap for gap in gaps if gap not in audit_gaps]
    removed = [gap for gap in gaps if gap in audit_gaps]
    return filtered, removed


_EXTERNAL_STRICTER_ONLY_GAPS: dict[tuple[str, ...], set[str]] = {
    ("land",): {"candidate_base_stale", "protected_root_mutation", "work_lane_dirty"},
    ("publish",): {"protected_root_mutation"},
}

_EXTERNAL_STRICTER_ONLY_GAP_PREFIXES: dict[tuple[str, ...], tuple[str, ...]] = {
    ("quality", "command-surface"): (
        "retired_public_command_prefix_mention:",
        "retired_public_root_mention:",
    ),
    ("playbooks", "route", "--changed"): ("playbook_changed_path_unmatched:.ethos/",),
}


def _without_external_stricter_only_gaps(
    command: tuple[str, ...],
    gaps: list[str],
) -> tuple[list[str], list[str]]:
    allowed = _EXTERNAL_STRICTER_ONLY_GAPS.get(command, set())
    allowed_prefixes = _EXTERNAL_STRICTER_ONLY_GAP_PREFIXES.get(command, ())
    if not allowed and not allowed_prefixes:
        return gaps, []
    filtered = [gap for gap in gaps if gap not in allowed and not gap.startswith(allowed_prefixes)]
    removed = [gap for gap in gaps if gap in allowed or gap.startswith(allowed_prefixes)]
    return filtered, removed


_PRODUCT_REPOSITORY_AUDIT_GAP_PREFIXES = (
    "docs/",
    "schemas/",
    "packages/",
    "distribution_adapter_missing:",
    "adoption_scaffold_missing:",
    "openspec_family_missing:",
    "claims_",
    "claim_",
    "schema_",
    "openspec_",
    "command_",
)


def _is_product_repository_audit_gap(gap: str) -> bool:
    return gap.startswith(_PRODUCT_REPOSITORY_AUDIT_GAP_PREFIXES)


def _without_changed_route_noop_gaps(
    external: dict[str, Any],
    embedded: dict[str, Any],
    gaps: list[str],
) -> tuple[list[str], list[str]]:
    if not _is_changed_route_noop(external, embedded, gaps):
        return gaps, []
    filtered = [gap for gap in gaps if not _is_changed_route_noop_gap(gap)]
    removed = [gap for gap in gaps if _is_changed_route_noop_gap(gap)]
    return filtered, removed


def _is_changed_route_noop_gap(gap: str) -> bool:
    return gap in {
        "skill_missing_id",
        "playbook_route_missing:changed-scope",
    } or gap.startswith("playbook_activation_unsupported_version:")


def _is_changed_route_noop(
    external: dict[str, Any],
    embedded: dict[str, Any],
    gaps: list[str],
) -> bool:
    external_data_value = external.get("data")
    external_data = external_data_value if isinstance(external_data_value, dict) else {}
    embedded_summary_value = embedded.get("summary")
    embedded_summary = embedded_summary_value if isinstance(embedded_summary_value, dict) else {}
    return (
        (external.get("command") or external_data.get("command")) == "playbooks route"
        and external_data.get("subject") == "changed-scope"
        and embedded_summary.get("changed_requested") is True
        and embedded_summary.get("changed_path_count") == 0
        and bool(gaps)
        and all(_is_changed_route_noop_gap(gap) for gap in gaps)
    )


def _report_parity_evidence_refresh_bootstrap_gaps(
    external: dict[str, Any],
    embedded: dict[str, Any],
    external_projection: dict[str, Any],
    embedded_projection: dict[str, Any],
) -> list[str]:
    external_summary_value = external.get("summary")
    external_summary = external_summary_value if isinstance(external_summary_value, dict) else {}
    parity_pending_count = external_summary.get("parity_pending_count")
    governance_gap_count = external_summary.get("governance_gap_count")
    if not isinstance(parity_pending_count, int) or parity_pending_count <= 0:
        return []
    if governance_gap_count not in (None, 0):
        return []
    if external_projection.get("command") != "report":
        return []
    if embedded_projection.get("command") != "report":
        return []
    if external_projection.get("required_gaps") or embedded_projection.get("required_gaps"):
        return []
    if external_projection.get("ok") is not False or embedded_projection.get("ok") is not True:
        return []
    if external_projection.get("state") != "gapped":
        return []
    if embedded_projection.get("state") != "ready":
        return []
    return [f"parity_pending_count:{parity_pending_count}"]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _canonical_status_role(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return STATUS_ROLE_ALIASES.get(value, value)


def _first_list(*values: Any) -> list[Any]:
    for value in values:
        if isinstance(value, list):
            return value
    return []


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _gate_ids(value: Any) -> list[str]:
    return sorted({str(gate.get("id")) for gate in _list(value) if isinstance(gate, dict)})
