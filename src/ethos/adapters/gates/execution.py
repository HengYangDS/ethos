"""Resolve repository-selected native tools and retain their invocation lifetime."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.toolchain.mise import locked_environment
from ethos.adapters.toolchain.mise import locked_tool
from ethos.adapters.toolchain.mise import repository_mise_files

if TYPE_CHECKING:
    from contextlib import ExitStack


def native_tool(root: Path, name: str) -> str:
    """Select the declared locked executable rather than an ambient replacement."""
    if (files := repository_mise_files(root)) is not None:
        return str(locked_tool(root, name, files=files))
    path = shutil.which(name)
    if path is None:
        message = f"native_tool_unavailable:{name}"
        raise ValueError(message)
    return str(Path(path).resolve())


def native_environment(root: Path, scope: ExitStack) -> dict[str, str]:
    """Hold one selected tool graph through native execution and evidence observation."""
    files = repository_mise_files(root)
    return scope.enter_context(locked_environment(root, files)) if files is not None else {}
