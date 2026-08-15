"""Materialize isolated executable fixtures for architecture tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def isolated_path(tmp_path: Path, executables: Mapping[str, str]) -> dict[str, str]:
    """Materialize executable fixtures on a minimal cross-platform PATH."""
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    for name, body in executables.items():
        path = fake_bin / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join((str(fake_bin), "/bin", "/usr/bin"))
    return env
