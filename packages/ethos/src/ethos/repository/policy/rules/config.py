"""Rules configuration: rules.toml loading, profile resolution, raw-rule normalization."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path


def rules_path(root: Path) -> Path:
    """Return the tracked rules configuration path for a repository root."""
    return root / ".ethos" / "rules.toml"


def load_rules_config(root: Path) -> dict[str, Any]:
    """Parse rules configuration once, preserving a structured parse error."""
    path = rules_path(root)
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {"_parse_error": str(exc)}


def _normalize_profile(profile: str) -> str:
    if profile == "python-package":
        return "python"
    return profile


def resolve_profile_stack(config: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Resolve active profiles from one parsed config and report invalid shapes."""
    if "_parse_error" in config:
        return ["generic"], [f"rules_config_parse_error:{config['_parse_error']}"]
    profiles = config.get("profiles")
    if profiles is None:
        return ["generic"], []
    if not isinstance(profiles, dict):
        return ["generic"], ["rules_profile_invalid:must_be_table"]
    active = profiles.get("active")
    if active is None:
        return ["generic"], []
    if not isinstance(active, list) or any(not isinstance(item, str) for item in active):
        return ["generic"], ["rules_profile_invalid:active_must_be_string_array"]
    if not active:
        return ["generic"], ["rules_profile_invalid:active_must_not_be_empty"]
    if any(not item.strip() for item in active):
        return ["generic"], ["rules_profile_invalid:active_must_not_contain_empty_values"]
    normalized = [_normalize_profile(item) for item in active]
    if len(normalized) != len(set(normalized)):
        return ["generic"], ["rules_profile_ambiguous:active_contains_duplicates"]
    stack = list(normalized)
    if "generic" not in stack:
        stack.insert(0, "generic")
    return stack, []


def is_legacy_rule_item(item: dict[str, Any]) -> bool:
    """Return whether a parsed rule still contains legacy Rule V1 keys."""
    return bool({"risk", "paths", "requires", "evidence"}.intersection(item))


def configured_rules(
    root: Path,
    *,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return normalized rule dicts from .ethos/rules.toml, including legacy rule normalization."""
    parsed = config if config is not None else load_rules_config(root)
    rules = parsed.get("rule")
    if not isinstance(rules, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in rules:
        if not isinstance(item, dict):
            normalized.append({"id": "", "_invalid": "rule_not_table"})
            continue
        normalized.append(normalize_rule_item(item))
    return normalized


def normalize_rule_item(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize one parsed legacy or V2 rule into the canonical Rule V2 shape."""
    legacy_rule = is_legacy_rule_item(item)
    path_globs = item.get("path_globs", item.get("paths"))
    required_gates = item.get("required_gates", item.get("requires"))
    evidence_requirements = item.get("evidence_requirements", item.get("evidence", []))
    payload: dict[str, Any] = {}
    for key in (
        "id",
        "owner",
        "authority_ref",
        "contract_ref",
        "subject",
        "severity",
        "stop_condition",
    ):
        if key in item:
            payload[key] = item[key]
    if legacy_rule:
        _apply_legacy_rule_defaults(payload, item)
    raw_version = item.get("version", 1)
    payload["version"] = int(raw_version) if str(raw_version).isdigit() else raw_version
    payload["profile_layers"] = (
        [str(layer) for layer in item.get("profile_layers", [])]
        if isinstance(item.get("profile_layers"), list)
        else []
    )
    if isinstance(path_globs, list):
        payload["path_globs"] = [str(path) for path in path_globs]
    if isinstance(required_gates, list):
        payload["required_gates"] = [str(gate) for gate in required_gates]
    if isinstance(evidence_requirements, list) and evidence_requirements:
        payload["evidence_requirements"] = [str(req) for req in evidence_requirements]
    if "non_waivable" in item:
        payload["non_waivable"] = item["non_waivable"]
    return payload


def _apply_legacy_rule_defaults(payload: dict[str, Any], item: dict[str, Any]) -> None:
    rule_id = str(item.get("id") or "legacy-rule")
    risk = str(item.get("risk") or rule_id.replace(".", "_"))
    payload.setdefault("id", rule_id)
    payload.setdefault("owner", "repo-local")
    payload.setdefault("authority_ref", ".ethos/rules.toml")
    payload.setdefault("contract_ref", ".ethos/rules.toml")
    payload.setdefault("subject", risk)
    payload.setdefault("severity", "advisory")
    payload.setdefault("stop_condition", risk)


def legacy_state(
    root: Path,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Report whether parsed repository rules still carry legacy configuration."""
    parsed = config if config is not None else load_rules_config(root)
    if not parsed:
        return {"legacy_detected": False}
    legacy_keys = {"formats", "artifacts", "determinism", "standards", "gates"}
    rules = parsed.get("rule")
    legacy_rule_items = isinstance(rules, list) and any(
        isinstance(item, dict) and is_legacy_rule_item(item) for item in rules
    )
    has_v2_rules = isinstance(parsed.get("profiles"), dict) or (
        isinstance(rules, list) and not legacy_rule_items
    )
    return {
        "legacy_detected": (
            legacy_rule_items or (bool(legacy_keys.intersection(parsed)) and not has_v2_rules)
        ),
        "has_v2_rules": has_v2_rules,
        "legacy_rule_items": legacy_rule_items,
    }
