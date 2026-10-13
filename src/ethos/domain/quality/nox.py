"""Observe one exact Ruff launch from the Nox session child that owns its environment."""

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
    from collections.abc import Sequence

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
    command: tuple[str, ...], *, runtime_output: Path, identity: str, configuration: Path
) -> int:
    """Launch one exact Ruff argv and record it beside this interpreter's identity.

    The session child records its own interpreter, so no detached runtime print
    precedes the launch and the Nox parent needs no ETHOS. Audit events observe
    the pre-spawn request under a trusted producer. They do not authenticate
    hostile process behavior or the runtime distribution bytes. Environment
    values are deliberately never retained. The exit code is Ruff's own.
    """
    captured: list[tuple[str, tuple[str, ...], str]] = []
    stdout = runtime_output.with_suffix(".stdout")
    stderr = runtime_output.with_suffix(".stderr")
    selected = configuration.resolve()
    digest = hashlib.sha256(selected.read_bytes()).hexdigest()
    code: int | None = None
    token = _ACTIVE.set(captured)
    try:
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            code = subprocess.run(
                command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, check=False
            ).returncode
        return code
    finally:
        _ACTIVE.reset(token)
        observed = captured[0] if len(captured) == 1 else ("", (), str(Path.cwd()))
        record = {
            "executable": sys.executable,
            "version": list(sys.version_info[:3]),
            "prefix": sys.prefix,
            "ruff": {
                "session": identity,
                "executable": observed[0],
                "argv": list(observed[1]),
                "cwd": observed[2],
                "configuration": str(selected),
                "configuration_sha256": digest,
                "completed": code == 0,
                "launches": len(captured),
                "stdout": stdout.read_text(encoding="utf-8") if stdout.exists() else "",
                "stderr": stderr.read_text(encoding="utf-8") if stderr.exists() else "",
            },
        }
        runtime_output.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")


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
    except OSError as error:
        sys.stderr.write(f"{parser.prog}: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
