"""Deterministic subprocess doubles for coverage tests."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Callable


def completed(
    stdout: str = "", stderr: str = "", returncode: int = 0, *, command: str = "git"
) -> subprocess.CompletedProcess[str]:
    """Build a text-mode completed process with a stable synthetic command."""
    return subprocess.CompletedProcess([command], returncode, stdout, stderr)


def kill_after_marker(
    root: Path, script: str, args: tuple[str, ...], marker: Path, *, timeout: float = 45
) -> str:
    """Kill one owned child only after its real effect reaches an observable boundary."""
    script = (
        f"import sys; sys.path.insert(0, {str(Path(__file__).resolve().parents[2])!r})\n" + script
    )
    with (
        marker.with_suffix(".log").open("w+") as output,
        subprocess.Popen(
            [sys.executable, "-B", "-I", "-c", script, *args],
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=subprocess.STDOUT,
        ) as child,
    ):
        try:
            deadline = time.monotonic() + timeout
            while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            output.seek(0)
            assert marker.exists(), output.read()
            assert child.poll() is None
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
    assert child.returncode != 0
    return marker.read_text()


def pause_after_effect(
    owner: Any, name: str, marker: Path, *, matches: Callable[..., bool] = lambda *_: True
) -> None:
    """Inject ACK loss only after a successful real effect selected by the scenario."""
    native = getattr(owner, name)

    def paused(*args, **kwargs):
        result = native(*args, **kwargs)
        if matches(*args):
            assert getattr(result, "returncode", 0) == 0
            marker.write_text(result if isinstance(result, str) else "native-effect-completed")
            sys.stdin.read(1)
        return result

    setattr(owner, name, paused)
