"""The record binding: `[artifacts]` in `rules.toml` retires into the profile's `record_roots`.

No reader consults `[artifacts]`. Its `durable_evidence_roots` name what the effective record roots
hold now, as whole directories, and `state_tracked_truth` has no successor. The roots move first:
while the profile lacks one of them, the only gap is the profile's, and the table's own gap appears
once the profile holds every root, so no repair drops a root on the way.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm

OBLIGATION = "record-binding"
ROOTS = "record_roots"
TABLE = "artifacts"


def record_binding_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str], rules: str | None
) -> list[ParadigmGap]:
    """Report the roots the profile still lacks, and only then the table that retires."""
    table = _parsed(rules).get(TABLE)
    if not isinstance(table, dict):
        return []
    profile, carrier = paradigm.binding.path("profile"), paradigm.binding.path("rules")
    paths = table.get("durable_evidence_roots", [])
    if not isinstance(paths, list) or not all(
        isinstance(path, str) and _relative(path) for path in paths
    ):
        repair = f"name each durable evidence root as a repository directory in {carrier}"
        return [ParadigmGap(OBLIGATION, f"{carrier}:{TABLE}.durable_evidence_roots", repair)]
    held = _parsed(tracked_text(root, profile, tracked)).get(ROOTS, [])
    held = [path for path in held if isinstance(path, str)] if isinstance(held, list) else []
    if missing := [path for path in folded_roots(paths) if not path.startswith(tuple(held))]:
        roots = folded_roots([*held, *missing])
        repair = f"declare {ROOTS} = {roots} in {profile}, then repair again to retire [{TABLE}]"
        return [ParadigmGap(OBLIGATION, f"{profile}:{ROOTS}={','.join(roots)}", repair)]
    return [
        ParadigmGap(
            OBLIGATION, f"{carrier}:{TABLE}", f"remove [{TABLE}]; {profile} holds its roots"
        )
    ]


def folded_roots(paths: Iterable[str]) -> list[str]:
    """Return each path as a directory root, without a root that another one holds."""
    roots = sorted({path.removesuffix("/") + "/" for path in paths})
    return [
        path
        for path in roots
        if not any(path != other and path.startswith(other) for other in roots)
    ]


def _relative(path: str) -> bool:
    """Whole segments under the repository root; no empty, `.` or `..` segment."""
    parts = path.removesuffix("/").split("/")
    return not path.startswith("/") and all(part not in {"", ".", ".."} for part in parts)


def _parsed(text: str | None) -> dict[str, object]:
    try:
        return tomllib.loads(text or "")
    except tomllib.TOMLDecodeError:
        return {}
