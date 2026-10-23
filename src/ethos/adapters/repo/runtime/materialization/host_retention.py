"""Retire host-store installations that no recorded consumer still needs.

A repository records itself in each installation it selects or holds as rollback supply. An
installation is retired only when every recorded consumer is gone or names it in neither its
selector (`CURRENT`) nor its rollback selector (`ROLLBACK`), and no running process or binding
refers into it. An installation pinned before consumers were recorded has unknown users, so it
stays; so does one whose consumer record or selector cannot be read.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal

from filelock import FileLock

from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes

if TYPE_CHECKING:
    from collections.abc import Callable

_HEX = frozenset("0123456789abcdef")


def retire_unused_installations(
    store: Path, *, in_use: Callable[[], frozenset[Path]]
) -> dict[str, object]:
    """Retire each recorded installation that no consumer, process or binding still needs."""
    retired: list[str] = []
    retained: list[str] = []
    unrecorded = 0
    references: frozenset[Path] | None = None
    if not store.is_dir() or store.is_symlink():
        return {"retired": retired, "retained": retained, "unrecorded": unrecorded}
    with FileLock(
        store / "install.lock", timeout=10, fallback_to_soft=False, preserve_lock_file=True
    ):
        for installation in sorted(store.iterdir()):
            if not _index(installation.name) or installation.is_symlink():
                continue
            consumers = installation_consumers(installation)
            if consumers is None:
                unrecorded += 1
                continue
            needed = False
            for record, consumer in consumers.items():
                if _consumer_state(consumer, installation) == "released":
                    record.unlink(missing_ok=True)
                else:
                    needed = True
            if not needed:
                references = in_use() if references is None else references
                needed = any(path.is_relative_to(installation) for path in references)
            if needed:
                retained.append(installation.as_posix())
                continue
            remove_generated_tree(installation)
            retired.append(installation.as_posix())
    return {"retired": retired, "retained": retained, "unrecorded": unrecorded}


def _consumer_state(
    consumer: Path | None, installation: Path
) -> Literal["needs", "released", "unknown"]:
    if consumer is None:
        return "unknown"
    if not consumer.exists() and not consumer.is_symlink():
        return "released"
    try:
        named = [_named_runtime(consumer, name) for name in ("CURRENT", "ROLLBACK")]
    except (OSError, UnicodeError, ValueError):
        return "unknown"
    return (
        "needs" if any(path and path.is_relative_to(installation) for path in named) else "released"
    )


def _named_runtime(common: Path, name: str) -> Path | None:
    """Read one runtime selector in the `CURRENT` encoding; an absent selector names nothing."""
    selector = common / "ethos/runtime" / name
    if not selector.exists() and not selector.is_symlink():
        return None
    if selector.is_symlink():
        raise ValueError(name)
    raw = selector.read_bytes()
    parts = raw.decode("utf-8").removesuffix("\n").split("\n")
    root = common.resolve()
    candidate = root / "ethos/runtime" / parts[0] if len(parts) == 1 else Path(parts[-1])
    if len(parts) not in {1, 2} or runtime_selection_bytes(root, candidate) != raw:
        raise ValueError(name)
    return candidate


def _index(value: str) -> bool:
    return len(value) == 16 and not set(value) - _HEX
