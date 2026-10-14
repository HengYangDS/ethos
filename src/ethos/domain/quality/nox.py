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

from ethos.domain.quality.observer import runtime_identity

if TYPE_CHECKING:
    from collections.abc import Sequence

_ACTIVE: ContextVar[tuple[tuple[str, ...], list[tuple[str, tuple[str, ...], str]]] | None] = (
    ContextVar("native_quality_launch", default=None)
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
    active = _ACTIVE.get()
    if active is None or event != "subprocess.Popen":
        return
    original, capture = active
    executable, argv, cwd, _environment = arguments
    if isinstance(argv, str):
        if argv != subprocess.list2cmdline(original):
            return
        argv = original
        executable = original[0] if executable is None else executable
    if executable != original[0] or argv not in (original, list(original)):
        return
    if cwd is not None and not isinstance(cwd, str):
        return
    capture.append((original[0], original, str(Path(cwd or Path.cwd()).resolve())))


sys.addaudithook(_audit)


def run_ruff(
    command: tuple[str, ...],
    *,
    runtime_output: Path,
    identity: str,
    configuration: Path,
) -> int:
    """Observe one exact Ruff argv in this installed child, without scheduling.

    Audit events observe the pre-spawn request under a trusted producer. They do
    not authenticate hostile process behavior. Loaded PEP 610 provenance binds
    the supplied wheel separately. Only a completed zero exit is accepted.
    Environment values are deliberately never retained.
    """
    runtime = runtime_identity()
    captured: list[tuple[str, tuple[str, ...], str]] = []
    stdout = runtime_output.with_suffix(".stdout")
    stderr = runtime_output.with_suffix(".stderr")
    result = None
    selected = configuration.resolve()
    digest = hashlib.sha256(selected.read_bytes()).hexdigest()
    _write(runtime_output, runtime, command, identity, selected, digest, captured, result)
    token = _ACTIVE.set((command, captured))
    try:
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                check=False,
            ).returncode
        return result
    finally:
        _ACTIVE.reset(token)
        _write(runtime_output, runtime, command, identity, selected, digest, captured, result)


def _write(
    output: Path,
    runtime: dict[str, object],
    command: tuple[str, ...],
    identity: str,
    configuration: Path,
    digest: str,
    captured: list[tuple[str, tuple[str, ...], str]],
    result: int | None,
) -> None:
    launch = captured[0] if len(captured) == 1 else ("", command, str(Path.cwd()))
    stdout, stderr = output.with_suffix(".stdout"), output.with_suffix(".stderr")
    runtime["ruff"] = {
        "session": identity,
        "executable": launch[0],
        "argv": list(launch[1]),
        "cwd": launch[2],
        "configuration": str(configuration),
        "configuration_sha256": digest,
        "completed": result == 0,
        "launches": len(captured),
        "stdout": stdout.read_text(encoding="utf-8") if stdout.exists() else "",
        "stderr": stderr.read_text(encoding="utf-8") if stderr.exists() else "",
    }
    output.write_text(json.dumps(runtime, sort_keys=True) + "\n", encoding="utf-8")


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
        return run_ruff(
            command,
            runtime_output=options.runtime_output,
            identity=options.session,
            configuration=options.configuration,
        )
    except (OSError, ValueError) as error:
        sys.stderr.write(f"{parser.prog}: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
