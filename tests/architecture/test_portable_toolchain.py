from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    from pathlib import Path


def test_project_runtime_fails_closed_without_path_fallback(tmp_path: Path) -> None:
    scripts = tmp_path / ("Scripts" if os.name == "nt" else "bin")
    scripts.mkdir()
    runtime = ProjectRuntime(tmp_path, tmp_path / "python", scripts)
    with pytest.raises(RuntimeError, match="project executable is unavailable"):
        runtime.script("uv")


def test_project_runtime_resolves_the_bound_platform_executable(tmp_path: Path) -> None:
    scripts = tmp_path / ("Scripts" if os.name == "nt" else "bin")
    scripts.mkdir()
    executable = scripts / ("ruff.exe" if os.name == "nt" else "ruff")
    executable.write_text("", encoding="utf-8")
    assert ProjectRuntime(tmp_path, tmp_path / "python", scripts).script("ruff") == str(executable)
