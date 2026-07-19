"""Legacy rules migration and TOML serialization."""

from __future__ import annotations

import fcntl
import hashlib
import os
import re
import tempfile
import tomllib
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

from ethos.repository.policy.rules.config import is_legacy_rule_item
from ethos.repository.policy.rules.config import normalize_rule_item
from ethos.repository.policy.rules.config import resolve_profile_stack
from ethos.repository.policy.rules.config import rules_path
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def migrate_legacy_rules(
    root: Path,
    *,
    apply: bool = False,
    expect_source_digest: str | None = None,
    expect_head: str | None = None,
    read_head: Callable[[], str] | None = None,
) -> dict[str, object]:
    """Report (and optionally apply) a lossless migration to the Rules V2 shape."""
    path = rules_path(root)
    source_text = path.read_text(encoding="utf-8") if path.exists() else ""
    source_digest = _text_digest(source_text)
    try:
        source = tomllib.loads(source_text) if source_text else {}
    except tomllib.TOMLDecodeError as exc:
        return _migration_error(source_text, source_digest, f"rules_config_parse_error:{exc}")
    legacy = _legacy_state_from_source(source)
    legacy_detected = bool(legacy["legacy_detected"])
    profile_stack, profile_gaps = resolve_profile_stack(source)
    migration_gaps = [*profile_gaps, *_legacy_rule_migration_gaps(root, source)]
    if migration_gaps:
        return _migration_error(
            source_text,
            source_digest,
            migration_gaps,
            source=source,
            legacy_detected=legacy_detected,
        )
    try:
        target_text = (
            _migrated_rules_text(source_text, source, profile_stack)
            if legacy_detected
            else source_text
        )
        target = tomllib.loads(target_text) if target_text else source
    except (IndexError, KeyError, ValueError, tomllib.TOMLDecodeError) as exc:
        return _migration_error(
            source_text,
            source_digest,
            f"rules_migration_target_parse_error:{exc}",
            source=source,
            legacy_detected=legacy_detected,
        )
    target_gaps = _target_rule_migration_gaps(target)
    if target_gaps:
        return _migration_error(
            source_text,
            source_digest,
            target_gaps,
            source=source,
            legacy_detected=legacy_detected,
        )
    required_gaps: list[str] = []
    if expect_source_digest is not None and expect_source_digest != source_digest:
        required_gaps.append("rules_migration_source_changed")
    if apply and legacy_detected and not required_gaps:
        expected_digest = expect_source_digest or source_digest
        write_gap = _compare_and_swap_rules(
            path,
            expected_digest,
            target_text,
            expect_head=expect_head,
            read_head=read_head,
        )
        if write_gap is not None:
            required_gaps.append(write_gap)
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


def _migration_error(
    source_text: str,
    source_digest: str,
    gaps: str | list[str],
    *,
    source: dict[str, Any] | None = None,
    legacy_detected: bool = False,
) -> dict[str, object]:
    return {
        "ok": False,
        "legacy_detected": legacy_detected,
        "applied": False,
        "source_digest": source_digest,
        "target": source or {},
        "target_text": source_text,
        "required_gaps": [gaps] if isinstance(gaps, str) else gaps,
        "next_actions": ["repair .ethos/rules.toml before migration"],
    }


def _text_digest(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _compare_and_swap_rules(
    path: Path,
    expected_digest: str,
    target_text: str,
    *,
    expect_head: str | None,
    read_head: Callable[[], str] | None,
) -> str | None:
    """Serialize cooperating writers, then commit one atomic replacement."""
    lock_path = path.parent / "state" / "rules-migration.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return _write_text_atomic(
            path,
            expected_digest,
            target_text,
            expect_head=expect_head,
            read_head=read_head,
        )


def _write_text_atomic(
    path: Path,
    expected_digest: str,
    text: str,
    *,
    expect_head: str | None,
    read_head: Callable[[], str] | None,
) -> str | None:
    temporary = _prepared_temporary(path, text)
    try:
        try:
            current = path.open("r+", encoding="utf-8")
        except FileNotFoundError:
            return "rules_migration_source_changed"
        with current:
            fcntl.flock(current.fileno(), fcntl.LOCK_EX)
            current.seek(0)
            if _text_digest(current.read()) != expected_digest:
                return "rules_migration_source_changed"
            temporary.chmod(os.fstat(current.fileno()).st_mode)
            head_gap = _head_guard_gap(expect_head, read_head)
            if head_gap is not None:
                return head_gap
            current.seek(0)
            if _text_digest(current.read()) != expected_digest:
                return "rules_migration_source_changed"
            try:
                temporary.replace(path)
            except OSError as exc:
                return f"rules_migration_write_failed:{exc.errno or 'unknown'}"
            return None
    finally:
        temporary.unlink(missing_ok=True)


def _head_guard_gap(
    expect_head: str | None,
    read_head: Callable[[], str] | None,
) -> str | None:
    if expect_head is None:
        return None
    if read_head is None or read_head() != expect_head:
        return "expect_head_mismatch"
    return None


def _prepared_temporary(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.migration.",
    )
    temporary = type(path)(raw_path)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    return temporary


