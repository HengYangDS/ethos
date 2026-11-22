"""Judge a staged admission's OpenSpec scope by the staged tree's own files."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.openspec.projection import openspec_tree_projection
from ethos.adapters.openspec.projection import report_carriers
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from pathlib import Path

    Scope = tuple[dict[str, object], dict[str, object], bool]

# The obligation that a staged admission is judged by its staged tree alone.
STAGED_TREE = "staged-openspec-tree"
_UNOBSERVED = "openspec_tree_projection_missing"


def staged_tree_scope(
    root: Path,
    tree: object,
    environment: Mapping[str, str] | None,
    evaluate: Callable[[Path | None], Scope],
    *,
    working_files: bool = False,
) -> Scope:
    """Return the OpenSpec scope of a staged admission, judged by its staged tree.

    `evaluate` resolves the scope with every file read below the root that it is given, and at
    the working files for None; Git, the Lease and history are read at `root` either way. An
    admission without a staged tree, or one that resolves in the working files, is the working
    files' alone. The staged tree's answer stands when it passes, and it names that tree. While
    the obligation reports, an answer that does not pass yields to the working files' answer,
    which then carries the staged tree's gaps as reported, and a staged tree that cannot be
    observed, or whose evaluation fails, is reported as `openspec_tree_projection_missing` with
    the fault's type, and the working files answer. Once the obligation is armed the staged tree
    alone decides, and a tree that cannot be observed is refused.
    """
    if working_files or not tree:
        return evaluate(None)
    tree = str(tree)
    try:
        carriers = report_carriers(root, tree, environment=environment)
        with openspec_tree_projection(
            root, tree, carriers=carriers, environment=environment
        ) as files:
            scope, official, invalid = _named_by_tree(evaluate(files), files, root)
        official["observed_tree"] = tree
        passed = report_verdict(scope) == "pass"
    except Exception as error:
        # While the obligation reports, no fault of the staged evaluation may change the verdict.
        gap = f"{_UNOBSERVED}:{type(error).__name__}"
        unobserved: Scope = ({"verdict": "unknown", "required_gaps": [gap]}, {}, False)
        (scope, official, invalid), passed = unobserved, False
    if passed or load_repository_paradigm().armed(STAGED_TREE):
        return scope, official, invalid
    working, official, invalid = evaluate(None)
    return {**working, "reported_gaps": scope.get("required_gaps", [])}, official, invalid


def _named_by_tree(result: Scope, files: Path, root: Path) -> Scope:
    """Name repository-relative paths, and the lane in a next action, never the projection."""
    spellings = tuple(sorted({files.as_posix(), files.resolve().as_posix()}, key=len, reverse=True))
    lane = root.resolve().as_posix()

    def named(value: object, *, action: bool = False) -> object:
        if isinstance(value, dict):
            return {key: named(item, action=key == "next_action") for key, item in value.items()}
        if isinstance(value, list | tuple):
            return type(value)(named(item, action=action) for item in value)
        return _respelled(value, spellings, lane if action else None)

    scope, official, invalid = result
    return cast("Scope", (named(scope), named(official), invalid))


def _respelled(value: object, spellings: tuple[str, ...], lane: str | None) -> object:
    """Spell a projection path as the lane's root in an action, else relative to the repository."""
    if not isinstance(value, str):
        return value
    for spelling in spellings:
        value = (
            value.replace(f"{spelling}/", "").replace(spelling, ".")
            if lane is None
            else value.replace(spelling, lane)
        )
    return value
