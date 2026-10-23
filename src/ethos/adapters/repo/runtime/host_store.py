"""The user-owned host root of installed runtime supply and the state derived from it."""

from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
from pathlib import Path

from platformdirs import user_data_path

_CONSUMERS = "consumers"


def host_store_root() -> Path | None:
    """Return ETHOS's host root, or None when an explicit XDG_DATA_HOME is not absolute."""
    if declared := os.environ.get("XDG_DATA_HOME"):
        root = Path(declared)
        return root.resolve() / "ethos" if root.is_absolute() else None
    return user_data_path("ethos", appauthor=False).resolve()


def record_consumer(installation: Path, consumer: Path) -> None:
    """Record one repository common directory that selects or holds this installation."""
    common = consumer.resolve()
    records = installation / _CONSUMERS
    record = records / hashlib.sha256(os.fsencode(common)).hexdigest()[:32]
    content = common.as_posix() + "\n"
    with contextlib.suppress(OSError):
        if record.read_text(encoding="utf-8") == content:
            return
    records.mkdir(mode=0o700, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=records, prefix=".", suffix=".tmp", delete=False, encoding="utf-8"
    ) as stream:
        stream.write(content)
    Path(stream.name).replace(record)


def installation_consumers(installation: Path) -> dict[Path, Path | None] | None:
    """Map each consumer record to its common directory; None marks an unreadable record.

    An installation pinned before consumers were recorded returns None: its users are unknown.
    """
    records = installation / _CONSUMERS
    if not records.is_dir() or records.is_symlink():
        return None
    consumers: dict[Path, Path | None] = {}
    for record in sorted(records.iterdir()):
        if record.name.startswith("."):
            continue
        try:
            text = record.read_text(encoding="utf-8") if not record.is_symlink() else ""
        except (OSError, UnicodeError):
            text = ""
        common = Path(text.removesuffix("\n"))
        consumers[record] = common if text.endswith("\n") and common.is_absolute() else None
    return consumers
