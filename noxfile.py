"""Repository-owned sessions executed inside the single uv-locked `.venv`."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from typing import cast

import nox

ROOT = Path(__file__).resolve().parent
RUFF_CACHE = ROOT / "build/runtime/tool-cache/ruff"

nox.options.default_venv_backend = "none"
nox.options.error_on_external_run = True
nox.options.sessions = ["lint"]


def _tracked_python_paths() -> tuple[str, ...]:
    completed = subprocess.run(
        ("git", "ls-files", "-z", "*.py", "*.pyi"),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = tuple(path for path in completed.stdout.split("\0") if path)
    if not paths:
        msg = "no tracked Python files found for Ruff"
        raise RuntimeError(msg)
    return paths


def _ruff_ratchet(session: nox.Session, paths: tuple[str, ...]) -> None:
    policy = tomllib.loads((ROOT / ".config/checks/ruff/ratchet.toml").read_text(encoding="utf-8"))
    baselines = {str(rule): int(value) for rule, value in policy["ignored_rule_baseline"].items()}
    completed = cast(
        "str",
        session.run(
            "ruff",
            "check",
            "--config",
            "ruff.toml",
            *paths,
            "--select",
            ",".join(sorted(baselines)),
            "--exit-zero",
            "--statistics",
            silent=True,
            env={"RUFF_CACHE_DIR": str(RUFF_CACHE)},
        ),
    )
    counts = dict.fromkeys(baselines, 0)
    for count, rule in re.findall(r"^\s*(\d+)\s+([A-Z]+\d+)\b", completed, re.MULTILINE):
        if rule in counts:
            counts[rule] = int(count)
    drift = [
        f"{rule}: {counts[rule]} != {baselines[rule]}"
        for rule in sorted(baselines)
        if counts[rule] != baselines[rule]
    ]
    if drift:
        session.error("Ruff ratchet drift:\n" + "\n".join(drift))


@nox.session(python=False)
def lint(session: nox.Session) -> None:
    """Run repository-wide Ruff lint, format, and exact debt ratchet."""
    paths = _tracked_python_paths()
    RUFF_CACHE.mkdir(parents=True, exist_ok=True)
    common = ("--cache-dir", str(RUFF_CACHE), "--config", "ruff.toml")
    session.run("ruff", "check", *common, *paths)
    session.run("ruff", "format", *common, "--check", *paths)
    _ruff_ratchet(session, paths)
