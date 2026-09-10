"""Preserve official intent sources and project syntax without certifying understanding."""

from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from markdown_it import MarkdownIt

from ethos.normalization.coercion import object_sequence
from ethos.normalization.coercion import string_mapping

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ethos.contracts.semantic import Commitment


def compile_intent_context(
    root: Path,
    *,
    commitment: Commitment,
    config: dict[str, Any],
    status: dict[str, Any],
    apply: dict[str, Any],
) -> tuple[dict[str, object], tuple[str, ...]]:
    """Read selected sources once and return non-authorizing context plus exact gaps."""
    sources, gaps = _sources(root, apply.get("contextFiles"))
    view: dict[str, list[str]] = {
        key: [] for key in ("requirements", "edge_cases", "negative_scope", "ambiguities")
    }
    for path, source in sources.items():
        for key, value in _document_context(Path(path).parent.name, source["content"]):
            view[key].append(value)
    artifacts = [
        item for item in object_sequence(status.get("artifacts")) if isinstance(item, dict)
    ]
    return {
        "change": status.get("changeName", ""),
        "schema": status.get("schemaName", ""),
        "acceptance": list(commitment.acceptance),
        **view,
        "sources": sources,
        "source_state": "incomplete" if gaps else "complete",
        "interpretation_state": "not_assessed",
        "duplicate_requirements": sorted(
            name for name, count in Counter(view["requirements"]).items() if count > 1
        ),
        "project_context": apply.get("context", ""),
        "project_rules": string_mapping(config.get("rules")),
        "instruction": apply.get("instruction", ""),
        "artifacts": artifacts,
        "affected_capabilities": sorted({item.split(":", 1)[0] for item in view["requirements"]}),
        "open_tasks": [
            item
            for item in object_sequence(apply.get("tasks"))
            if isinstance(item, dict) and not item.get("done")
        ],
    }, tuple(gaps)


def _sources(root: Path, declared: object) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Retain exact selected UTF-8 sources; unavailable declarations remain explicit."""
    if not isinstance(declared, dict) or not declared:
        return {}, ["openspec_context_sources_missing"]
    sources: dict[str, dict[str, str]] = {}
    gaps: list[str] = []
    root = root.resolve()
    for role, paths in sorted(declared.items()):
        if (
            not isinstance(paths, list)
            or not paths
            or any(not isinstance(p, str) or not p for p in paths)
        ):
            gaps.append(f"openspec_context_paths_invalid:{role}")
            continue
        for value in paths:
            try:
                path = (root / value).resolve()
                if not path.is_relative_to(root):
                    gaps.append(f"openspec_context_path_escape:{value}")
                    continue
                relative = path.relative_to(root).as_posix()
                if relative in sources:
                    continue
                content = path.read_bytes()
                sources[relative] = {
                    "content": content.decode("utf-8"),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            except (OSError, RuntimeError, UnicodeError, ValueError) as error:
                gaps.append(f"openspec_context_source_unavailable:{value}:{type(error).__name__}")
    return dict(sorted(sources.items())), sorted(set(gaps))


def _document_context(capability: str, content: str) -> Iterator[tuple[str, str]]:
    """Project actual CommonMark headings and paragraphs, never fenced pseudo-structure."""
    section, requirement, heading = "", "", ""
    for token in MarkdownIt("commonmark").parse(content):
        if token.type == "heading_open":
            heading = token.tag
        elif token.type == "heading_close":
            heading = ""
        elif token.type == "inline":
            text = "\n".join(line.strip() for line in token.content.splitlines()).strip()
            if heading in {"h1", "h2"}:
                section = {"out of scope": "negative_scope", "open questions": "ambiguities"}.get(
                    text.casefold(), ""
                )
                requirement = ""
            elif heading == "h3":
                requirement = (
                    text.removeprefix("Requirement: ") if text.startswith("Requirement: ") else ""
                )
                if requirement:
                    yield "requirements", f"{capability}:{requirement}"
            elif heading == "h4" and requirement and text.startswith("Scenario: "):
                yield "edge_cases", f"{capability}:{requirement}:{text.removeprefix('Scenario: ')}"
            elif not heading and section and text:
                yield section, text
