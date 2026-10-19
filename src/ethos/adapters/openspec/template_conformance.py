"""Bind active Change artifacts to the templates the official OpenSpec CLI resolves."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ethos.repository.openspec.identifiers import LOGICAL_CHANGE_ID_PATTERN
from ethos.repository.openspec.template_outline import OutlineHeading
from ethos.repository.openspec.template_outline import markdown_outline
from ethos.repository.openspec.template_outline import outline_gaps
from ethos.repository.openspec.template_outline import template_outline

STATUS_ALL = ("status", "--all", "--json")
# Every template-heading gap begins with this prefix; repair admission reads it.
TEMPLATE_HEADING_GAP = "openspec_template_heading_"
_TEMPLATE_ARTIFACTS = ("proposal", "design")
_MAX_MARKDOWN_BYTES = 1 << 20


def active_change_graphs(status_all: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Return the official artifact graph of every active Change, or None when unreadable."""
    changes = status_all["json"].get("changes")
    readable = (
        not status_all["exit_code"]
        and not status_all["parse_error"]
        and isinstance(changes, list)
        and all(
            isinstance(change, dict)
            and isinstance(change.get("changeName"), str)
            and isinstance(change.get("schemaName"), str)
            and isinstance(change.get("artifactPaths"), dict)
            for change in changes
        )
    )
    return changes if readable else None


def template_reads(changes: list[dict[str, Any]]) -> tuple[tuple[str, ...], ...]:
    """Read the templates of each distinct schema in use once."""
    schemas = sorted(
        {
            str(change["schemaName"])
            for change in changes
            if LOGICAL_CHANGE_ID_PATTERN.fullmatch(str(change["schemaName"]))
        }
    )
    return tuple(("templates", "--schema", schema, "--json") for schema in schemas)


def template_conformance_gaps(
    root: Path, changes: list[dict[str, Any]], templates: dict[str, dict[str, Any]]
) -> list[str]:
    """Report each literal template heading that an active proposal or design lacks in place."""
    gaps: list[str] = []
    outlines: dict[str, dict[str, tuple[OutlineHeading, ...] | None] | None] = {}
    for change in changes:
        name, schema = str(change["changeName"]), str(change["schemaName"])
        if schema not in outlines:
            outlines[schema] = _template_outlines(templates.get(schema))
        schema_outlines = outlines[schema]
        if schema_outlines is None:
            gaps.append(f"openspec_templates_unavailable:{name}:{schema}")
            continue
        for artifact, outline in schema_outlines.items():
            if outline is None:
                gaps.append(f"openspec_template_unreadable:{schema}:{artifact}")
                continue
            graph = change["artifactPaths"].get(artifact)
            outputs = graph.get("existingOutputPaths") if isinstance(graph, dict) else None
            for output in outputs if isinstance(outputs, list) else ():
                text = _markdown(Path(str(output)), root=root)
                if text is None:
                    gaps.append(f"openspec_artifact_unreadable:{name}:{artifact}")
                    continue
                gaps.extend(
                    f"{TEMPLATE_HEADING_GAP}{kind}:{name}:{artifact}:{path}"
                    for kind, path in outline_gaps(outline, markdown_outline(text))
                )
    return list(dict.fromkeys(gaps))


def _template_outlines(
    result: dict[str, Any] | None,
) -> dict[str, tuple[OutlineHeading, ...] | None] | None:
    """Outline each checked artifact template of one schema; None when the read failed."""
    if result is None or result["exit_code"] or result["parse_error"]:
        return None
    outlines: dict[str, tuple[OutlineHeading, ...] | None] = {}
    for artifact in _TEMPLATE_ARTIFACTS:
        template = result["json"].get(artifact)
        if template is None:
            continue
        path = template.get("path") if isinstance(template, dict) else None
        text = _markdown(Path(path), root=None) if isinstance(path, str) else None
        outlines[artifact] = template_outline(text) if text is not None else None
    return outlines


def _markdown(path: Path, *, root: Path | None) -> str | None:
    """Read one bounded official file; artifacts must stay inside the repository."""
    if not path.is_absolute():
        return None
    try:
        resolved = path.resolve(strict=True)
        if root is not None and not resolved.is_relative_to(root.resolve()):
            return None
        if not resolved.is_file() or resolved.stat().st_size > _MAX_MARKDOWN_BYTES:
            return None
        return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
