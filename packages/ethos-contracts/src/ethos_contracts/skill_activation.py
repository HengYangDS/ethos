from __future__ import annotations

import hashlib
import json
from typing import Any


def normalize_skill_activation(
    payload: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    meta = dict(payload.get("meta") or {})
    raw_version = int(meta.get("version") or 1)
    records = [
        _normalize_record(entry, raw_version=raw_version)
        for entry in _list_of_dicts(payload.get("skill"))
    ]
    return {
        "schema_version": 2,
        "source": source,
        "meta": meta,
        "coverage": dict(payload.get("coverage") or {}),
        "retired": dict(payload.get("retired") or {}),
        "records": records,
    }


def skill_registry_digest(registry: dict[str, Any]) -> str:
    canonical = _without_digest(registry)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _normalize_record(entry: dict[str, Any], *, raw_version: int) -> dict[str, Any]:
    declared_id = _string(entry.get("id"))
    declared_name = _string(entry.get("name"))
    skill_id = declared_id or declared_name
    identifier_source = "id" if declared_id else "name" if declared_name else "missing"
    primary_subject = _string(entry.get("subject") or entry.get("primary_subject"))
    path_globs = _string_list(entry.get("path_globs"))
    subjects = _route_subjects(
        _string_list(entry.get("subjects")),
        primary_subject=primary_subject,
        has_path_globs=bool(path_globs),
    )
    return {
        "id": skill_id,
        "declared_id": declared_id,
        "declared_name": declared_name,
        "identifier_source": identifier_source,
        "priority": int(entry.get("priority") or 0),
        "path": _string(entry.get("path")) or f".agents/skills/{skill_id}/SKILL.md",
        "package_manifest": _string(entry.get("package_manifest")),
        "primary_subject": primary_subject,
        "operation": _string(entry.get("operation")),
        "authority": _string(entry.get("authority")) or ("legacy" if raw_version < 2 else ""),
        "lifecycle": _string(entry.get("lifecycle")) or "active",
        "route_subjects": subjects,
        "subjects": subjects,
        "activation": {"path_globs": path_globs},
        "routing": {"intent_tokens": _string_list(entry.get("intent_tokens"))},
        "obligations": {
            "pre_reads": _string_list(entry.get("pre_reads")),
            "during_rules": _string_list(entry.get("during_rules")),
            "post_checks": _string_list(entry.get("post_checks")),
        },
        "relations": {
            "may_coactivate": _string_list(entry.get("may_coactivate")),
            "supports": _string_list(entry.get("supports")),
            "excludes": _string_list(entry.get("excludes")),
        },
        "commands": _string_list(entry.get("commands")),
        "boundary": _string(entry.get("boundary")),
        "legacy": {
            "raw_version": raw_version,
            "identifier_source": identifier_source,
        },
        "extensions": _extensions(entry),
    }


def _route_subjects(
    subjects: list[str],
    *,
    primary_subject: str,
    has_path_globs: bool,
) -> list[str]:
    route_subjects: list[str] = []
    for subject in ([primary_subject] if primary_subject else []) + subjects:
        if subject and subject not in route_subjects:
            route_subjects.append(subject)
    if has_path_globs and "changed-scope" not in route_subjects:
        route_subjects.append("changed-scope")
    return route_subjects


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _extensions(entry: dict[str, Any]) -> dict[str, Any]:
    known = {
        "id",
        "name",
        "priority",
        "path",
        "package_manifest",
        "expected_digest",
        "subject",
        "primary_subject",
        "operation",
        "authority",
        "lifecycle",
        "subjects",
        "path_globs",
        "intent_tokens",
        "pre_reads",
        "during_rules",
        "post_checks",
        "may_coactivate",
        "supports",
        "excludes",
        "commands",
        "boundary",
    }
    return {key: value for key, value in entry.items() if key not in known}


def _without_digest(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_digest(item)
            for key, item in sorted(value.items())
            if key not in {"digest", "computed_digest"} and not key.startswith("expected_")
        }
    if isinstance(value, list):
        return [_without_digest(item) for item in value]
    return value
