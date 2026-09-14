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


def write_reference_source(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def declare_reference_package(root: Path, *, entry_point: str = "") -> None:
    """Declare package ownership, including Cyclopts only for command surfaces."""
    metadata = '[project]\nname = "example"\nversion = "1"\n'
    if entry_point:
        metadata += (
            f'dependencies = ["cyclopts"]\n\n[project.scripts]\nethos = "{entry_point}:main"\n'
        )
    write_reference_source(root, "pyproject.toml", metadata)
