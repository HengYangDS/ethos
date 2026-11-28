"""Retire host-store installations that no recorded consumer still needs.

A repository records itself in each installation it selects or holds as rollback supply. An
installation is retired only when every recorded consumer names it in neither its selector
(`CURRENT`) nor its rollback selector (`ROLLBACK`), and no running process or binding refers into
it. An installation pinned before consumers were recorded has unknown users, so it stays; so does
one whose consumer record or selector cannot be read, one whose consumer holds its selection lock,
because a selection holds it from the pin that records the consumer until its selectors name what
it pinned, and one whose consumer path is gone, because a moved repository or an unmounted volume
looks the same as a removed one. The report names those absent consumers. Retention creates
nothing in a consumer without ETHOS state.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import stat
import time
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal

from filelock import FileLock

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.host_store import record_consumer
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import named_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_lock
from ethos.contracts.digest import is_hex
from ethos.repository.paradigm.parameters import seconds

if TYPE_CHECKING:
    from collections.abc import Callable


def retire_unused_installations(
    store: Path, *, in_use: Callable[[], frozenset[Path]]
) -> dict[str, object]:
    """Retire each recorded installation that no consumer, process or binding still needs."""
    retired: list[str] = []
    retained: list[str] = []
    kept: list[tuple[Path | None, str, str]] = []
    unrecorded = 0
    references: frozenset[Path] | None = None
    if not store.is_dir() or store.is_symlink():
        return {"retired": [], "retained": [], "unrecorded": 0, "absent": [], "unread": []}
    with FileLock(
        store / "install.lock",
        timeout=seconds("lock"),
        fallback_to_soft=False,
        preserve_lock_file=True,
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
                state, reason = _consumer_reading(consumer, installation)
                if state == "released":
                    record.unlink(missing_ok=True)
                else:
                    kept.append((consumer, state, reason))
                    needed = True
            if not needed:
                references = in_use() if references is None else references
                needed = any(path.is_relative_to(installation) for path in references)
            if needed:
                retained.append(installation.as_posix())
                continue
            remove_generated_tree(installation)
            retired.append(installation.as_posix())
    return {"retired": retired, "retained": retained, "unrecorded": unrecorded, **_filed(kept)}


def _filed(kept: list[tuple[Path | None, str, str]]) -> dict[str, object]:
    """File each kept consumer under what its path said: absent, or unread with the reason."""
    absent = {path.as_posix() for path, state, _ in kept if path and state == "absent"}
    unread = {path.as_posix(): reason for path, _, reason in kept if path and reason}
    return {
        "absent": sorted(absent),
        "unread": [{"consumer": path, "reason": unread[path]} for path in sorted(unread)],
    }


type _ConsumerState = Literal["needs", "released", "unknown", "absent"]


def _consumer_state(consumer: Path | None, installation: Path) -> _ConsumerState:
    """Say whether a consumer needs the installation; a missing path is never released."""
    return _consumer_reading(consumer, installation)[0]


def _place(consumer: Path) -> str:
    """Say what stands at a consumer's path: `directory`, `absent`, or why it was not read."""
    try:
        # The host's own status is asked, so a path that cannot be looked at is unread on every
        # interpreter. A file left at the path does not say what stood there.
        if not stat.S_ISDIR(consumer.stat().st_mode):
            return "not_a_directory"
    except (FileNotFoundError, NotADirectoryError):
        # Gone, unless a link that names nothing stands there: it does not say it either.
        return "dangling_link" if consumer.is_symlink() else "absent"
    except (OSError, ValueError):
        # A directory that may not be searched, or a record whose path no host can be asked
        # about, such as one with a null character.
        return "unanswered"
    return "directory"


def _consumer_reading(consumer: Path | None, installation: Path) -> tuple[_ConsumerState, str]:
    """Return a consumer's state and, for an unknown one, the reason it was not read."""
    if consumer is None:
        return "unknown", ""
    place = _place(consumer)
    if place != "directory":
        return ("absent", "") if place == "absent" else ("unknown", place)
    try:
        # A held selection lock is a selection in progress, which may be about to name this
        # installation; its Timeout is an OSError, so the consumer's liveness stays unknown.
        # Taking a lock creates it, so a consumer without ETHOS state, which has no selectors and
        # no selection, is read without one.
        lock = runtime_selection_lock(consumer) if (consumer / "ethos").is_dir() else None
        with lock.acquire(blocking=False) if lock is not None else contextlib.nullcontext():
            named = [named_runtime(consumer, name) for name in ("CURRENT", "ROLLBACK")]
    except (OSError, UnicodeError, ValueError):
        return "unknown", "selection_unread"
    needs = any(path and path.is_relative_to(installation) for path in named)
    return ("needs" if needs else "released"), ""


def _index(value: str) -> bool:
    return is_hex(value, 16)


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
        store / "install.lock",
        timeout=seconds("lock"),
        fallback_to_soft=False,
        preserve_lock_file=True,
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


def path_absent(path: Path) -> bool | None:
    """Say whether nothing is at a path; None when the host does not answer.

    Only the host's own answer that no entry exists counts. A directory that may not be searched,
    or any other failure, leaves the answer unknown, alike on every supported interpreter.
    """
    try:
        os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return True
    except (OSError, ValueError):
        return None
    return False


