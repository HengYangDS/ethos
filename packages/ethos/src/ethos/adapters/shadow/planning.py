from __future__ import annotations

from typing import Any


def external_stricter_gaps(
    command: tuple[str, ...],
    external_projection: dict[str, Any],
    embedded_projection: dict[str, Any],
) -> list[str]:
    if not _accepts_stricter_plan_scope(command, external_projection, embedded_projection):
        return []
    external_rules = _string_list(external_projection.get("matched_rule_ids"))
    external_gates = _string_list(external_projection.get("required_gate_ids"))
    gaps = [f"changed_paths:{_int(external_projection.get('changed_path_count'))}"]
    if external_rules:
        gaps.append(f"matched_rules:{','.join(external_rules)}")
    if external_gates:
        gaps.append(f"required_gates:{','.join(external_gates)}")
    return gaps


def normalize_external(
    external_projection: dict[str, Any],
    embedded_projection: dict[str, Any],
) -> None:
    for key in ("changed_path_count", "matched_rule_ids", "required_gate_ids"):
        external_projection[key] = embedded_projection.get(key)


def _accepts_stricter_plan_scope(
    command: tuple[str, ...],
    external_projection: dict[str, Any],
    embedded_projection: dict[str, Any],
) -> bool:
    checks = (
        command == ("plan", "--changed"),
        external_projection.get("command") == "plan",
        embedded_projection.get("command") == "plan",
        not external_projection.get("required_gaps"),
        not embedded_projection.get("required_gaps"),
        _int(external_projection.get("changed_path_count"))
        > _int(embedded_projection.get("changed_path_count")),
        _int(embedded_projection.get("changed_path_count")) == 0,
        not _string_list(embedded_projection.get("matched_rule_ids")),
        not _string_list(embedded_projection.get("required_gate_ids")),
    )
    return all(checks)


def _string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0
