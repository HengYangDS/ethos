"""Compile transient intent facts from official OpenSpec projections."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from ethos.contracts.semantic import Commitment

_REQUIREMENT = re.compile(r"^### Requirement: (.+)$", re.MULTILINE)
_SCENARIO = re.compile(r"^#### Scenario: (.+)$", re.MULTILINE)


def compile_intent_context(
    root: Path,
    *,
    commitment: Commitment,
    config: dict[str, Any],
    status: dict[str, Any],
    apply: dict[str, Any],
) -> tuple[dict[str, object], tuple[str, ...]]:
    """Project one selected Change's intent without persisting another owner."""
    context_files = apply.get("contextFiles")
    files = context_files if isinstance(context_files, dict) else {}
    values = [path for paths in files.values() if isinstance(paths, list) for path in paths]
    requirements = _requirements(root, values)
    edge_cases = _scenarios(root, values)
    artifacts = status.get("artifacts")
    artifact_rows = (
        [item for item in artifacts if isinstance(item, dict)]
        if isinstance(artifacts, list)
        else []
    )
    tasks = apply.get("tasks")
    task_rows = (
        [item for item in tasks if isinstance(item, dict)] if isinstance(tasks, list) else []
    )
    conflicts = sorted({item for item in requirements if requirements.count(item) > 1})
    return {
        "change": status.get("changeName", ""),
        "schema": status.get("schemaName", ""),
        "acceptance": list(commitment.acceptance),
        "negative_scope": _negative_scope(root, values),
        "ambiguities": _open_questions(root, values),
        "conflicts": conflicts,
        "project_context": apply.get("context", ""),
        "project_rules": config.get("rules", {}) if isinstance(config.get("rules"), dict) else {},
        "instruction": apply.get("instruction", ""),
        "artifact_dependencies": {
            str(item.get("id") or ""): list(item.get("requires") or ()) for item in artifact_rows
        },
        "completed_artifacts": [
            str(item.get("id") or "")
            for item in artifact_rows
            if item.get("status") in {"done", "skipped"}
        ],
        "affected_capabilities": sorted({item.split(":", 1)[0] for item in requirements}),
        "requirements": requirements,
        "edge_cases": edge_cases,
        "open_tasks": [item for item in task_rows if not item.get("done")],
    }, ()


def _paths(root: Path, values: object) -> tuple[Path, ...]:
    paths: list[Path] = []
    for value in values if isinstance(values, list) else ():
        path = Path(str(value)).resolve()
        if path.is_relative_to(root.resolve()) and path.is_file():
            paths.append(path)
    return tuple(paths)


def _requirements(root: Path, values: object) -> list[str]:
    requirements: list[str] = []
    for path in _paths(root, values):
        capability = path.parent.name
        requirements.extend(
            f"{capability}:{name.strip()}"
            for name in _REQUIREMENT.findall(path.read_text(encoding="utf-8"))
        )
    return requirements


def _scenarios(root: Path, values: object) -> list[str]:
    scenarios: list[str] = []
    for path in _paths(root, values):
        capability = path.parent.name
        text = path.read_text(encoding="utf-8")
        requirement = ""
        for line in text.splitlines():
            if match := _REQUIREMENT.fullmatch(line):
                requirement = match.group(1).strip()
            elif requirement and (match := _SCENARIO.fullmatch(line)):
                scenarios.append(f"{capability}:{requirement}:{match.group(1).strip()}")
    return scenarios


def _section_items(root: Path, values: object, heading: str) -> list[str]:
    items: list[str] = []
    for path in _paths(root, values):
        text = path.read_text(encoding="utf-8")
        marker = f"## {heading}"
        if marker not in text:
            continue
        section = text.split(marker, 1)[1].split("\n## ", 1)[0]
        items.extend(
            line.removeprefix("- ").strip()
            for line in section.splitlines()
            if line.startswith("- ")
        )
    return items


def _negative_scope(root: Path, values: object) -> list[str]:
    return _section_items(root, values, "Out of Scope")


def _open_questions(root: Path, values: object) -> list[str]:
    return _section_items(root, values, "Open Questions")
