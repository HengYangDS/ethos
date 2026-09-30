"""Bind native coverage to checkout bytes or exact installed wheel contents."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.python.coverage as native_coverage
from ethos.adapters.gates.verification import NativePythonReports
from tests.support.governed_repository import committed_source_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "fault", ["checkout", "installed", "namespace", "installed-drift", "wheel-drift"]
)
def test_native_coverage_preserves_installed_source_identity(tmp_path: Path, fault: str) -> None:
    """Neither a basename nor current package metadata proves source correspondence."""
    files = {
        "src/sample/__init__.py": "",
        "src/sample/answer.py": "def answer():\n    return 42\nanswer()\n",
        "pyproject.toml": (
            '[build-system]\nrequires = ["hatchling"]\n'
            'build-backend = "hatchling.build"\n\n'
            '[project]\nname = "sample"\nversion = "1.0"\n\n'
            '[tool.hatch.build.targets.wheel]\npackages = ["src/sample"]\n'
        ),
    }
    root = committed_source_repo(tmp_path / "source", files)
    output = tmp_path / "reports"
    output.mkdir()
    source = tuple(path for path in files if path.endswith(".py"))
    projection = native_coverage.artifact_sources(root, (sys.executable,))
    inputs = NativePythonReports(
        root=output,
        source_digests=tuple(
            (path, hashlib.sha256((root / path).read_bytes()).hexdigest()) for path in source
        ),
        python_prefix=(sys.executable,),
        packaged_sources=projection,
    )
    target = root / "src/sample/answer.py"
    if fault != "checkout":
        wheel = _install_native_wheel(root, tmp_path / "installed", tmp_path / "wheels")
        target = tmp_path / "installed/sample/answer.py"
        if fault == "namespace":
            target = tmp_path / "installed/other/answer.py"
            target.parent.mkdir()
            target.write_bytes((root / "src/sample/answer.py").read_bytes())
        elif fault == "installed-drift":
            target.write_text("def answer():\n    return 43\nanswer()\n")
        elif fault == "wheel-drift":
            wheel.write_bytes(b"altered artifact")
    environment = {
        **os.environ,
        "COVERAGE_FILE": str(output / ".coverage"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    subprocess.run(
        [sys.executable, "-B", "-m", "coverage", "run", "--branch", "--parallel-mode", str(target)],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    if fault in {"namespace", "installed-drift", "wheel-drift"}:
        with pytest.raises(ValueError, match=r"python_native_(?:source|artifact)_"):
            native_coverage.observe(root, inputs, source)
        return

    result = native_coverage.observe(root, inputs, source)

    assert result["covered"] > 0
    assert set(result["selected_paths"]) == set(source)
    assert result["non_applicable_paths"] == ["src/sample/__init__.py"]
    assert bool(result["artifacts"]) is (fault == "installed")


def _install_native_wheel(root: Path, target: Path, wheels: Path) -> Path:
    """Build and install the native artifact, without an editable source shortcut."""
    subprocess.run(
        [sys.executable, "-B", "-m", "hatchling", "build", "-t", "wheel", "-d", str(wheels)],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    wheel = next(wheels.glob("*.whl"))
    subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "uv",
            "pip",
            "install",
            "--offline",
            "--no-cache",
            "--no-config",
            "--no-deps",
            "--target",
            str(target),
            str(wheel),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return wheel


def test_native_coverage_does_not_relabel_suppressed_statements_as_empty(tmp_path: Path) -> None:
    """A source pragma cannot erase a production subject's execution obligation."""
    root = committed_source_repo(
        tmp_path / "source",
        {"observed.py": "answer = 42\n", "unused.py": "unused = 0  # pragma: no cover\n"},
    )
    output = tmp_path / "reports"
    output.mkdir()
    source = ("observed.py", "unused.py")
    inputs = NativePythonReports(
        root=output,
        source_digests=tuple(
            (path, hashlib.sha256((root / path).read_bytes()).hexdigest()) for path in source
        ),
        python_prefix=(sys.executable,),
    )
    subprocess.run(
        (
            sys.executable,
            "-B",
            "-m",
            "coverage",
            "run",
            "--branch",
            "--parallel-mode",
            "observed.py",
        ),
        cwd=root,
        env={**os.environ, "COVERAGE_FILE": str(output / ".coverage")},
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    with pytest.raises(ValueError, match=r"python_native_source_unexercised:unused.py"):
        native_coverage.observe(root, inputs, source)
