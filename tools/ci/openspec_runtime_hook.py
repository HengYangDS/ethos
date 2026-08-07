"""Hatch hook for the lock-bound, production-only OpenSpec runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class OpenSpecRuntimeHook(BuildHookInterface):
    """Compile the npm production closure into wheel build data."""

    PLUGIN_NAME = "openspec-runtime"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if version == "editable":
            return
        root = Path(self.root)
        supply = root / "build/runtime/work/openspec-supply"
        supply.mkdir(parents=True, exist_ok=True)
        for relative in ("package.json", "package-lock.json"):
            shutil.copy2(root / relative, supply / relative)
        node = os.environ.get("ETHOS_BUILD_NODE", "")
        npm_cli = os.environ.get("ETHOS_BUILD_NPM_CLI", "")
        if not node or not npm_cli:
            message = "Nox must bind the package-local Node/npm runtime"
            raise RuntimeError(message)
        subprocess.run(
            (
                node,
                npm_cli,
                "ci",
                "--omit=dev",
                "--ignore-scripts",
                "--offline",
                "--workspaces=false",
                "--no-audit",
                "--no-fund",
            ),
            cwd=supply,
            check=True,
        )
        build_data["force_include"][str(supply / "node_modules")] = (
            "ethos/data/openspec-runtime/node_modules"
        )


def get_build_hook() -> type[OpenSpecRuntimeHook]:
    """Expose the single custom hook class to Hatchling."""
    return OpenSpecRuntimeHook
