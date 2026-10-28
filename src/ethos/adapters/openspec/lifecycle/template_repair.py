"""Bounded repair of active Change artifacts that drifted from their official templates.

Template drift is reported by ETHOS, not by the official validator, so a Change that
strict validation accepts can still be blocked by it. Its exact drifted artifacts are
then the only writable paths, which lets the drift be repaired without bypassing any
other check.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from ethos.adapters.openspec.template_conformance import TEMPLATE_HEADING_GAP
from ethos.normalization.coercion import string_sequence


def _template_drifted_artifacts(official: dict[str, object], *, change: str) -> set[str]:
    """Name the selected Change's drifted artifacts when template drift alone blocks it.

    Another active Change's drift may block as well; it is repaired once that Change is
    selected, so two drifted Changes never hold each other's repair.
    """
    gaps = string_sequence(official.get("required_gaps"))
    if not gaps or not all(gap.startswith(TEMPLATE_HEADING_GAP) for gap in gaps):
        return set()
    return {parts[2] for gap in gaps if len(parts := gap.split(":", 3)) == 4 and parts[1] == change}


def other_change_template_drift(gap: str, change: str) -> bool:
    """Whether a gap is template drift of another active Change, which that Change repairs."""
    parts = gap.split(":", 3)
    return gap.startswith(TEMPLATE_HEADING_GAP) and len(parts) == 4 and parts[1] != change


def template_conformance_repair_paths(
    root: Path,
    official: dict[str, object],
    *,
    change: str,
    official_artifact_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Resolve the selected Change's template-drifted artifacts to its existing outputs."""
    drifted = _template_drifted_artifacts(official, change=change)
    commands = official.get("commands")
    status = commands.get("status") if isinstance(commands, dict) else None
    payload = status.get("json") if isinstance(status, dict) else None
    graphs = payload.get("artifactPaths") if isinstance(payload, dict) else None
    if not drifted or not isinstance(graphs, dict):
        return ()
    repository = root.resolve()
    outputs: set[str] = set()
    for name in drifted:
        graph = graphs.get(name)
        listed = graph.get("existingOutputPaths") if isinstance(graph, dict) else None
        for output in listed if isinstance(listed, list) else ():
            with contextlib.suppress(ValueError):
                outputs.add(Path(str(output)).relative_to(repository).as_posix())
    # The official outputs list already passed repository confinement; select from it.
    return tuple(path for path in official_artifact_paths if path in outputs)
