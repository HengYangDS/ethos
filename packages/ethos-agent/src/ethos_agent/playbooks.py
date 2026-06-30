from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def _skills_root(root: Path) -> Path:
    return root / ".agents" / "skills"


def _activation_path(root: Path) -> Path:
    return _skills_root(root) / "activation.toml"


def _load_activation(root: Path) -> tuple[dict[str, Any], list[str]]:
    path = _activation_path(root)
    if not path.exists():
        return {}, [".agents/skills/activation.toml"]
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}, [".agents/skills/activation.toml:invalid_toml"]
    return payload, []


def playbooks_report(root: Path) -> dict[str, object]:
    skills_root = _skills_root(root)
    payload, missing = _load_activation(root)
    skill_entries = payload.get("skill", []) if isinstance(payload, dict) else []
    if not isinstance(skill_entries, list):
        skill_entries = []
    skills = []
    gaps = list(missing)
    for entry in skill_entries:
        if not isinstance(entry, dict):
            continue
        skill_id = str(entry.get("id") or "")
        relative_path = str(entry.get("path") or "")
        if not skill_id:
            gaps.append("skill_missing_id")
            continue
        if not relative_path or not (root / relative_path).exists():
            gaps.append(f"skill_missing_file:{skill_id}")
        skills.append(
            {
                "id": skill_id,
                "path": relative_path,
                "subjects": list(entry.get("subjects") or []),
                "commands": list(entry.get("commands") or []),
                "boundary": str(entry.get("boundary") or ""),
            }
        )
    if skills_root.exists() and not (skills_root / "README.md").exists():
        gaps.append(".agents/skills/README.md")
    if not skills_root.exists():
        gaps.append(".agents/skills")
    return {
        "ok": not gaps,
        "skills_root": ".agents/skills",
        "skills": [skill["id"] for skill in skills],
        "records": skills,
        "required_gaps": gaps,
    }


def route_playbook(
    root: Path,
    subject: str,
    *,
    require_explicit_subject: bool = False,
) -> dict[str, object]:
    report = playbooks_report(root)
    normalized = subject.strip().lower()
    selected = [
        record
        for record in report["records"]
        if _matches_route_subject(
            record,
            normalized,
            require_explicit_subject=require_explicit_subject,
        )
    ]
    gaps = list(report["required_gaps"])
    if not selected:
        gaps.append(f"playbook_route_missing:{subject}")
    return {
        "ok": not gaps,
        "subject": subject,
        "selected": selected,
        "required_gaps": gaps,
        "skills_root": report["skills_root"],
    }


def _matches_route_subject(
    record: dict[str, object],
    normalized: str,
    *,
    require_explicit_subject: bool,
) -> bool:
    subjects = [str(item).strip().lower() for item in record["subjects"]]
    if require_explicit_subject:
        return normalized in subjects
    return normalized in str(record["id"]).lower() or any(normalized in item for item in subjects)
