"""Run and inventory one selected native repository starter."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.filesystem import is_junction


def compose_starter(
    candidate: Path, starter: str, purpose: str
) -> tuple[dict[str, str], dict[str, str], str, str]:
    """Let the selected native owner generate optional domain content."""
    foundation, gap, detail = _candidate_outputs(candidate)
    if gap or starter == "foundation":
        return foundation, {}, gap, detail
    generator_gap, detail = _run_python_library_generator(candidate, purpose)
    if generator_gap:
        return {}, {}, generator_gap, detail
    outputs, gap, detail = _candidate_outputs(candidate)
    if gap:
        return outputs, {}, gap, detail
    if any(outputs.get(path) != digest for path, digest in foundation.items()):
        return {}, {}, "formation_starter_overwrote_foundation", ""
    if "pyproject.toml" not in outputs or not any(
        path.startswith("src/") and path.endswith("/__init__.py") for path in outputs
    ):
        return {}, {}, "formation_starter_output_incomplete", "Python library files missing"
    generated = {path: digest for path, digest in outputs.items() if path not in foundation}
    return outputs, generated, "", ""


def _run_python_library_generator(candidate: Path, purpose: str) -> tuple[str, str]:
    """Run only the locked native uv initializer with fixed inert flags."""
    command = (
        sys.executable,
        "-B",
        "-I",
        "-m",
        "uv",
        "init",
        "--lib",
        "--name",
        candidate.name,
        "--description",
        purpose,
        "--vcs",
        "none",
        "--no-readme",
        "--no-pin-python",
        "--no-workspace",
        "--author-from",
        "none",
        "--offline",
        "--no-python-downloads",
        "--no-config",
        "--python",
        "3.12",
        ".",
    )
    try:
        result = run_command(
            candidate,
            command,
            timeout=30,
            env={"UV_NO_CACHE": "1"},
            remove_env=("VIRTUAL_ENV",),
            remove_env_prefixes=("UV_",),
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return "formation_starter_generation_failed", str(error)
    if result.returncode:
        return "formation_starter_generation_failed", (
            result.stderr.strip() or "starter_generator_exit_nonzero"
        )
    return "", ""


def _candidate_outputs(candidate: Path) -> tuple[dict[str, str], str, str]:
    """Inventory only exclusive regular files below an unlinked candidate tree."""
    files: list[Path] = []
    pending = [candidate]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                path = Path(entry.path)
                info = path.lstat()
                if is_junction(path):
                    return {}, "formation_starter_output_unsafe", str(path)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    files.append(path)
                else:
                    return {}, "formation_starter_output_unsafe", str(path)
    outputs = {
        path.relative_to(candidate).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    return dict(sorted(outputs.items())), "", ""
