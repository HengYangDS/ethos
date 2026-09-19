"""Native compilers for source-bound generated repository projections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.projections.cue import compile_projections

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.repository.policy.projections import Projection


def render_projections(
    root: Path,
    relations: tuple[Projection, ...],
    files: Mapping[str, str],
    changes: Mapping[str, str | None],
) -> dict[str, str]:
    """Compile each affected native owner once using only supplied material bytes."""
    declarations = {
        item.declaration
        for item in relations
        if item.kind == "cue" and changes.keys() & set(item.materials)
    }
    rendered: dict[str, str] = {}
    for declaration in sorted(declarations):
        group = tuple(item for item in relations if item.declaration == declaration)
        if any(path not in files for item in group for path in (item.source, *item.inputs)):
            continue
        providers = compile_projections(root, declaration, files)
        rendered.update({item.output: providers[item.provider] for item in group})
    return rendered
