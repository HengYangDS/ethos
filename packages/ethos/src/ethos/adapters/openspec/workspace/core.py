from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def openspec_workspace_signature(root: Path) -> tuple[tuple[str, int, int], ...]:
    """Return a stable cache signature for tracked OpenSpec workspace files."""
    openspec_root = root / "openspec"
    if not openspec_root.exists():
        return ()
    signature: list[tuple[str, int, int]] = []
    for path in sorted(item for item in openspec_root.rglob("*") if item.is_file()):
        stat = path.stat()
        signature.append((path.relative_to(root).as_posix(), stat.st_mtime_ns, stat.st_size))
    return tuple(signature)
