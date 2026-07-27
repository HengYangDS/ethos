"""Repository-root binding for CLI commands."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

RootOption = Annotated[Path, Parameter(name="--root")]


def resolve_root(root: Path | None) -> Path:
    """Resolve an explicit path or the containing Git worktree root."""
    candidate = (root or Path.cwd()).resolve()
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=candidate,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        return candidate
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return candidate
