"""Compile transient intent facts from official OpenSpec projections."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from markdown_it import MarkdownIt

if TYPE_CHECKING:
    from markdown_it.token import Token

    from ethos.contracts.semantic import Commitment

_REQUIREMENT = re.compile(r"^### Requirement: (.+)$", re.MULTILINE)
_SCENARIO = re.compile(r"^#### Scenario: (.+)$", re.MULTILINE)
_EDGE_SECTION = "## Requirement To Task To Proof"
_TASK = re.compile(r"^(F\.\d+|\d+\.\d+)\b")
_MARKDOWN = MarkdownIt("commonmark").enable("table")


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
    declared_edges = _edges(root, values)
    edges = _expand_edges(requirements, declared_edges)
    mapped = {str(edge["requirement"]) for edge in edges}
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
    task_ids = {task_id for item in task_rows for task_id in _task_ids(item)}
    edge_invalid = any(
        edge["requirement"] not in requirements or edge["task"] not in task_ids for edge in edges
    ) or any(
        str(edge["requirement"]).endswith(":*")
        and not any(
            _edge_matches(requirement, str(edge["requirement"])) for requirement in requirements
        )
        for edge in declared_edges
    )
    conflicts = sorted({item for item in requirements if requirements.count(item) > 1})
    gaps = ("model_gap",) if set(requirements) - mapped or edge_invalid or conflicts else ()
    return {
        "change": status.get("changeName", ""),
        "schema": status.get("schemaName", ""),
        "intent": commitment.intent,
        "invariants": list(commitment.invariants),
        "acceptance": list(commitment.acceptance),
        "risks": list(commitment.risks),
        "assumptions": [value.model_dump(mode="json") for value in commitment.hypotheses],
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
        "requirement_edges": edges,
        "open_tasks": [item for item in task_rows if not item.get("done")],
    }, gaps


def _paths(root: Path, values: object) -> tuple[Path, ...]:
    paths: list[Path] = []
    for value in values if isinstance(values, list) else ():
        path = Path(str(value)).resolve()
        if path.is_relative_to(root.resolve()) and path.is_file():
            paths.append(path)
    return tuple(paths)


def _task_ids(item: dict[str, Any]) -> tuple[str, ...]:
    identifiers = [str(item.get("id") or "").strip()]
    if match := _TASK.search(str(item.get("description") or "")):
        identifiers.append(match.group(1))
    return tuple(identifier for identifier in identifiers if identifier)


def _edge_matches(requirement: str, declaration: str) -> bool:
    return (
        requirement.startswith(declaration.removesuffix("*"))
        if declaration.endswith(":*")
        else requirement == declaration
    )


def _expand_edges(requirements: list[str], edges: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {**edge, "requirement": requirement}
        for edge in edges
        for requirement in requirements
        if _edge_matches(requirement, str(edge["requirement"]))
    ]


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


def _edges(root: Path, values: object) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in _paths(root, values):
        tokens = _MARKDOWN.parse(path.read_text(encoding="utf-8"))
        rows.extend(_edge_rows(tokens))
    return rows


def _edge_rows(tokens: list[Token]) -> list[dict[str, str]]:
    section = False
    table = False
    row: list[str] = []
    rows: list[dict[str, str]] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            title = tokens[index + 1].content if index + 1 < len(tokens) else ""
            if section and title != _EDGE_SECTION.removeprefix("## "):
                break
            section = title == _EDGE_SECTION.removeprefix("## ")
        elif section and token.type == "table_open":
            table = True
        elif table and token.type == "table_close":
            break
        elif table and token.type == "tr_open":
            row = []
        elif table and token.type == "inline" and token.level >= 4:
            row.append(_inline_text(token))
        elif table and token.type == "tr_close" and len(row) == 3 and row[0] != "Requirement":
            rows.append(dict(zip(("requirement", "task", "proof"), row, strict=True)))
    return rows


def _inline_text(token: Token) -> str:
    return "".join(child.content for child in token.children or ()).strip()


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
