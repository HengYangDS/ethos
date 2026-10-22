"""Native producer relations, rendering and exact projection retirement."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

PROJECTION_DECLARATIONS = {
    ".config/checks/architecture-projection/policy.toml": (
        "ethos-architecture-projection-v1",
        "source",
        "output",
        "likec4-to-mermaid",
    ),
    ".config/checks/ci-projection/policy.toml": (
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
    inputs: tuple[str, ...] = ()
    provider: str = ""

    @property
    def materials(self) -> tuple[str, ...]:
        """Return the complete declared input/output closure for this projection."""
        return (self.declaration, self.source, *self.inputs, self.output)

    def render(self, text: str) -> str:
        """Render with the same pure producer used by native quality checks."""
        if self.kind == "likec4-to-mermaid":
            return render_architecture(self.source, text)
        if self.kind == "copy":
            return text
        msg = f"projection_requires_native_compiler:{self.output}"
        raise ValueError(msg)


def projection_relations(files: Mapping[str, str]) -> tuple[Projection, ...]:
    """Read native declarations strictly, preserving conflicting output ownership."""
    relations: list[Projection] = []
    outputs: set[str] = set()
    for path, (schema, source_key, output_key, kind) in PROJECTION_DECLARATIONS.items():
        if path not in files:
            continue
        try:
            payload = tomllib.loads(files[path])
        except tomllib.TOMLDecodeError as error:
            msg = f"projection_declaration_invalid:{path}"
            raise ValueError(msg) from error
        if payload.get("schema") != schema or not isinstance(payload.get("projection", []), list):
            msg = f"projection_declaration_invalid:{path}"
            raise ValueError(msg)
        providers: set[str] = set()
        for entry in payload.get("projection", []):
            if not isinstance(entry, dict) or entry.get("kind", kind) not in {kind, "cue"}:
                msg = f"projection_kind_unknown:{path}"
                raise ValueError(msg)
            selected_kind = entry.get("kind", kind)
            if selected_kind == "cue":
                source, inputs, provider = _compiler_relation(payload, entry, path)
                if provider in providers:
                    msg = f"projection_provider_conflict:{path}:{provider}"
                    raise ValueError(msg)
                providers.add(provider)
            else:
                source, inputs, provider = _local_path(entry.get(source_key), path), (), ""
            output = _local_path(entry.get(output_key), path)
            if source == output or output in outputs or output in PROJECTION_DECLARATIONS:
                msg = f"projection_owner_conflict:{output}:{path}"
                raise ValueError(msg)
            outputs.add(output)
            relations.append(Projection(path, source, output, selected_kind, inputs, provider))
    return tuple(relations)


def projection_input_bindings(values: object, declaration: str) -> dict[str, tuple[str, str]]:
    """Resolve one typed native input contract for compilation and source closure."""
    if not isinstance(values, dict):
        msg = f"projection_inputs_invalid:{declaration}"
        raise TypeError(msg)
    bindings = {}
    for key, value in values.items():
        if not isinstance(key, str) or not key:
            msg = f"projection_input_name_invalid:{declaration}"
            raise ValueError(msg)
        if isinstance(value, str):
            path, kind = value, "toml"
        elif (
            isinstance(value, dict)
            and set(value) == {"path", "format"}
            and isinstance(value["format"], str)
            and value["format"] in {"toml", "json"}
        ):
            path, kind = value["path"], value["format"]
        else:
            msg = f"projection_input_invalid:{declaration}:{key}"
            raise ValueError(msg)
        bindings[key] = (_local_path(path, declaration), kind)
    return bindings


def _compiler_relation(
    payload: dict, entry: dict, declaration: str
) -> tuple[str, tuple[str, ...], str]:
    compiler = payload.get("compiler")
    if (
        not isinstance(compiler, dict)
        or not isinstance(compiler.get("inputs"), dict)
        or ("supply" in compiler and not isinstance(compiler["supply"], dict))
        or ("supply" not in compiler and not compiler.get("common"))
        or not isinstance(entry.get("provider"), str)
        or not entry["provider"]
    ):
        msg = f"projection_compiler_invalid:{declaration}"
        raise ValueError(msg)
    source = _local_path(compiler.get("source"), declaration)
    bindings = projection_input_bindings(compiler["inputs"], declaration)
    common = compiler.get("common")
    if common is not None and common != ".config/ci/verification.cue":
        msg = f"projection_common_model_unknown:{declaration}"
        raise ValueError(msg)
    supply = compiler.get("supply", {})
    inputs = (
        *(path for path, _kind in bindings.values()),
        *(
            (
                _local_path(supply.get("config"), declaration),
                _local_path(supply.get("lock"), declaration),
            )
            if "supply" in compiler
            else ()
        ),
    )
    return source, inputs, entry["provider"]


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
            try:
                files[relative] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                msg = f"projection_declaration_unavailable:{relative}"
                raise ValueError(msg) from error
    return projection_relations(files)


def projection_effect_gaps(
    before: tuple[Projection, ...],
    after: tuple[Projection, ...],
    files: Mapping[str, str],
    changes: Mapping[str, str | None],
    compiled: Mapping[str, str] | None = None,
) -> list[str]:
    """Check affected generation and require joint output/producer retirement."""
    gaps: list[str] = []
    affected = {item.output for item in (*before, *after) if changes.keys() & set(item.materials)}
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
        output = files.get(item.output)
        missing = [path for path in (item.source, *item.inputs) if path not in files]
        if missing:
            gaps.extend(f"generated_projection_input_missing:{path}" for path in missing)
        elif output is None:
            gaps.append(f"generated_projection_missing:{item.output}")
        elif item.kind == "cue":
            if compiled is None or item.output not in compiled:
                msg = f"compiled_projection_unavailable:{item.output}"
                raise ValueError(msg)
            if compiled[item.output] != output:
                gaps.append(f"generated_projection_drift:{item.output}")
        elif item.render(files[item.source]) != output:
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
