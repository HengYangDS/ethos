"""Read Git's worktree list whole: one attribute map per worktree, from NUL-terminated porcelain.

`git worktree list --porcelain -z` ends every attribute with NUL instead of a newline and ends every
record with one empty attribute, so a path or a lock reason that holds a newline stays one value.
A record starts with `worktree`, and a label and its value are separated by one space. `bare` and
`detached` are labels alone; `locked` is a label alone or a label and its reason, and `prunable`
carries Git's reason. With `-z` Git writes a lock reason unquoted, where the newline form quotes it
as `core.quotePath` does (git-worktree(1), "Porcelain Format" and the `-z` option).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.git import run_git
from ethos.contracts.outcome import refuse

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from pathlib import Path


def parse_worktree_list(listing: str) -> tuple[dict[str, str], ...]:
    """Map each record of a NUL-terminated listing from its labels to their exact values.

    A label alone maps to the empty string, so a flag is present or absent, never true or false.
    """
    return tuple(
        dict(field.partition(" ")[::2] for field in record.split("\0") if field)
        for record in listing.split("\0\0")
        if record
    )


def listed_worktrees(
    root: Path,
    *,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
) -> tuple[dict[str, str], ...] | None:
    """Observe each worktree record that Git lists for `root`, or None when Git cannot list them."""
    completed = runner(root, "worktree", "list", "--porcelain", "-z", check=False, env=environment)
    return None if completed.returncode else parse_worktree_list(completed.stdout)


def raw_worktree_records(
    root: Path,
    *,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., Any] = run_git,
    gap: str = "worktree_effect_observation_failed",
) -> tuple[dict[str, str], ...]:
    """Observe every worktree record whole; when Git cannot list them, refuse with `gap`."""
    records = listed_worktrees(root, environment=environment, runner=runner)
    if records is None:
        refuse(gap)
    return records
