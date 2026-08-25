"""Compile transient intent facts from official OpenSpec projections."""

from __future__ import annotations

import re
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.attestation_set import read_attestation_set

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


def selected_input_gaps(
    root: Path,
    change: str,
    identities: tuple[str, ...],
    *,
    expected_root: str | None = None,
) -> tuple[str, list[str]]:
    """Validate selected-input dispositions bound to one successor Commitment."""
    if not identities:
        return "", []
    try:
        selected_root, selected = read_attestation_set(root)
    except (OSError, TypeError, ValueError) as error:
        return "", [str(error)]
    if expected_root is not None and selected_root != expected_root:
        return selected_root, ["selected_attestation_set_changed"]
    members = {item.id: item for item in selected}
    owner = f"change:{change}"
    now = datetime.now(UTC)
    gaps: list[str] = []
    for identity in identities:
        item = members.get(identity)
        if item is None:
            gaps.append(f"selected_attestation_missing:{identity}")
            continue
        relations = {(r.kind, r.target_kind, r.target_id) for r in item.relations}
        disposed = {
            target
            for kind, target_kind, target in relations
            if kind == "relation:disposes" and target_kind == "semantic:attestation"
        }
        valid = (
            item.verdict == "pass"
            and not item.payload.body.get("required_gaps")
            and (item.valid_from or item.issued_at) <= now
            and (item.valid_until is None or now <= item.valid_until)
            and item.predicate == "selection:input"
            and item.payload.kind == "selection:disposition"
            and item.payload.body.get("disposition") == "semantic-owner"
            and item.payload.body.get("owner") == owner
            and ("relation:selected-for", "semantic:commitment", owner) in relations
            and disposed == {item.subject}
            and disposed <= members.keys()
        )
        if not valid:
            gaps.append(f"selected_attestation_disposition_invalid:{identity}")
    return selected_root, gaps
