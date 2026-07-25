# ruff: noqa: E501 - source-budget closeout keeps equivalent semantic projections compact.
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.shadow.planning as shadow_planning
from ethos.normalization.core import string_list

if TYPE_CHECKING:
    from collections.abc import Iterable

# fmt: off
SEMANTIC_DIMENSIONS = ["branch_role", "mutation_allowed", "changed_path_classification", "required_gates", "required_gaps", "assistant_boundary", "evidence_freshness", "land_readiness", "publish_readiness", "blocking_vs_advisory", "external_false_negative"]
STATUS_ROLE_ALIASES = {"integration_candidate": "candidate", "isolated_lane": "work_lane"}
_ACCEPTED_METADATA = {
    "external_product_repository_audit_gap": ("external_product_repository_audit", "external product repository audit gap is not an embedded adopter parity gap"),
    "changed_route_noop": ("changed_scope_route", "changed-scope route has no changed paths to route"),
    "report_parity_evidence_refresh_bootstrap": ("parity_evidence_refresh", "report parity freshness is being refreshed by the current shadow run"),
    "external_required_gap_superset": ("external_required_gap_superset", "external product reports the embedded blocking gaps plus stricter required gaps"),
    "external_stricter_required_gap": ("external_stricter_required_gap", "external product reports a stricter blocking gap allowed by shadow parity"),
    "external_stricter_plan_scope": ("external_stricter_plan_scope", "external product plans a stricter changed-scope gate set allowed by shadow parity"),
}
_READY_STATES = {"plan": "planned", "assistants doctor": "ready", "prove": "proven", "report": "ready", "quality command-surface": "clean", "playbooks route": "routed", "land": "ready_to_land", "publish": "local_publish_ready"}
_READY_MARKS = {"prove": ("proof_ready", True), "report": ("blocking_gap_count", 0), "quality command-surface": ("retired_violation_count", 0), "assistants doctor": ("assistant_ready", True), "playbooks route": ("route_ready", True), "land": ("readiness", True), "publish": ("readiness", True)}
_COMMAND_NAMES = {("assistants", "doctor"): "assistants doctor", ("playbooks", "route"): "playbooks route", ("quality", "command-surface"): "quality command-surface"}
_EXTERNAL_STRICTER_ONLY_GAPS = {("land",): {"candidate_base_stale", "protected_root_mutation", "work_lane_dirty"}, ("publish",): {"protected_root_mutation"}}
_EXTERNAL_STRICTER_ONLY_GAP_PREFIXES = {("quality", "command-surface"): ("retired_public_command_prefix_mention:", "retired_public_root_mention:"), ("playbooks", "route", "--changed"): ("playbook_changed_path_unmatched:.ethos/",)}
_PRODUCT_REPOSITORY_AUDIT_GAP_PREFIXES = ("docs/", "schemas/", "packages/", "distribution_adapter_missing:", "playbook_projection_missing:", "openspec_family_missing:", "claims_", "claim_", "schema_", "openspec_", "command_")
_CHANGED_ROUTE_NOOP_GAPS = {"skill_missing_id", "playbook_route_missing:changed-scope"}
_SEMANTIC_ARGS_ERROR = "semantic_diff expects external/embedded or command/external/embedded"


def semantic_diff(*args: Any) -> dict[str, Any]:
    command, external, embedded = _semantic_args(args)
    external_projection, embedded_projection, _accepted = _normalized_semantic_projections(command, external, embedded)
    return {key: {"external": external_projection.get(key), "embedded": embedded_projection.get(key)} for key in sorted(set(external_projection) | set(embedded_projection)) if external_projection.get(key) != embedded_projection.get(key)}


def false_negative_gaps(command: tuple[str, ...], external: dict[str, Any], embedded: dict[str, Any]) -> list[str]:
    external_projection, embedded_projection, _accepted = _normalized_semantic_projections(command, external, embedded)
    return sorted(set(string_list(embedded_projection.get("required_gaps"))) - set(string_list(external_projection.get("required_gaps"))))


def accepted_semantic_differences(*args: Any) -> list[dict[str, Any]]:
    command, external, embedded = _semantic_args(args)
    return _normalized_semantic_projections(command, external, embedded)[2]


def accepted_summary(differences: Iterable[object]) -> dict[str, Any]:
    items = differences if isinstance(differences, list) else list(differences)
    counts = Counter(str(item.get("kind") or "") for item in items if isinstance(item, dict) and item.get("kind"))
    return {"total_count": sum(counts.values()), "kind_counts": dict(sorted(counts.items()))}


def _semantic_args(args: tuple[Any, ...]) -> tuple[tuple[str, ...], dict[str, Any], dict[str, Any]]:
    if len(args) == 3:
        return tuple(str(item) for item in args[0]), args[1], args[2]
    if len(args) == 2:
        return tuple(str(args[0].get("command") or args[1].get("command") or "").split()), args[0], args[1]
    raise TypeError(_SEMANTIC_ARGS_ERROR)


