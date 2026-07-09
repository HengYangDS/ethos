from __future__ import annotations

import json
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
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
            start_new_session=True,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "timeout",
            "json": {},
        }
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": parse_json_from_stdout(completed.stdout),
    }


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
