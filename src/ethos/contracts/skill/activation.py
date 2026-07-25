from __future__ import annotations

import hashlib
import json
from typing import Any

from ethos.normalization.core import string_list


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
    skill_id = declared_id
    identifier_source = "id" if declared_id else "missing"
    primary_subject = _string(entry.get("subject") or entry.get("primary_subject"))
    path_globs = string_list(entry.get("path_globs"), drop_empty=True)
    subjects = _route_subjects(
        string_list(entry.get("subjects"), drop_empty=True),
        primary_subject=primary_subject,
        has_path_globs=bool(path_globs),
    )
    return {
        "id": skill_id,
        "declared_id": declared_id,
        "declared_name": declared_name,
        "identifier_source": identifier_source,
        "priority": int(entry.get("priority") or 0),
        "path": _string(entry.get("path"))
        or (f".agents/skills/{skill_id}/SKILL.md" if skill_id else ""),
        "package_manifest": _string(entry.get("package_manifest")),
        "primary_subject": primary_subject,
        "operation": _string(entry.get("operation")),
        "authority": _string(entry.get("authority")),
        "lifecycle": _string(entry.get("lifecycle")) or "active",
        "route_subjects": subjects,
        "subjects": subjects,
        "activation": {"path_globs": path_globs},
        "routing": {"intent_tokens": string_list(entry.get("intent_tokens"), drop_empty=True)},
        "obligations": {
            "pre_reads": string_list(entry.get("pre_reads"), drop_empty=True),
            "during_rules": string_list(entry.get("during_rules"), drop_empty=True),
            "post_checks": string_list(entry.get("post_checks"), drop_empty=True),
        },
        "relations": {
            "may_coactivate": string_list(entry.get("may_coactivate"), drop_empty=True),
            "supports": string_list(entry.get("supports"), drop_empty=True),
            "excludes": string_list(entry.get("excludes"), drop_empty=True),
        },
        "commands": string_list(entry.get("commands"), drop_empty=True),
        "boundary": _string(entry.get("boundary")),
        "source_version": raw_version,
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
            if isinstance(key, str)
            and key not in {"digest", "computed_digest"}
            and not key.startswith("expected_")
        }
    if isinstance(value, list):
        return [_without_digest(item) for item in value]
    return value
