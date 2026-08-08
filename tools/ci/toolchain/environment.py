"""Typed access to the single locked project execution closure."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectRuntime:
    """Resolve project-owned executables without ambient PATH fallback."""

    root: Path
    python: Path
    scripts: Path

    @classmethod
    def discover(cls, root: Path) -> ProjectRuntime:
        """Bind the current interpreter and its console-script directory."""
        python = Path(sys.executable).absolute()
        return cls(root.resolve(), python, python.parent)

    def script(self, name: str) -> str:
        """Return one console script from the bound project environment."""
        suffix = ".exe" if os.name == "nt" else ""
        executable = self.scripts / f"{name}{suffix}"
        if not executable.is_file():
            message = f"project executable is unavailable: {executable}"
            raise RuntimeError(message)
        return str(executable)