def _record_accepted(accepted: list[dict[str, Any]], kind: str, projection: dict[str, Any], gaps: list[str]) -> None:
    if gaps:
        accepted.append(_accepted_difference(kind, command=projection.get("command"), gaps=gaps))


def _normalized_semantic_projections(command: tuple[str, ...], external: dict[str, Any], embedded: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    external_projection, embedded_projection = _semantic_projection(command, external), _semantic_projection(command, embedded)
    embedded_gaps, external_gaps, accepted = string_list(embedded_projection.get("required_gaps")), string_list(external_projection.get("required_gaps")), []
    if embedded_gaps:
        missing = sorted(set(embedded_gaps) - set(external_gaps))
        extra = sorted(set(external_gaps) - set(embedded_gaps))
        if extra and not missing:
            _record_accepted(accepted, "external_required_gap_superset", external_projection, extra)
            external_gaps = embedded_gaps
    else:
        external_gaps, removed = _without_product_repository_audit_gaps(external, external_gaps)
        _record_accepted(accepted, "external_product_repository_audit_gap", external_projection, removed)
        external_gaps, removed = _without_changed_route_noop_gaps(external, embedded, external_gaps)
        _record_accepted(accepted, "changed_route_noop", external_projection, removed)
        _record_accepted(accepted, "report_parity_evidence_refresh_bootstrap", external_projection, _report_parity_evidence_refresh_bootstrap_gaps(external, external_projection, embedded_projection))
        plan_gaps = shadow_planning.external_stricter_gaps(command, external_projection, embedded_projection)
        _record_accepted(accepted, "external_stricter_plan_scope", external_projection, plan_gaps)
        if plan_gaps:
            shadow_planning.normalize_external(external_projection, embedded_projection)
        external_gaps, removed = _without_external_stricter_only_gaps(command, external_gaps)
        _record_accepted(accepted, "external_stricter_required_gap", external_projection, removed)
    external_projection["required_gaps"] = sorted(external_gaps)
    if accepted and not external_gaps and not embedded_gaps:
        command_name = external_projection.get("command")
        external_projection.update(ok=True, state=_ready_state_for_command(command_name))
        _mark_projection_ready(external_projection)
    return external_projection, embedded_projection, accepted


def _accepted_difference(kind: str, *, command: object, gaps: list[str]) -> dict[str, Any]:
    scope, reason = _ACCEPTED_METADATA.get(kind, ("unknown", "unclassified accepted difference"))
    return {"kind": kind, "classification": "accepted", "scope": scope, "commands": [_command_label(command)], "gaps": sorted(set(gaps)), "reason": reason}


def _command_label(command: object) -> str:
    text = str(command or "").strip()
    return text if text.startswith("ethos ") else f"ethos {text}".strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _semantic_projection(command: tuple[str, ...], payload: dict[str, Any]) -> dict[str, Any]:
    summary, data = _dict(payload.get("summary")), _dict(payload.get("data"))
    name = _command_name(command, payload, summary)
    state = _semantic_state(payload, summary=summary, command=name)
    projection: dict[str, Any] = {"ok": payload.get("ok"), "command": name, "state": state, "required_gaps": sorted(string_list(payload.get("required_gaps")))}
    root = command[0] if command else name.split()[0] if name else ""
    if root == "status":
        changed = _first_list(data.get("changed_paths"), payload.get("changed_paths"))
        dirty = _first_present(data.get("dirty"), summary.get("dirty"), payload.get("dirty"))
        projection.update(role=_canonical_status_role(payload.get("role") or summary.get("role") or data.get("role")), dirty=False if dirty is None and state == "ready" else dirty, changed_path_count=len(changed))
    elif root == "plan":
        gates = _first_list(data.get("required_gates"), payload.get("required_gates"))
        projection.update(changed_path_count=len(_first_list(data.get("changed_paths"), payload.get("changed_paths"))), matched_rule_ids=sorted(str(rule.get("id")) for rule in _first_list(data.get("matched_rules"), payload.get("matched_rules")) if isinstance(rule, dict)), required_gate_ids=_gate_ids(gates))
    elif root == "prove":
        projection["proof_ready"] = bool(payload.get("ok")) and not payload.get("required_gaps")
    elif root == "report":
        projection["blocking_gap_count"] = summary.get("blocking_gap_count") if summary.get("blocking_gap_count") is not None else len(payload.get("required_gaps", []))
    elif root == "quality":
        projection["retired_violation_count"] = summary.get("retired_violation_count") or len(_list(data.get("retired_public_root_mentions")))
    elif root == "assistants":
        projection["assistant_ready"] = bool(payload.get("ok"))
    elif root == "playbooks":
        projection["route_ready"] = bool(payload.get("ok"))
    elif root in {"land", "publish"}:
        projection.update(readiness=bool(payload.get("ok")) and not payload.get("required_gaps"), remote_push=data.get("remote_push") or summary.get("remote_push"))
    return projection


def _mark_projection_ready(projection: dict[str, Any]) -> None:
    if mark := _READY_MARKS.get(projection.get("command")):
        projection[mark[0]] = mark[1]


def _command_name(command: tuple[str, ...], payload: dict[str, Any], summary: dict[str, Any]) -> str:
    explicit = payload.get("command") or summary.get("command")
    if explicit:
        return str(explicit)
    return next((name for prefix, name in _COMMAND_NAMES.items() if command[:2] == prefix), command[0] if command else "")


def _semantic_state(payload: dict[str, Any], *, summary: dict[str, Any], command: object) -> object:
    state = payload.get("state")
    if isinstance(state, str):
        return "proven" if payload.get("ok") is True and command == "prove" and state == "ready" and not string_list(payload.get("required_gaps")) else state
    if payload.get("ok") is not True:
        return state
    if command == "status":
        return "dirty" if payload.get("dirty", summary.get("dirty", False)) else "ready"
    return _ready_state_for_command(command) if _ready_state_for_command(command) is not None else state


def _ready_state_for_command(command: object) -> str | None:
    return _READY_STATES.get(command)


def _partition(gaps: list[str], predicate: Any) -> tuple[list[str], list[str]]:
    return [gap for gap in gaps if not predicate(gap)], [gap for gap in gaps if predicate(gap)]


def _without_product_repository_audit_gaps(payload: dict[str, Any], gaps: list[str]) -> tuple[list[str], list[str]]:
    audit_gaps = {gap for gap in string_list(_dict(_dict(payload.get("data")).get("repository_audit")).get("required_gaps")) if gap.startswith(_PRODUCT_REPOSITORY_AUDIT_GAP_PREFIXES)}
    return _partition(gaps, audit_gaps.__contains__) if audit_gaps else (gaps, [])


def _without_external_stricter_only_gaps(command: tuple[str, ...], gaps: list[str]) -> tuple[list[str], list[str]]:
    allowed, prefixes = _EXTERNAL_STRICTER_ONLY_GAPS.get(command, set()), _EXTERNAL_STRICTER_ONLY_GAP_PREFIXES.get(command, ())
    return _partition(gaps, lambda gap: gap in allowed or gap.startswith(prefixes)) if allowed or prefixes else (gaps, [])


def _without_changed_route_noop_gaps(external: dict[str, Any], embedded: dict[str, Any], gaps: list[str]) -> tuple[list[str], list[str]]:
    return _partition(gaps, _is_changed_route_noop_gap) if _is_changed_route_noop(external, embedded, gaps) else (gaps, [])


def _is_changed_route_noop_gap(gap: str) -> bool:
    return gap in _CHANGED_ROUTE_NOOP_GAPS or gap.startswith("playbook_activation_unsupported_version:")


def _is_changed_route_noop(external: dict[str, Any], embedded: dict[str, Any], gaps: list[str]) -> bool:
    external_data, embedded_summary = _dict(external.get("data")), _dict(embedded.get("summary"))
    return (external.get("command") or external_data.get("command")) == "playbooks route" and external_data.get("subject") == "changed-scope" and embedded_summary.get("changed_requested") is True and embedded_summary.get("changed_path_count") == 0 and bool(gaps) and all(map(_is_changed_route_noop_gap, gaps))


def _report_parity_evidence_refresh_bootstrap_gaps(external: dict[str, Any], external_projection: dict[str, Any], embedded_projection: dict[str, Any]) -> list[str]:
    summary = _dict(external.get("summary"))
    pending, governance = summary.get("parity_pending_count"), summary.get("governance_gap_count")
    matches = isinstance(pending, int) and pending > 0 and governance in (None, 0) and external_projection.get("command") == embedded_projection.get("command") == "report" and not external_projection.get("required_gaps") and not embedded_projection.get("required_gaps") and external_projection.get("ok") is False and embedded_projection.get("ok") is True and external_projection.get("state") == "gapped" and embedded_projection.get("state") == "ready"
    return [f"parity_pending_count:{pending}"] if matches else []


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _canonical_status_role(value: Any) -> Any:
    return STATUS_ROLE_ALIASES.get(value, value) if isinstance(value, str) else value


def _first_list(*values: Any) -> list[Any]:
    return next((value for value in values if isinstance(value, list)), [])


def _first_present(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _gate_ids(value: Any) -> list[str]:
    return sorted({str(gate.get("id")) for gate in _list(value) if isinstance(gate, dict)})
