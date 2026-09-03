from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict

from ethos.contracts.plan import dependency_order
from ethos.contracts.value import FrozenTuple
from ethos.contracts.verdict import Verdict
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_list


class _ActivationModel(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class ActivatedSkill(_ActivationModel):
    id: str
    path: str
    operation: str


class SkillContext(_ActivationModel):
    pre_reads: FrozenTuple[str] = ()
    during_rules: FrozenTuple[str] = ()
    post_checks: FrozenTuple[str] = ()


class SkillActivation(_ActivationModel):
    verdict: Verdict
    skills: FrozenTuple[ActivatedSkill] = ()
    context: SkillContext = SkillContext()
    required_gaps: FrozenTuple[str] = ()


def normalize_skill_activation(
    payload: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    meta = dict(payload.get("meta") or {})
    records = [_normalize_record(entry) for entry in _list_of_dicts(payload.get("skill"))]
    return {
        "schema_version": 2,
        "source": source,
        "meta": meta,
        "coverage": dict(payload.get("coverage") or {}),
        "retired": dict(payload.get("retired") or {}),
        "records": records,
    }


def compile_skill_activation(
    registry: dict[str, Any],
    *,
    operation: str,
    subjects: tuple[str, ...] = (),
    changed_paths: tuple[str, ...] = (),
) -> SkillActivation:
    """Compile current operation and repository facts into one capability set."""
    records = {
        str(record["id"]): record
        for record in _list_of_dicts(registry.get("records"))
        if record.get("id") and record.get("lifecycle") == "active"
    }
    selected = {
        skill_id
        for skill_id, record in records.items()
        if _record_matches(
            record,
            operation=operation,
            subjects=subjects,
            changed_paths=changed_paths,
        )
    }
    gaps = _requirement_closure(selected, records)
    gaps.extend(_exclusion_gaps(selected, records))
    graph = {
        skill_id: tuple(
            sorted(
                required
                for required in records[skill_id]["relations"]["requires"]
                if required in selected
            )
        )
        for skill_id in sorted(selected)
    }
    ordered = _stable_skill_order(graph)
    if ordered is None:
        gaps.append("skill_activation_dependency_cycle")
        ordered = ()
    skills = [records[skill_id] for skill_id in ordered]
    return SkillActivation(
        verdict="pass" if not gaps else "block",
        skills=tuple(
            ActivatedSkill(
                id=str(record["id"]),
                path=str(record["path"]),
                operation=str(record["operation"]),
            )
            for record in skills
        ),
        context=SkillContext(
            **{
                key: tuple(_ordered_unique(record["obligations"][key] for record in skills))
                for key in ("pre_reads", "during_rules", "post_checks")
            }
        ),
        required_gaps=tuple(dict.fromkeys(gaps)),
    )


def _normalize_record(entry: dict[str, Any]) -> dict[str, Any]:
    skill_id = _string(entry.get("id"))
    primary_subject = _string(entry.get("subject") or entry.get("primary_subject"))
    path_globs = string_list(entry.get("path_globs"), drop_empty=True)
    subjects = _route_subjects(
        string_list(entry.get("subjects"), drop_empty=True),
        primary_subject=primary_subject,
        has_path_globs=bool(path_globs),
    )
    return {
        "id": skill_id,
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
            "requires": string_list(entry.get("requires"), drop_empty=True),
            "excludes": string_list(entry.get("excludes"), drop_empty=True),
        },
        "boundary": _string(entry.get("boundary")),
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


def _record_matches(
    record: dict[str, Any],
    *,
    operation: str,
    subjects: tuple[str, ...],
    changed_paths: tuple[str, ...],
) -> bool:
    subject_match = bool(set(subjects) & set(record["route_subjects"]))
    path_match = any(
        repository_path_matches(path, pattern)
        for path in changed_paths
        for pattern in record["activation"]["path_globs"]
    )
    return subject_match or path_match or record["operation"] == operation


def _requirement_closure(
    selected: set[str],
    records: dict[str, dict[str, Any]],
) -> list[str]:
    gaps: list[str] = []
    pending = list(selected)
    while pending:
        skill_id = pending.pop()
        for required in records[skill_id]["relations"]["requires"]:
            if required not in records:
                gaps.append(f"skill_activation_requirement_missing:{skill_id}:{required}")
            elif required not in selected:
                selected.add(required)
                pending.append(required)
    return gaps


def _exclusion_gaps(
    selected: set[str],
    records: dict[str, dict[str, Any]],
) -> list[str]:
    gaps: list[str] = []
    seen: set[frozenset[str]] = set()
    for skill_id in sorted(selected):
        for excluded in records[skill_id]["relations"]["excludes"]:
            pair = frozenset((skill_id, excluded))
            if excluded in selected and pair not in seen:
                gaps.append(f"skill_activation_exclusion_conflict:{skill_id}:{excluded}")
                seen.add(pair)
    return gaps


def _stable_skill_order(
    graph: dict[str, tuple[str, ...]],
) -> tuple[str, ...] | None:
    try:
        return dependency_order(graph)
    except ValueError:
        return None


def _ordered_unique(groups: Any) -> list[str]:
    return list(dict.fromkeys(item for group in groups for item in group))
