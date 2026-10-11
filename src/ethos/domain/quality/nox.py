"""Bind one public Nox run to its actual launch and retained native output."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from contextvars import ContextVar
from pathlib import Path

from ethos.domain.quality.observer import runtime_identity

_ACTIVE: ContextVar[tuple[tuple[str, ...], list[tuple[str, tuple[str, ...], str]]] | None] = (
    ContextVar("native_quality_launch", default=None)
)


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


def main() -> int:
    """Expose custody as an installed child operation with explicit original argv."""
    parser = argparse.ArgumentParser(description=__doc__)
    run = parser.add_subparsers(dest="operation", required=True).add_parser("run")
    run.add_argument("--runtime-output", type=Path, required=True)
    run.add_argument("--session", required=True)
    run.add_argument("--configuration", type=Path, required=True)
    run.add_argument("command", nargs=argparse.REMAINDER)
    options = parser.parse_args()
    if not options.command or options.command[0] != "--" or len(options.command) < 2:
        parser.error("run requires -- followed by the exact Ruff argv")
    try:
        return run_ruff(
            tuple(options.command[1:]),
            runtime_output=options.runtime_output,
            identity=options.session,
            configuration=options.configuration,
        )
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
