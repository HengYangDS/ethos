"""Native producer relations, rendering and exact projection retirement."""

from __future__ import annotations

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
