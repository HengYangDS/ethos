"""Legacy rules migration and TOML serialization."""

from __future__ import annotations

import fcntl
import hashlib
import re
import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.rules.config import _is_legacy_rule_item
from ethos.repository.policy.rules.config import _legacy_state
from ethos.repository.policy.rules.config import _normalize_rule_item
from ethos.repository.policy.rules.config import _profile_stack
from ethos.repository.policy.rules.config import _rules_path

if TYPE_CHECKING:
    from pathlib import Path


def migrate_legacy_rules(
    root: Path,
    *,
    apply: bool = False,
    expect_source_digest: str | None = None,
) -> dict[str, object]:
    """Report (and optionally apply) a lossless migration to the Rules V2 shape."""
    path = _rules_path(root)
    source_text = path.read_text(encoding="utf-8") if path.exists() else ""
    source_digest = _text_digest(source_text)
    try:
        source = tomllib.loads(source_text) if source_text else {}
    except tomllib.TOMLDecodeError as exc:
        return _migration_error(source_text, source_digest, f"rules_config_parse_error:{exc}")
    legacy = _legacy_state(root)
    legacy_detected = bool(legacy["legacy_detected"])
    target_text = (
        _migrated_rules_text(source_text, source, _profile_stack(root))
        if legacy_detected
        else source_text
    )
    target = tomllib.loads(target_text) if target_text else source
    required_gaps: list[str] = []
    if expect_source_digest is not None and expect_source_digest != source_digest:
        required_gaps.append("rules_migration_source_changed")
    if apply and legacy_detected and not required_gaps:
        expected_digest = expect_source_digest or source_digest
        if not _compare_and_swap_rules(path, expected_digest, target_text):
            required_gaps.append("rules_migration_source_changed")
    applied = bool(apply and legacy_detected and not required_gaps)
    return {
        "ok": not required_gaps,
        "legacy_detected": legacy_detected,
        "applied": applied,
        "source_digest": source_digest,
        "target": target,
        "target_text": target_text,
        "required_gaps": required_gaps,
        "next_actions": (
            ["ethos rules migrate --apply --authorize --expect-head <git-head>"]
            if legacy_detected and not apply
            else []
        ),
    }


_TABLE_HEADER = re.compile(r"^\s*\[{1,2}[^\]]+\]{1,2}\s*(?:#.*)?$")
_RULE_HEADER = re.compile(r"^\s*\[\[\s*rule\s*\]\]\s*(?:#.*)?$")
_PROFILES_HEADER = re.compile(r"^\s*\[\s*profiles\s*\]\s*(?:#.*)?$")
_ACTIVE_ASSIGNMENT = re.compile(r"^\s*active\s*=")


def _migration_error(source_text: str, source_digest: str, gap: str) -> dict[str, object]:
    return {
        "ok": False,
        "legacy_detected": False,
        "applied": False,
        "source_digest": source_digest,
        "target": {},
        "target_text": source_text,
        "required_gaps": [gap],
        "next_actions": ["repair .ethos/rules.toml before migration"],
    }


def _text_digest(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _compare_and_swap_rules(path: Path, expected_digest: str, target_text: str) -> bool:
    lock_path = path.parent / "state" / "rules-migration.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        current_text = path.read_text(encoding="utf-8") if path.exists() else ""
        if _text_digest(current_text) != expected_digest:
            return False
        _write_text_atomic(path, target_text)
    return True


def _write_text_atomic(path: Path, text: str) -> None:
    temporary = path.with_suffix(f"{path.suffix}.migration.tmp")
    try:
        temporary.write_text(text, encoding="utf-8")
        temporary.chmod(path.stat().st_mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _migrated_rules_text(
    source_text: str,
    source: dict[str, Any],
    active_profiles: list[str],
) -> str:
    lines = source_text.splitlines(keepends=True)
    raw_rules = source.get("rule") if isinstance(source.get("rule"), list) else []
    output: list[str] = []
    rule_index = 0
    profiles_found = False
    index = 0
    while index < len(lines):
        line = lines[index]
        if _PROFILES_HEADER.match(line):
            profiles_found = True
            end = _next_table_index(lines, index + 1)
            output.extend(_profiles_block(lines[index:end], active_profiles))
            index = end
            continue
        if _RULE_HEADER.match(line):
            end = _next_table_index(lines, index + 1)
            raw_rule = raw_rules[rule_index]
            rule_index += 1
            if isinstance(raw_rule, dict) and _is_legacy_rule_item(raw_rule):
                output.append("\n".join(_rule_toml_lines(_normalize_rule_item(raw_rule))) + "\n")
            else:
                output.extend(lines[index:end])
            index = end
            continue
        output.append(line)
        index += 1
    body = "".join(output)
    if profiles_found:
        return body
    return f"[profiles]\nactive = {toml_string_array(active_profiles)}\n\n{body}"


def _next_table_index(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        if _TABLE_HEADER.match(lines[index]):
            return index
    return len(lines)


def _profiles_block(lines: list[str], active_profiles: list[str]) -> list[str]:
    replacement = f"active = {toml_string_array(active_profiles)}\n"
    for index, line in enumerate(lines[1:], start=1):
        if _ACTIVE_ASSIGNMENT.match(line):
            return [*lines[:index], replacement, *lines[index + 1 :]]
    return [lines[0], replacement, *lines[1:]]


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
