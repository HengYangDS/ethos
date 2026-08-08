"""Repository-root binding for CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from ethos.adapters.repo.git import run_git

RootOption = Annotated[Path, Parameter(name="--root")]


def resolve_root(root: Path | None) -> Path:
    """Resolve an explicit path or the containing Git worktree root."""
    candidate = (root or Path.cwd()).resolve()
    completed = run_git(candidate, "rev-parse", "--show-toplevel", check=False)
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return candidate
