"""Resolve native tool supply from exact mise inputs without executing project hooks."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Mapping


MISE_CONFIG = ".config/mise/config.toml"
MISE_LOCK = ".config/mise/mise.lock"


def mise_executable(root: Path) -> Path:
    """Resolve native mise without installing or changing the operator's tool owner."""
    installed = shutil.which("mise")
    candidate = Path(installed) if installed else root / "build/runtime/tool-cache/mise/bin/mise"
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        message = "mise_unavailable:run tools/ci/scripts/bootstrap-python.sh"
        raise ValueError(message)
    return candidate


def run_mise(
    root: Path,
    arguments: tuple[str, ...],
    *,
    files: Mapping[str, str] | None = None,
    timeout: float = 15,
) -> subprocess.CompletedProcess[str]:
    """Run native mise over exact inputs with no project hooks or ambient config."""
    materials = (
        {path: (root / path).read_text(encoding="utf-8") for path in (MISE_CONFIG, MISE_LOCK)}
        if files is None
        else files
    )
    with TemporaryDirectory(prefix="ethos-mise-") as directory:
        isolated = Path(directory)
        for path in (MISE_CONFIG, MISE_LOCK):
            target = isolated / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(materials[path], encoding="utf-8")
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in {"MISE_DATA_DIR", "MISE_CACHE_DIR", "MISE_INSTALLS_DIR"}
        } | {
            "MISE_SAFE": "1",
            "MISE_LOCKED": "1",
            "MISE_NOT_FOUND_SYSTEM_FALLBACK": "0",
            "MISE_YES": "0",
            "MISE_GLOBAL_CONFIG_FILE": str(isolated / "absent-global.toml"),
            "MISE_SYSTEM_CONFIG_DIR": str(isolated / "absent-system"),
        }
        return run_command(
            isolated,
            (str(mise_executable(root)), *arguments),
            timeout=timeout,
            remove_env_prefixes=("MISE_",),
            env=environment,
        )


def locked_tool(root: Path, name: str, files: Mapping[str, str] | None = None) -> Path:
    """Resolve installed locked supply; never install or use an ambient tool fallback."""
    result = run_mise(root, ("which", name), files=files)
    if result.returncode or result.stderr:
        message = f"mise_supply_unavailable:{name}:{result.stderr.strip()}"
        raise ValueError(message)
    executable = Path(result.stdout.strip())
    if not executable.is_absolute() or not executable.is_file():
        message = f"mise_executable_unavailable:{name}"
        raise ValueError(message)
    return executable
