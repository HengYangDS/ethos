"""Typed access to the single locked project execution closure."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from importlib import import_module
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
        executable = self.scripts / name
        if not executable.is_file():
            message = f"project executable is unavailable: {executable}"
            raise RuntimeError(message)
        return str(executable)

    def node_executable(self) -> Path:
        """Resolve Node only for a consumer that requires its executable."""
        owner = import_module("ethos.adapters.repo.runtime.materialization.input_resolution")
        return owner.resolve_node_runtime().executable

    def npm_command(self) -> tuple[str, str]:
        """Bind npm's native CLI to the same locked Node distribution."""
        owner = import_module("ethos.adapters.repo.runtime.materialization.input_resolution")
        runtime = owner.resolve_node_runtime()
        return str(runtime.executable), str(runtime.npm)

    def node_package_supply(self) -> Path:
        """Validate current locked Node supply at the capability boundary."""
        owner = import_module("ethos.adapters.repo.runtime.materialization.node_package_supply")
        return owner.resolve_node_package_supply(self.root)
