"""Small deterministic subprocess doubles shared by coverage tests."""

from __future__ import annotations

import subprocess


def completed(
    stdout: str = "", stderr: str = "", returncode: int = 0, *, command: str = "git"
) -> subprocess.CompletedProcess[str]:
    """Build a text-mode completed process with a stable synthetic command."""
    return subprocess.CompletedProcess([command], returncode, stdout, stderr)
