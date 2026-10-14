"""Bind one public Nox run to its actual launch and retained native output."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence
    from typing import TextIO

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


def _observe(
    launch: Callable[[TextIO, TextIO], bool],
    runtime: dict[str, object],
    *,
    runtime_output: Path,
    identity: str,
    configuration: Path,
) -> None:
    """Retain the launches one call makes, with its output, beside the interpreter.

    Audit events observe the pre-spawn request under a trusted producer. They do
    not authenticate hostile process behavior or the runtime distribution bytes.
    Environment values are deliberately never retained.
    """
    captured: list[tuple[str, tuple[str, ...], str]] = []
    stdout = runtime_output.with_suffix(".stdout")
    stderr = runtime_output.with_suffix(".stderr")
    selected = configuration.resolve()
    digest = hashlib.sha256(selected.read_bytes()).hexdigest()
    completed = False
    token = _ACTIVE.set(captured)
    try:
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            completed = launch(out, err)
    finally:
        _ACTIVE.reset(token)
        observed = captured[0] if len(captured) == 1 else ("", (), str(Path.cwd()))
        runtime["ruff"] = {
            "session": identity,
            "executable": observed[0],
            "argv": list(observed[1]),
            "cwd": observed[2],
            "configuration": str(selected),
            "configuration_sha256": digest,
            "completed": completed,
            "launches": len(captured),
            "stdout": stdout.read_text(encoding="utf-8") if stdout.exists() else "",
            "stderr": stderr.read_text(encoding="utf-8") if stderr.exists() else "",
        }
        runtime_output.write_text(json.dumps(runtime, sort_keys=True) + "\n", encoding="utf-8")


def run_ruff(
    session: nox.Session,
    command: tuple[str, ...],
    *,
    runtime_output: Path,
    identity: str,
    configuration: Path,
) -> str | bool | None:
    """Add execution custody, not scheduling or authority, around one Session.run.

    The Nox parent calls this with the child's recorded interpreter already at
    ``runtime_output``. Only explicit zero success is accepted; install-only
    produces no launch.
    """
    runtime = json.loads(runtime_output.read_bytes())
    if not isinstance(runtime, dict):
        msg = "python_native_toolchain_unbound"
        raise TypeError(msg)
    result: str | bool | None = None

    def launch(out: TextIO, err: TextIO) -> bool:
        nonlocal result
        result = session.run(*command, success_codes=(0,), stdout=out, stderr=err, external=True)
        return result is True

    _observe(
        launch,
        runtime,
        runtime_output=runtime_output,
        identity=identity,
        configuration=configuration,
    )
    return result


def _run_child(
    command: tuple[str, ...], *, runtime_output: Path, identity: str, configuration: Path
) -> int:
    """Launch one exact Ruff argv from the interpreter that owns its environment.

    This child records its own interpreter, so no detached runtime print precedes
    the launch and the Nox parent needs no ETHOS. The exit code is Ruff's own.
    """
    code = 1

    def launch(out: TextIO, err: TextIO) -> bool:
        nonlocal code
        code = subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, check=False
        ).returncode
        return code == 0

    runtime: dict[str, object] = {
        "executable": sys.executable,
        "version": list(sys.version_info[:3]),
        "prefix": sys.prefix,
    }
    _observe(
        launch,
        runtime,
        runtime_output=runtime_output,
        identity=identity,
        configuration=configuration,
    )
    return code


def main(arguments: Sequence[str] | None = None) -> int:
    """Expose the child launch as one installed operation taking the exact Ruff argv."""
    selected = list(sys.argv[1:] if arguments is None else arguments)
    boundary = selected.index("--") if "--" in selected else len(selected)
    parser = argparse.ArgumentParser(prog="python -m ethos.domain.quality.nox", allow_abbrev=False)
    run = parser.add_subparsers(dest="operation", required=True).add_parser(
        "run", allow_abbrev=False
    )
    run.add_argument("--runtime-output", type=Path, required=True)
    run.add_argument("--session", required=True)
    run.add_argument("--configuration", type=Path, required=True)
    options = parser.parse_args(selected[:boundary])
    command = tuple(selected[boundary + 1 :])
    if not command:
        parser.error("run requires -- followed by the exact Ruff argv")
    try:
        return _run_child(
            command,
            runtime_output=options.runtime_output,
            identity=options.session,
            configuration=options.configuration,
        )
    except OSError as error:
        sys.stderr.write(f"{parser.prog}: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
