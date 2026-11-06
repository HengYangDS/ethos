"""Read a mise lock as data: the aube sidecars it declares and its dependency-graph entries.

Neither reader runs mise or consults trust; the native boundary in `mise.py` owns both.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def lock_sidecars(root: Path, lock: str, content: str) -> tuple[str, ...]:
    """Name every file of each aube sidecar directory the lock declares, relative to root."""
    try:
        tools = tomllib.loads(content).get("tools", {})
    except tomllib.TOMLDecodeError as error:
        message = "locked_toolchain_invalid"
        raise ValueError(message) from error
    base = (root / lock).parent
    directories = {
        entry["aube"]["path"]
        for entries in (tools.values() if isinstance(tools, dict) else ())
        for entry in (entries if isinstance(entries, list) else ())
        if isinstance(entry, dict)
        and isinstance(entry.get("aube"), dict)
        and isinstance(entry["aube"].get("path"), str)
    }
    files: list[str] = []
    for directory in sorted(directories):
        sidecar = (base / directory).resolve()
        if not sidecar.is_relative_to(root):
            message = f"mise_lock_sidecar_outside_root:{directory}"
            raise ValueError(message)
        if not sidecar.is_dir():
            # Native mise reports a sidecar the lock names but the tree lacks.
            continue
        files.extend(
            path.relative_to(root).as_posix()
            for path in sorted(sidecar.rglob("*"))
            if path.is_file() and not path.is_symlink()
        )
    return tuple(files)


def graph_locked(lock: str, tools: list[str]) -> bool:
    """Whether a missing tool's lock entry references a dependency graph, such as an aube entry."""
    try:
        entries = tomllib.loads(lock).get("tools", {})
    except tomllib.TOMLDecodeError:
        return False
    return isinstance(entries, dict) and any(
        isinstance(entry, dict) and "aube" in entry
        for tool in tools
        for entry in (entries.get(tool) if isinstance(entries.get(tool), list) else ())
    )
