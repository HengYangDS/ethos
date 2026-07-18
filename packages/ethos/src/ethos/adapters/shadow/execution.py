from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT_OPTION_COMMANDS = {
    ("status",),
    ("plan", "--changed"),
    ("prove",),
    ("report",),
    ("quality", "command-surface"),
    ("playbooks", "route", "--changed"),
    ("land",),
    ("publish",),
}
_TERMINATION_GRACE_SECONDS = 1


def run_external(
    target: Path,
    command: tuple[str, ...],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    if command not in ROOT_OPTION_COMMANDS:
        return run_json_command(
            [sys.executable, "-m", "ethos.cli", *command, "--json"],
            cwd=target.resolve(),
            timeout_seconds=timeout_seconds,
        )
    return run_json_command(
        [
            sys.executable,
            "-m",
            "ethos.cli",
            *command,
            "--root",
            target.as_posix(),
            "--json",
        ],
        cwd=Path.cwd(),
        timeout_seconds=timeout_seconds,
    )


def run_embedded(
    target: Path,
    command: tuple[str, ...],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    target = target.resolve()
    backend = embedded_backend(target, command)
    embedded_command = backend.get("argv")
    if not isinstance(embedded_command, list):
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": "embedded ETHOS backend missing",
            "json": {},
            "backend": {key: value for key, value in backend.items() if key != "argv"},
            "required_gaps": list(backend.get("required_gaps", [])),
        }
    result = run_json_command(
        embedded_command,
        cwd=target,
        timeout_seconds=timeout_seconds,
    )
    return {
        **result,
        "backend": {key: value for key, value in backend.items() if key != "argv"},
        "required_gaps": list(backend.get("required_gaps", [])),
    }


def embedded_ethos_command(target: Path, command: tuple[str, ...]) -> list[str] | None:
    backend = embedded_backend(target, command)
    argv = backend.get("argv")
    return argv if isinstance(argv, list) else None


def embedded_backend(target: Path, command: tuple[str, ...]) -> dict[str, Any]:
    if has_pixi_project(target):
        argv = ["pixi", "run", "ethos", *command, "--json"]
        return {
            "kind": "pixi",
            "command": " ".join(argv),
            "blocking": False,
            "required_gaps": [],
            "argv": argv,
        }
    if has_uv_ethos_workspace(target):
        argv = ["uv", "run", "--package", "ethos", "ethos", *command, "--json"]
        return {
            "kind": "uv-workspace",
            "command": " ".join(argv),
            "blocking": False,
            "required_gaps": [],
            "argv": argv,
        }
    return {
        "kind": "missing",
        "command": "",
        "blocking": True,
        "required_gaps": ["embedded_backend_missing"],
        "argv": None,
    }


def has_pixi_project(target: Path) -> bool:
    if (target / "pixi.toml").exists():
        return True
    data = pyproject_tool(target)
    return isinstance(data.get("pixi"), dict)


def has_uv_ethos_workspace(target: Path) -> bool:
    tool = pyproject_tool(target)
    uv = tool.get("uv")
    if not isinstance(uv, dict):
        return False
    workspace = uv.get("workspace")
    return isinstance(workspace, dict)


def pyproject_tool(target: Path) -> dict[str, Any]:
    pyproject = target / "pyproject.toml"
    if not pyproject.exists():
        return {}
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return {}
    return tool


def run_json_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process.pid)
        try:
            stdout, stderr = process.communicate(timeout=_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _kill_process_group(process.pid)
            try:
                stdout, stderr = process.communicate(timeout=_TERMINATION_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                stdout, stderr = _text(exc.stdout), _text(exc.stderr)
        return {
            "exit_code": 124,
            "stdout": _text(stdout) or _text(exc.stdout),
            "stderr": _text(stderr) or _text(exc.stderr) or "timeout",
            "json": {},
        }
    return {
        "exit_code": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "json": parse_json_from_stdout(stdout),
    }


def _terminate_process_group(pid: int) -> None:
    """Terminate the session created for a timed-out shadow command.

    Shadow execution deliberately creates a session so an external runner cannot
    inherit this process group's signals.  ``subprocess.run`` only terminates its
    direct child on timeout, however; package runners such as ``uv`` can leave
    their command child behind holding workspace locks.  Kill the created process
    group as one bounded unit before returning timeout evidence.
    """
    if pid <= 0:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        return


def _kill_process_group(pid: int) -> None:
    """Force-stop a shadow session that ignored the bounded TERM grace period."""
    if pid <= 0:
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except PermissionError:
        return


def _text(value: str | bytes | None) -> str:
    """Normalize timeout streams before their shadow result becomes JSON evidence."""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""


def parse_json_from_stdout(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        parsed = json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def process_failed(result: dict[str, Any]) -> bool:
    if result.get("exit_code") == 124:
        return True
    parsed = result.get("json")
    if not is_ethos_verdict(parsed):
        return True
    exit_code = result.get("exit_code")
    return exit_code not in {0, 1}


def is_ethos_verdict(payload: object) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("ok"), bool)
        and isinstance(payload.get("command"), str)
        and isinstance(payload.get("required_gaps"), list)
    )
