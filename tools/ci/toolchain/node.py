"""Package-local Node and npm coordinates for wheel construction."""

from __future__ import annotations

import os
from importlib import import_module
from pathlib import Path


def node_runtime(
    *,
    package_root: Path | None = None,
    platform_name: str | None = None,
) -> tuple[Path, Path]:
    """Return validated Node and npm paths from the locked package supply."""
    root = package_root or Path(import_module("nodejs_wheel").__file__).resolve().parent
    platform = platform_name or os.name
    node = root / "node.exe" if platform == "nt" else root / "bin/node"
    npm_cli = root / "lib/node_modules/npm/bin/npm-cli.js"
    if not node.is_file() or (platform != "nt" and not os.access(node, os.X_OK)):
        message = f"package-local Node executable is unavailable: {node}"
        raise RuntimeError(message)
    if not npm_cli.is_file():
        message = f"package-local npm CLI is unavailable: {npm_cli}"
        raise RuntimeError(message)
    return node, npm_cli