_LEGACY_TOP_LEVEL_KEYS = {"formats", "artifacts", "determinism", "standards", "gates"}
_SUPPORTED_RULE_KEYS = {
    "id",
    "version",
    "owner",
    "profile_layers",
    "authority_ref",
    "contract_ref",
    "subject",
    "path_globs",
    "severity",
    "required_gates",
    "evidence_requirements",
    "stop_condition",
    "non_waivable",
    "risk",
    "paths",
    "requires",
    "evidence",
}
_RULE_KEY_PAIRS = (
    ("paths", "path_globs"),
    ("requires", "required_gates"),
    ("evidence", "evidence_requirements"),
)
_STRING_RULE_KEYS = {
    "id",
    "owner",
    "authority_ref",
    "contract_ref",
    "subject",
    "severity",
    "stop_condition",
    "risk",
}
_STRING_ARRAY_RULE_KEYS = {
    "profile_layers",
    "path_globs",
    "required_gates",
    "evidence_requirements",
    "paths",
    "requires",
    "evidence",
}


def _legacy_state_from_source(source: dict[str, Any]) -> dict[str, object]:
    rules = source.get("rule")
    legacy_rule_items = isinstance(rules, list) and any(
        isinstance(item, dict) and is_legacy_rule_item(item) for item in rules
    )
    has_v2_rules = isinstance(source.get("profiles"), dict) or (
        isinstance(rules, list) and not legacy_rule_items
    )
    return {
        "legacy_detected": legacy_rule_items
        or (bool(_LEGACY_TOP_LEVEL_KEYS.intersection(source)) and not has_v2_rules),
        "has_v2_rules": has_v2_rules,
        "legacy_rule_items": legacy_rule_items,
    }


def _legacy_rule_migration_gaps(
    root: Path,
    source: dict[str, Any],
) -> list[str]:
    raw_rules = source.get("rule")
    if not isinstance(raw_rules, list):
        return []
    gaps: list[str] = []
    for index, item in enumerate(raw_rules):
        if not isinstance(item, dict) or not is_legacy_rule_item(cast("dict[str, Any]", item)):
            continue
        rule = cast("dict[str, Any]", item)
        rule_id = str(rule.get("id") or f"<index:{index}>")
        unsupported = sorted(set(rule).difference(_SUPPORTED_RULE_KEYS))
        if unsupported:
            gaps.append(f"rules_migration_lossy:{rule_id}:unsupported_keys:{','.join(unsupported)}")
        gaps.extend(_legacy_rule_type_gaps(rule_id, rule))
        for legacy_key, v2_key in _RULE_KEY_PAIRS:
            if legacy_key in rule and v2_key in rule and rule[legacy_key] != rule[v2_key]:
                gaps.append(f"rules_migration_ambiguous:{rule_id}:{legacy_key}:{v2_key}")
        risk_present = "risk" in rule
        for v2_key in ("subject", "stop_condition"):
            if risk_present and v2_key in rule and rule["risk"] != rule[v2_key]:
                gaps.append(f"rules_migration_ambiguous:{rule_id}:risk:{v2_key}")
        normalized = normalize_rule_item(rule)
        validation = validate_schema_instance("rule.schema.json", normalized, root=root)
        gaps.extend(
            f"rules_migration_invalid:{rule_id}:{gap}"
            for gap in cast("list[str]", validation["required_gaps"])
        )
    return list(dict.fromkeys(gaps))


def _target_rule_migration_gaps(target: dict[str, Any]) -> list[str]:
    raw_rules = target.get("rule")
    if not isinstance(raw_rules, list):
        return []
    return [
        f"rules_migration_target_legacy_keys:{item.get('id') or f'<index:{index}>'}"
        for index, item in enumerate(raw_rules)
        if isinstance(item, dict) and is_legacy_rule_item(cast("dict[str, Any]", item))
    ]


def _legacy_rule_type_gaps(rule_id: str, item: dict[str, Any]) -> list[str]:
    gaps = [
        f"rules_migration_invalid:{rule_id}:{key}_must_be_string"
        for key in sorted(_STRING_RULE_KEYS.intersection(item))
        if not isinstance(item[key], str)
    ]
    gaps.extend(
        f"rules_migration_invalid:{rule_id}:{key}_must_be_string_array"
        for key in sorted(_STRING_ARRAY_RULE_KEYS.intersection(item))
        if not isinstance(item[key], list) or any(not isinstance(value, str) for value in item[key])
    )
    if "version" in item and (
        not isinstance(item["version"], int) or isinstance(item["version"], bool)
    ):
        gaps.append(f"rules_migration_invalid:{rule_id}:version_must_be_integer")
    if "non_waivable" in item and not isinstance(item["non_waivable"], bool):
        gaps.append(f"rules_migration_invalid:{rule_id}:non_waivable_must_be_boolean")
    return gaps


def _migrated_rules_text(
    source_text: str,
    source: dict[str, Any],
    active_profiles: list[str],
) -> str:
    lines = source_text.splitlines(keepends=True)
    configured_rules = source.get("rule")
    raw_rules = cast("list[object]", configured_rules) if isinstance(configured_rules, list) else []
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
            if isinstance(raw_rule, dict) and is_legacy_rule_item(cast("dict[str, Any]", raw_rule)):
                rule = cast("dict[str, Any]", raw_rule)
                output.append("\n".join(_rule_toml_lines(normalize_rule_item(rule))) + "\n")
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
            end = _profiles_active_assignment_end(lines, index)
            return [*lines[:index], replacement, *lines[end:]]
    return [lines[0], replacement, *lines[1:]]


def _profiles_active_assignment_end(lines: list[str], start: int) -> int:
    return next(
        end
        for end in range(start + 1, len(lines) + 1)
        if _profiles_active_assignment_is_complete(lines, start, end)
    )


def _profiles_active_assignment_is_complete(lines: list[str], start: int, end: int) -> bool:
    candidate = "[profiles]\n" + "".join(lines[start:end])
    try:
        tomllib.loads(candidate)
    except tomllib.TOMLDecodeError:
        return False
    return True


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
        value = cast("str", rule[key])
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


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
