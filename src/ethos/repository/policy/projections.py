"""Native producer relations, rendering and exact projection retirement."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

PROJECTION_DECLARATIONS = {
    ".config/checks/architecture/projection.toml": (
        "ethos-architecture-projection-v1",
        "source",
        "output",
        "likec4-to-mermaid",
    ),
    ".config/checks/ci/templates.toml": (
        "ethos-ci-template-consistency-v1",
        "template",
        "projection",
        "copy",
    ),
}

SOURCE_BINDING_DECLARATION = "system/projections/terminal-architecture/declaration.json"


def source_binding_inputs(declaration: bytes) -> tuple[str, dict[str, dict[str, str]]]:
    """Resolve the native graph's partial, multi-input derived binding fields."""
    payload = json.loads(declaration)
    if not isinstance(payload, dict) or payload.get("schema") != "ethos.projection-declaration/v1":
        message = "source_binding_declaration_invalid"
        raise ValueError(message)
    documents, sources = payload.get("documents"), payload.get("sources")
    if not isinstance(documents, dict) or not isinstance(sources, list) or not sources:
        message = "source_binding_declaration_invalid"
        raise ValueError(message)
    output = _local_path(documents.get("semantic_graph"), SOURCE_BINDING_DECLARATION)
    bindings: dict[str, dict[str, str]] = {}
    for item in sources:
        if not isinstance(item, dict):
            message = "source_binding_declaration_invalid"
            raise TypeError(message)
        identity, authority = item.get("id"), item.get("authority")
        source = _local_path(item.get("path"), SOURCE_BINDING_DECLARATION)
        if (
            not isinstance(identity, str)
            or not identity
            or identity in bindings
            or not isinstance(authority, str)
            or not authority
            or source == output
        ):
            message = "source_binding_declaration_invalid"
            raise ValueError(message)
        bindings[identity] = {"path": source, "authority": authority}
    return output, bindings


def render_source_bindings(
    graph: bytes,
    bindings: Mapping[str, Mapping[str, str]],
    before: Mapping[str, bytes],
    after: Mapping[str, bytes],
) -> bytes:
    """Refresh only exact digest fields; neither accept nor rewrite authored meaning."""
    payload = json.loads(graph)
    validate_source_bindings(payload, bindings, before)
    changed = False
    for identity, binding in bindings.items():
        source = binding["path"]
        if source not in after:
            message = f"source_binding_input_missing:{identity}"
            raise ValueError(message)
        row = payload["sources"][identity]
        digest = hashlib.sha256(after[source]).hexdigest()
        changed |= row["sha256"] != digest
        row["sha256"] = digest
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode() if changed else graph


def validate_source_bindings(
    graph: object,
    bindings: Mapping[str, Mapping[str, str]],
    sources: Mapping[str, bytes],
) -> None:
    """Validate identity, role and bytes for both native refresh and exact export."""
    declared = graph.get("sources") if isinstance(graph, dict) else None
    if not isinstance(declared, dict) or declared.keys() != bindings.keys():
        message = "source_binding_graph_invalid"
        raise ValueError(message)
    for identity, binding in bindings.items():
        row = declared[identity]
        if not isinstance(row, dict):
            message = f"source_binding_graph_invalid:{identity}"
            raise TypeError(message)
        for key, value in binding.items():
            if row.get(key) != value:
                message = f"source {key} mismatch: {identity}"
                raise ValueError(message)
        if binding["path"] not in sources:
            message = f"source_binding_input_missing:{identity}"
            raise ValueError(message)
        if row.get("sha256") != hashlib.sha256(sources[binding["path"]]).hexdigest():
            message = f"source digest mismatch: {identity}"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class Projection:
    """One native source-to-output relation, not an authorizing caller label."""

    declaration: str
    source: str
    output: str
    kind: str

    def render(self, text: str) -> str:
        """Render with the same pure producer used by native quality checks."""
        return render_architecture(self.source, text) if self.kind == "likec4-to-mermaid" else text


