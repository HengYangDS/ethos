"""Legacy rules migration and TOML serialization."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.rules.config import _legacy_state
from ethos.repository.policy.rules.config import _profile_stack
from ethos.repository.policy.rules.config import _rules_path
from ethos.repository.policy.rules.config import configured_gate_tables
from ethos.repository.policy.rules.config import configured_rules

if TYPE_CHECKING:
    from pathlib import Path


def migrate_legacy_rules(root: Path, *, apply: bool = False) -> dict[str, object]:
    """Report (and optionally apply) migration of legacy rules.toml to the v2 shape."""
    legacy = _legacy_state(root)
    target_profiles: dict[str, object] = {"active": _profile_stack(root)}
    target_gates = configured_gate_tables(root)
    target_rules = configured_rules(root)
    target_text = rules_toml_text(
        target_rules,
        profiles=target_profiles,
        gates=target_gates,
    )
    target: dict[str, object] = {"profiles": target_profiles, "rule": target_rules}
    if target_gates:
        target["gates"] = target_gates
    if apply and legacy["legacy_detected"]:
        path = _rules_path(root)
        path.write_text(target_text, encoding="utf-8")
    return {
        "ok": True,
        "legacy_detected": bool(legacy["legacy_detected"]),
        "applied": bool(apply and legacy["legacy_detected"]),
        "target": target,
        "target_text": target_text,
        "required_gaps": [],
        "next_actions": (
            ["ethos rules migrate --apply --authorize --expect-head <git-head>"]
            if legacy["legacy_detected"] and not apply
            else []
        ),
    }


def rules_toml_text(
    rules: list[dict[str, Any]],
    *,
    profiles: dict[str, object] | None = None,
    gates: dict[str, dict[str, object]] | None = None,
) -> str:
    """Serialize compiled rules, profiles, and gate tables back to rules.toml text."""
    profiles_active = profiles.get("active") if isinstance(profiles, dict) else None
    active_profiles = profiles_active if isinstance(profiles_active, list) else ["generic"]
    lines = ["[profiles]", f"active = {toml_string_array(active_profiles)}", ""]
    for gate_id, gate in sorted((gates or {}).items()):
        lines.append(f"[gates.{toml_table_key(gate_id)}]")
        for key in ("command", "blocking"):
            if key in gate:
                lines.append(f"{key} = {toml_value(gate[key])}")
        lines.append("")
    for rule in rules:
        if not rule.get("id"):
            continue
        lines.extend(_rule_toml_lines(rule))
    return "\n".join(lines).rstrip() + "\n"


def _rule_toml_lines(rule: dict[str, Any]) -> list[str]:
    lines = ["[[rule]]"]
    for key in (
        "id",
        "owner",
        "authority_ref",
        "contract_ref",
        "subject",
        "severity",
        "stop_condition",
    ):
        value = rule.get(key)
        if isinstance(value, str) and value:
            lines.append(f'{key} = "{_toml_escape(value)}"')
    version = rule.get("version")
    if isinstance(version, int) and version != 1:
        lines.append(f"version = {version}")
    for key in (
        "profile_layers",
        "path_globs",
        "required_gates",
        "evidence_requirements",
    ):
        value = rule.get(key)
        if isinstance(value, list):
            lines.append(f"{key} = {toml_string_array(value)}")
    if "non_waivable" in rule:
        lines.append(f"non_waivable = {str(bool(rule['non_waivable'])).lower()}")
    lines.append("")
    return lines


def toml_string_array(values: list[Any]) -> str:
    """Render a list as a TOML string array."""
    return "[" + ", ".join(f'"{_toml_escape(str(value))}"' for value in values) + "]"


def toml_value(value: object) -> str:
    """Render a scalar or list as its TOML literal form."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return toml_string_array(value)
    return f'"{_toml_escape(str(value))}"'


def toml_table_key(value: str) -> str:
    """Render a TOML table key, quoting it when it is not a bare key."""
    if value.replace("_", "-").replace("-", "").isalnum():
        return value
    return f'"{_toml_escape(value)}"'


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
