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


def _validated_active_profiles(active: object) -> tuple[list[str], str]:
    if not isinstance(active, list) or any(not isinstance(item, str) for item in active):
        return [], "rules_profile_invalid:active_must_be_string_array"
    active_profiles = [item for item in active if isinstance(item, str)]
    if not active_profiles:
        return [], "rules_profile_invalid:active_must_not_be_empty"
    if any(not item.strip() for item in active_profiles):
        return [], "rules_profile_invalid:active_must_not_contain_empty_values"
    return active_profiles, ""


def resolve_profile_stack(config: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Resolve active profiles from one parsed config and report invalid shapes."""
    if "_parse_error" in config:
        return ["generic"], [f"rules_config_parse_error:{config['_parse_error']}"]
    profiles = config.get("profiles")
    if profiles is None:
        profiles = {}
    if not isinstance(profiles, dict):
        return ["generic"], ["rules_profile_invalid:must_be_table"]
    active = profiles.get("active")
    if active is None:
        active = ["generic"]
    active_profiles, active_gap = _validated_active_profiles(active)
    if active_gap:
        return ["generic"], [active_gap]
    normalized = [_normalize_profile(item) for item in active_profiles]
    if len(normalized) != len(set(normalized)):
        return ["generic"], ["rules_profile_ambiguous:active_contains_duplicates"]
    stack = list(normalized)
    if "generic" not in stack:
        stack.insert(0, "generic")
    return stack, []


def configured_rules(
    root: Path,
    *,
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return raw rule dicts from .ethos/rules.toml."""
    parsed = config if config is not None else load_rules_config(root)
    rules = parsed.get("rule")
    if not isinstance(rules, list):
        return []
    configured: list[dict[str, Any]] = []
    for item in rules:
        if not isinstance(item, dict):
            configured.append({"id": "", "_invalid": "rule_not_table"})
            continue
        configured.append(item)
    return configured
