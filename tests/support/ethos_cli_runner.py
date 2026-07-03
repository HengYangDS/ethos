from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PYTHONPATH = os.pathsep.join(
    str(ROOT / package / "src")
    for package in (
        "packages/ethos",
        "packages/ethos-adapters",
        "packages/ethos-assistants",
        "packages/ethos-contracts",
        "packages/ethos-core",
        "packages/ethos-quality",
        "packages/ethos-repository",
        "packages/ethos-test",
    )
)


def run_ethos(*args: str, cwd: Path | None = None) -> dict[str, Any]:
    completed = run_ethos_raw(*args, cwd=cwd)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


def run_ethos_blocked(*args: str, cwd: Path | None = None) -> dict[str, Any]:
    """Run an admission command expected to BLOCK: assert non-zero exit, return JSON.

    Admission commands (hook admit, lane prewrite) enforce their verdict via a
    non-zero process exit on a blocked verdict, so a git hook / CI / MCP host can
    refuse the write. This helper proves that contract: exit code must be 1.
    """
    completed = run_ethos_raw(*args, cwd=cwd)
    if completed.returncode == 0:
        msg = f"expected a blocked (non-zero exit) verdict, got exit 0: {completed.stdout}"
        raise AssertionError(msg)
    return json.loads(completed.stdout)


def run_ethos_raw(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    if "--help" in args or "--version" in args:
        return _run_subprocess(*args, cwd=cwd)
    if "--json" not in args:
        return _run_subprocess(*args, cwd=cwd)
    return _run_inprocess(*args, cwd=cwd)


def _run_inprocess(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    from ethos.cli import app

    previous_cwd = Path.cwd()
    stdout = StringIO()
    stderr = StringIO()
    returncode = 0
    try:
        os.chdir(cwd or ROOT)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                app(list(args), exit_on_error=False)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                returncode = code
    except BaseException as exc:  # pragma: no cover - exercised through failing tests.
        returncode = 1
        stderr.write(f"{type(exc).__name__}: {exc}")
    finally:
        os.chdir(previous_cwd)
    return subprocess.CompletedProcess(
        [sys.executable, "-m", "ethos.cli", *args],
        returncode,
        stdout.getvalue(),
        stderr.getvalue(),
    )


def _run_subprocess(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH
    return subprocess.run(
        [sys.executable, "-m", "ethos.cli", *args],
        cwd=cwd or ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