def _directory(path: Path) -> bool:
    """Say whether a path is a directory and no link; an unseen place is none."""
    try:
        return stat.S_ISDIR(os.lstat(path).st_mode)
    except (OSError, ValueError):
        return False


def _store_there(store: Path) -> bool:
    """Say whether a store is a directory; one the host cannot look at refuses, not being absent."""
    try:
        os.lstat(store)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except (OSError, ValueError) as error:
        raise ValueError(str(error).strip() or type(error).__name__) from error
    return _directory(store)


def absent_consumers(
    store: Path, *, consumers: tuple[Path, ...], apply: bool, expected_plan: str | None = None
) -> dict[str, object]:
    """Plan, and on apply release, the consumer records whose repository path is absent.

    A record is planned only when the host answers that nothing is at its path, and none of an
    installation is planned while a scanned repository cannot say whether it names it. Apply
    checks the previewed plan first, records each scanned repository that names an installation,
    so a moved repository keeps what it selects, and unlinks exactly the planned records, each
    read absent again. It removes no installation: the cleanup that ends `hook install` retires
    one that no record needs. A failure in the middle is named in the report beside the records
    released before it, and so is each planned record that was not read absent again. A store
    that the host cannot look at is no absent store: it refuses, and nothing is planned.
    """
    if not _store_there(store):
        return _absent_report([], [])
    with FileLock(
        store / "install.lock",
        timeout=seconds("lock"),
        fallback_to_soft=False,
        preserve_lock_file=True,
    ):
        rows, kept = _absent_rows(store, consumers)
        report = _absent_report(rows, kept) | {"unread": _unread_records(store)}
        if apply:
            if expected_plan != report["plan_digest"]:
                message = "host_store_plan_changed"
                raise ValueError(message)
            report["released"], report["not_released"], failed = _release(rows)
            if failed:
                report["failed"] = failed
    return report


type _AbsentRow = tuple[Path, Path, Path, list[Path]]


def _release(rows: list[_AbsentRow]) -> tuple[list[str], list[dict[str, str]], str]:
    """Release each planned record read absent again; return those, the others and a failure."""
    released: list[str] = []
    skipped: list[dict[str, str]] = []
    try:
        for installation, record, consumer, named in rows:
            for common in named:
                record_consumer(installation, common)
            again = path_absent(consumer)
            if again:
                record.unlink(missing_ok=True)
                released.append(consumer.as_posix())
                continue
            reason = "unknown" if again is None else "present"
            row = {"installation": installation.as_posix(), "record": record.name}
            skipped.append(row | {"consumer": consumer.as_posix(), "reason": reason})
    except (OSError, ValueError, RuntimeError) as error:
        # The result is the only account of the records that were already released, so a failure
        # of any of these kinds ends the release as text, which names the failure's class.
        named = filter(None, (type(error).__name__, f"{error}".strip()))
        return released, skipped, ": ".join(named)
    return released, skipped, ""


def _absent_rows(store: Path, consumers: tuple[Path, ...]) -> tuple[list[_AbsentRow], list[Path]]:
    """Return a row for each absent record, and the installations whose records are all kept.

    A row holds the installation, the record, its consumer and the scanned repositories that
    name the installation; one scanned repository of unknown state keeps the installation's
    records out.
    """
    rows: list[_AbsentRow] = []
    kept: list[Path] = []
    for installation in sorted(store.iterdir()):
        absent = _absent_records(installation)
        if not absent:
            continue
        states = {common: _consumer_state(common, installation) for common in consumers}
        if "unknown" in states.values():
            kept.append(installation)
            continue
        named = [common for common, state in states.items() if state == "needs"]
        rows.extend((installation, record, consumer, named) for record, consumer in absent)
    return rows, kept


def _absent_records(installation: Path) -> list[tuple[Path, Path]]:
    """Return an installation's records whose consumer path the host answers is absent."""
    if not _index(installation.name) or not _directory(installation):
        return []
    return [
        (record, consumer)
        for record, consumer in (installation_consumers(installation) or {}).items()
        if consumer is not None and path_absent(consumer)
    ]


def _unread_records(store: Path) -> list[dict[str, str]]:
    """Name each record whose consumer path reads neither a directory nor absent, with why."""
    return [
        {"installation": installation.as_posix(), "record": record.name}
        | {"consumer": consumer.as_posix(), "reason": place}
        for installation in sorted(store.iterdir())
        if _index(installation.name) and _directory(installation)
        for record, consumer in (installation_consumers(installation) or {}).items()
        if consumer is not None and (place := _place(consumer)) not in {"directory", "absent"}
    ]


def _absent_report(rows: list[_AbsentRow], kept: list[Path]) -> dict[str, object]:
    sizes = {installation: _size(installation) for installation, *_row in rows}
    planned = [
        {
            "installation": installation.as_posix(),
            "record": record.name,
            "consumer": consumer.as_posix(),
            "named_by": [common.as_posix() for common in named],
        }
        for installation, record, consumer, named in rows
    ]
    return {
        "plan_digest": hashlib.sha256(json.dumps(planned, sort_keys=True).encode()).hexdigest(),
        "absent": [
            row | {"bytes": sizes[installation]}
            for row, (installation, *_rest) in zip(planned, rows, strict=True)
        ],
        "held_bytes": sum(sizes.values()),
        "kept": [{"installation": path.as_posix(), "reason": "uncertain"} for path in kept],
        "unread": [],
        "released": [],
        "not_released": [],
    }


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