def projection_relations(files: Mapping[str, str]) -> tuple[Projection, ...]:
    """Read native declarations strictly, preserving conflicting output ownership."""
    relations: list[Projection] = []
    outputs: set[str] = set()
    for path, (schema, source_key, output_key, kind) in PROJECTION_DECLARATIONS.items():
        if path not in files:
            continue
        payload = tomllib.loads(files[path])
        if payload.get("schema") != schema or not isinstance(payload.get("projection", []), list):
            msg = f"projection_declaration_invalid:{path}"
            raise ValueError(msg)
        for entry in payload.get("projection", []):
            if not isinstance(entry, dict) or entry.get("kind", kind) != kind:
                msg = f"projection_kind_unknown:{path}"
                raise ValueError(msg)
            source, output = (_local_path(entry.get(key), path) for key in (source_key, output_key))
            if source == output or output in outputs or output in PROJECTION_DECLARATIONS:
                msg = f"projection_owner_conflict:{output}:{path}"
                raise ValueError(msg)
            outputs.add(output)
            relations.append(Projection(path, source, output, kind))
    return tuple(relations)


def _local_path(value: object, declaration: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        msg = f"projection_path_invalid:{declaration}"
        raise ValueError(msg)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() == ".":
        msg = f"projection_path_invalid:{declaration}:{value}"
        raise ValueError(msg)
    return path.as_posix()


def observe_projections(root: Path) -> tuple[Projection, ...]:
    """Observe declared producer ownership, including currently absent outputs."""
    files: dict[str, str] = {}
    for relative in PROJECTION_DECLARATIONS:
        path = root / relative
        if path.exists():
            if not path.resolve().is_relative_to(root.resolve()):
                msg = f"projection_declaration_outside_root:{relative}"
                raise ValueError(msg)
            files[relative] = path.read_text(encoding="utf-8")
    return projection_relations(files)


def projection_effect_gaps(
    before: tuple[Projection, ...],
    after: tuple[Projection, ...],
    files: Mapping[str, str],
    changes: Mapping[str, str | None],
) -> list[str]:
    """Check affected generation and require joint output/producer retirement."""
    gaps: list[str] = []
    affected = {
        item.output
        for item in (*before, *after)
        if changes.keys() & {item.declaration, item.source, item.output}
    }
    remaining = {item.output for item in after}
    gaps.extend(
        f"generated_projection_owner_removed:{item.output}"
        for item in before
        if item.output in affected
        and item.output not in remaining
        and (item.output not in changes or changes[item.output] is not None)
    )
    for item in after:
        if item.output not in affected:
            continue
        source, output = files.get(item.source), files.get(item.output)
        if source is None:
            gaps.append(f"generated_projection_input_missing:{item.source}")
        elif output is None:
            gaps.append(f"generated_projection_missing:{item.output}")
        elif item.render(source) != output:
            gaps.append(f"generated_projection_drift:{item.output}")
    return sorted(set(gaps))


def render_architecture(source: str, text: str) -> str:
    """Project the existing C4-like source subset to deterministic Mermaid bytes."""
    nodes: dict[str, str] = {}
    relations: list[tuple[str, str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split('"')
        if line.startswith(("system ", "container ")) and len(parts) >= 2:
            head = parts[0].split()
            label = [parts[1]]
            if len(parts) >= 4 and parts[3].strip():
                label.append(parts[3])
            nodes[head[1]] = " ".join(label).strip()
        elif line.startswith("rel ") and len(parts) >= 2:
            head = parts[0].split()
            relations.append((head[1], head[2], parts[1]))
    lines = [f"%% Generated from {source}. Do not edit by hand.", "flowchart LR"]
    lines.extend(f'  {ident}["{label}"]' for ident, label in nodes.items())
    lines.extend(f'  {left} -->|"{label}"| {right}' for left, right, label in relations)
    return "\n".join(lines) + "\n"
