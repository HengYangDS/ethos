"""The user-owned host root of installed runtime supply and the state derived from it."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_path


def host_store_root() -> Path | None:
    """Return ETHOS's host root, or None when an explicit XDG_DATA_HOME is not absolute."""
    if declared := os.environ.get("XDG_DATA_HOME"):
        root = Path(declared)
        return root.resolve() / "ethos" if root.is_absolute() else None
    return user_data_path("ethos", appauthor=False).resolve()
