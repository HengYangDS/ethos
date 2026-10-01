"""Deterministic subprocess doubles for coverage tests."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from contextlib import ExitStack
from contextlib import contextmanager
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


@contextmanager
def ready_descendant(monkeypatch, before_communication):
    """Observe a real child handshake before fault injection; close every probe handle."""
    communicate = subprocess.Popen.communicate
    connection = None
    with ExitStack() as resources:
        listener = resources.enter_context(socket.create_server(("127.0.0.1", 0)))
        listener.settimeout(10)
        child = (
            f"import socket; s=socket.create_connection({listener.getsockname()!r},timeout=10); "
            "s.settimeout(None); s.sendall(b'R'); s.recv(1)"
        )

        def after_ready(process, *args, **kwargs):
            nonlocal connection
            if connection is None:
                connection = resources.enter_context(listener.accept()[0])
                connection.settimeout(2)
                assert connection.recv(1) == b"R"
                before_communication(process, kwargs)
            return communicate(process, *args, **kwargs)

        monkeypatch.setattr(subprocess.Popen, "communicate", after_ready)
        yield child, lambda: connection is not None and connection.recv(1) == b""


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
            staging = marker.with_suffix(".pending")
            staging.write_text(result if isinstance(result, str) else "native-effect-completed")
            staging.replace(marker)
            sys.stdin.read(1)
        return result

    setattr(owner, name, paused)
