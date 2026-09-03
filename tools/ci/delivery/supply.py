"""Lock-bound dependency supply consumed by package delivery acceptance."""

from __future__ import annotations

from pathlib import Path

from ethos.adapters.process import run_command
from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[3]
UV_CACHE = ROOT / "build/runtime/tool-cache/uv"
RUNTIME = ProjectRuntime.discover(ROOT)


def _run(*command: str) -> None:
    completed = run_command(ROOT, command, remove_env_prefixes=("GIT_",))
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        message = f"package_runtime_supply_failed:{' '.join(command)}\n{detail}"
        raise RuntimeError(message)


def install_into(python: Path, *, constraints: Path) -> None:
    """Install the frozen production closure into one acceptance environment."""
    constraints.parent.mkdir(parents=True, exist_ok=True)
    uv = RUNTIME.script("uv")
    _run(
        uv,
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--offline",
        "--cache-dir",
        str(UV_CACHE),
        "--output-file",
        str(constraints),
    )
    _run(
        uv,
        "pip",
        "install",
        "--offline",
        "--cache-dir",
        str(UV_CACHE),
        "--require-hashes",
        "--requirements",
        str(constraints),
        "--python",
        str(python),
    )
