"""Repository-root binding for CLI commands."""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.repo.git import run_git

RootOption = Annotated[Path, Parameter(name="--root")]
# The root a command resolved; its oversized result detail belongs in that repository's store.
_RESOLVED_ROOT: ContextVar[Path | None] = ContextVar("ethos_resolved_root", default=None)


def resolve_root(root: Path | None) -> Path:
    """Resolve an explicit path or the containing Git worktree root."""
    candidate = (root or Path.cwd()).resolve()
    completed = run_git(candidate, "rev-parse", "--show-toplevel", check=False)
    if completed.returncode == 0 and completed.stdout.strip():
        candidate = Path(completed.stdout.strip()).resolve()
    _RESOLVED_ROOT.set(candidate)
    return candidate


def resolved_root() -> Path | None:
    """Return the root this invocation's command resolved, if it resolved one."""
    return _RESOLVED_ROOT.get()
