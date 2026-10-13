"""Bind one public Nox run to its actual launch and retained native output."""

from __future__ import annotations

import hashlib
import json
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import nox

_ACTIVE: ContextVar[list[tuple[str, tuple[str, ...], str]] | None] = ContextVar(
    "native_quality_launch", default=None
)


def popen_request(arguments: tuple[object, ...]) -> tuple[str, tuple[str, ...], str] | None:
    """Return one textual Popen audit request, or None when any part is not text."""
    executable, argv, cwd, _environment = arguments
    if not isinstance(executable, str) or not isinstance(argv, (tuple, list)):
        return None
    if not all(isinstance(item, str) for item in argv):
        return None
    if cwd is not None and not isinstance(cwd, str):
        return None
    return executable, tuple(argv), str(Path(cwd or Path.cwd()).resolve())


def _audit(event: str, arguments: tuple[object, ...]) -> None:
    capture = _ACTIVE.get()
    if capture is not None and event == "subprocess.Popen":
        request = popen_request(arguments)
        if request is not None:
            capture.append(request)


sys.addaudithook(_audit)


def run_ruff(
    session: nox.Session,
    command: tuple[str, ...],
    *,
    runtime_output: Path,
    identity: str,
    configuration: Path,
) -> str | bool | None:
    """Add execution custody, not scheduling or authority, around one Session.run.

    Audit events observe the pre-spawn request under a trusted producer. They do
    not authenticate hostile process behavior or the runtime distribution bytes.
    Only explicit zero success is accepted; install-only produces no launch.
    Environment values are deliberately never retained.
    """
    runtime = json.loads(runtime_output.read_bytes())
    if not isinstance(runtime, dict):
        msg = "python_native_toolchain_unbound"
        raise TypeError(msg)
    captured: list[tuple[str, tuple[str, ...], str]] = []
    stdout = runtime_output.with_suffix(".stdout")
    stderr = runtime_output.with_suffix(".stderr")
    result: str | bool | None = None
    selected = configuration.resolve()
    digest = hashlib.sha256(selected.read_bytes()).hexdigest()
    token = _ACTIVE.set(captured)
    try:
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            result = session.run(
                *command,
                success_codes=(0,),
                stdout=out,
                stderr=err,
                external=True,
            )
        return result
    finally:
        _ACTIVE.reset(token)
        payload = runtime
        launch = captured[0] if len(captured) == 1 else ("", (), str(Path.cwd()))
        payload["ruff"] = {
            "session": identity,
            "executable": launch[0],
            "argv": list(launch[1]),
            "cwd": launch[2],
            "configuration": str(selected),
            "configuration_sha256": digest,
            "completed": result is True,
            "launches": len(captured),
            "stdout": stdout.read_text(encoding="utf-8") if stdout.exists() else "",
            "stderr": stderr.read_text(encoding="utf-8") if stderr.exists() else "",
        }
        runtime_output.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
