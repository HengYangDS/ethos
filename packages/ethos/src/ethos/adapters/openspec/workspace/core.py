from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def openspec_workspace_signature(root: Path) -> tuple[tuple[str, int, int], ...]:
    """Return a cache signature for OpenSpec and its profile-owned companion.

    The material-path declaration is deliberately outside the official OpenSpec
    workspace, but it participates in the lifecycle read model.  Include an
    explicit missing-file sentinel so creating or deleting the profile also
    invalidates a previously cached lifecycle result.
    """
    openspec_root = root / "openspec"
    signature: list[tuple[str, int, int]] = []
    if openspec_root.exists():
        for path in sorted(item for item in openspec_root.rglob("*") if item.is_file()):
            stat = path.stat()
            signature.append((path.relative_to(root).as_posix(), stat.st_mtime_ns, stat.st_size))
    profile = root / ".ethos" / "profile.toml"
    if profile.exists():
        stat = profile.stat()
        signature.append((".ethos/profile.toml", stat.st_mtime_ns, stat.st_size))
    else:
        signature.append((".ethos/profile.toml", -1, -1))
    return tuple(signature)
