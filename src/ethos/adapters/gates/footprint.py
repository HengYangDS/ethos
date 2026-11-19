"""What a run of gates left in a lane, as the difference of two observations.

An observation reads Git's listing of nontracked paths, collapsed to directories; the files of
the homes that the artifact topology keeps a run's output in, by name, size and modification
time; and the names directly under the work home. The report names what appeared or changed
between two observations. It decides nothing: a lane that cannot be observed reports why, and
the report is empty when nothing appeared. A write inside a root that Git lists whole, such as
an environment or a tool cache, is not seen.
"""

from __future__ import annotations

import os
from collections import Counter
from contextlib import suppress
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.gates.host_work import WORK_HOME
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import run_git
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration

if TYPE_CHECKING:
    from collections.abc import Mapping

type _Files = dict[str, tuple[int, int]]


@dataclass(frozen=True, slots=True)
class LaneObservation:
    """A lane's nontracked roots, the files of its kept homes and its work names, or why none."""

    roots: frozenset[str] = frozenset()
    files: Mapping[str, _Files] = field(default_factory=dict)
    work: frozenset[str] = frozenset()
    unavailable: str = ""


def _kept_homes() -> tuple[tuple[str, str], ...]:
    """Return each home that keeps a run's output with its lifecycle class; never the work home."""
    declared = load_generated_artifact_topology_declaration().lifecycle_class
    return tuple(
        (item.id, home) for item in declared if WORK_HOME not in item.homes for home in item.homes
    )


def _files(home: Path) -> _Files:
    """Return the size and modification time of each file under a home; a link is not followed."""
    found: _Files = {}
    for parent, _directories, names in os.walk(home):
        for name in names:
            path = Path(parent, name)
            with suppress(OSError):
                status = path.lstat()
                found[path.relative_to(home).as_posix()] = (status.st_size, status.st_mtime_ns)
    return found


def _names(directory: Path) -> frozenset[str]:
    """Return the names directly in a directory; none where the host says there is no entry."""
    try:
        return frozenset(path.name for path in directory.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        return frozenset()


def observe_lane(root: Path) -> LaneObservation:
    """Observe one lane; a listing that fails or a home that cannot be read names itself."""
    try:
        listed = run_git(
            root, "ls-files", "-z", "--others", "--directory", check=False, observation=True
        )
        if listed.returncode:
            return LaneObservation(unavailable="git_listing")
        files = {home: _files(root / home) for _kind, home in _kept_homes()}
        work = _names(root / WORK_HOME)
    except (OSError, ProcessExecutionError) as error:
        return LaneObservation(unavailable=type(error).__name__)
    return LaneObservation(frozenset(filter(None, listed.stdout.split("\0"))), files, work)


def lane_before(root: Path, *, execute: bool) -> LaneObservation | None:
    """Observe a lane whose gates are about to run; a run that executes none observes nothing."""
    return observe_lane(root) if execute else None


def footprint_entry(root: Path, before: LaneObservation | None) -> dict[str, object]:
    """Return the entry of a result's data that reports a run's footprint; none unobserved."""
    return {} if before is None else {"footprint": footprint_report(root, before)}


def _changed(before: _Files, after: _Files) -> dict[str, int]:
    """Return the size of each file that appeared or changed between two readings of a home."""
    return {path: state[0] for path, state in sorted(after.items()) if before.get(path) != state}


def footprint_report(root: Path, before: LaneObservation) -> dict[str, object]:
    """Return what appeared or changed in a lane since an observation; empty when nothing did.

    Its scalar members count each lifecycle class's files and bytes, the new work names and the
    new nontracked roots, so a bounded result keeps them while the paths move to its detail.
    """
    after = observe_lane(root)
    if before.unavailable or after.unavailable:
        return {"unavailable": before.unavailable or after.unavailable}
    counts: Counter[str] = Counter()
    homes: dict[str, object] = {}
    for kind, home in _kept_homes():
        changed = _changed(before.files.get(home, {}), after.files[home])
        if changed:
            size = sum(changed.values())
            homes[home] = {"files": len(changed), "bytes": size, "paths": [*changed]}
            counts.update({f"{kind}_files": len(changed), f"{kind}_bytes": size})
    work, roots = sorted(after.work - before.work), sorted(after.roots - before.roots)
    counts.update(work_names=len(work), new_roots=len(roots))
    listed: dict[str, object] = {"homes": homes, "work": work, "roots": roots}
    return {name: value for name, value in {**counts, **listed}.items() if value}
