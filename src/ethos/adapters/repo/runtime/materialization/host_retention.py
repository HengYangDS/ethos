"""Retire host-store installations that no recorded consumer still needs.

A repository records itself in each installation it selects or holds as rollback supply. An
installation is retired only when every recorded consumer is gone or names it in neither its
selector (`CURRENT`) nor its rollback selector (`ROLLBACK`), and no running process or binding
refers into it. An installation pinned before consumers were recorded has unknown users, so it
stays; so does one whose consumer record or selector cannot be read.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal

from filelock import FileLock

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.host_store import record_consumer
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


def legacy_supply(
    store: Path,
    *,
    consumers: tuple[Path, ...],
    in_use: Callable[[], frozenset[Path]],
    grace_seconds: float,
    apply: bool,
    expected_plan: str | None = None,
) -> dict[str, object]:
    """Plan, and on apply retire, the installations pinned before consumers were recorded.

    An unrecorded installation stays when a scanned repository's selector or rollback selector
    names it or cannot be read, when a running process or binding refers into it, or when it
    changed within the grace period, as an older ETHOS may have just pinned it as unrecorded
    rollback supply. Apply checks the previewed plan first, then records each naming repository
    as a consumer and retires exactly the planned installations; a changed plan changes nothing.
    """
    retired: list[str] = []
    if not store.is_dir() or store.is_symlink():
        return _legacy_report([], [], retired)
    with FileLock(
        store / "install.lock", timeout=10, fallback_to_soft=False, preserve_lock_file=True
    ):
        rows = _legacy_rows(store, consumers, in_use, grace_seconds)
        retirable = [installation for installation, reason, _named in rows if not reason]
        kept: list[dict[str, object]] = [
            {
                "installation": installation.as_posix(),
                "reason": reason,
                "named_by": [common.as_posix() for common in named],
            }
            for installation, reason, named in rows
            if reason
        ]
        # Sizes are measured before anything is removed, so an apply reports what it reclaimed.
        report = _legacy_report(retirable, kept, retired)
        if apply:
            if expected_plan != report["plan_digest"]:
                message = "host_store_plan_changed"
                raise ValueError(message)
            for installation, _reason, named in rows:
                for common in named:
                    record_consumer(installation, common)
            for installation in retirable:
                remove_generated_tree(installation)
                retired.append(installation.as_posix())
    return report


def _legacy_rows(
    store: Path,
    consumers: tuple[Path, ...],
    in_use: Callable[[], frozenset[Path]],
    grace_seconds: float,
) -> list[tuple[Path, str, list[Path]]]:
    """Classify each unrecorded installation; an empty reason means nothing still needs it."""
    rows: list[tuple[Path, str, list[Path]]] = []
    references: frozenset[Path] | None = None
    for installation in sorted(store.iterdir()):
        if not _index(installation.name) or installation.is_symlink():
            continue
        if installation_consumers(installation) is not None:
            continue
        states = {common: _consumer_state(common, installation) for common in consumers}
        named = [common for common, state in states.items() if state == "needs"]
        reason = "named" if named else "uncertain" if "unknown" in states.values() else ""
        if not reason:
            references = in_use() if references is None else references
            reason = _idle_reason(installation, references, grace_seconds)
        rows.append((installation, reason, named))
    return rows


def _idle_reason(installation: Path, references: frozenset[Path], grace_seconds: float) -> str:
    if any(path.is_relative_to(installation) for path in references):
        return "in_use"
    return "recent" if time.time() - installation.stat().st_mtime < grace_seconds else ""


def repository_common_dirs(roots: tuple[Path, ...]) -> tuple[Path, ...]:
    """Find the Git common directory of each repository at a scanned root or directly under it."""
    commons: set[Path] = set()
    for root in roots:
        children = sorted(child for child in root.iterdir() if child.is_dir())
        for candidate in (root, *children):
            if not (candidate / ".git").exists():
                continue
            found = run_git(
                candidate, "rev-parse", "--path-format=absolute", "--git-common-dir", check=False
            )
            if not found.returncode and found.stdout.strip():
                commons.add(Path(found.stdout.strip()).resolve())
    return tuple(sorted(commons))


def _legacy_report(
    retirable: list[Path], kept: list[dict[str, object]], retired: list[str]
) -> dict[str, object]:
    sizes = [_size(path) for path in retirable]
    return {
        "plan_digest": _plan_digest(retirable),
        "retirable": [
            {"installation": path.as_posix(), "bytes": size}
            for path, size in zip(retirable, sizes, strict=True)
        ],
        "retirable_bytes": sum(sizes),
        "kept": kept,
        "retired": retired,
    }


def _plan_digest(retirable: list[Path]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(path.as_posix() for path in retirable)).encode()
    ).hexdigest()


def _size(path: Path) -> int:
    total = 0
    for parent, _directories, files in os.walk(path):
        for name in files:
            with contextlib.suppress(OSError):
                total += Path(parent, name).lstat().st_size
    return total
