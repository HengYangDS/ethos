from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

OFFICIAL_NPX_PACKAGE = "@fission-ai/openspec@1.6.0"
# The hosted bootstrap exposes the official OpenSpec CLI through an npx shim.
# Cold package resolution can exceed the usual command budget, so lifecycle
# checks must allow that bounded startup before declaring the repository gapped.
OPENSPEC_COMMAND_TIMEOUT_SECONDS = 60


def current_branch(root: Path) -> str:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return "" if completed.returncode else completed.stdout.strip()


def openspec_base_command() -> tuple[str, ...] | None:
    explicit = os.environ.get("ETHOS_OPENSPEC_BIN", "").strip()
    if explicit:
        return (explicit,)
    return (
        cached_official_cli_entry()
        or (("openspec",) if shutil.which("openspec") else None)
        or (("npx", "--yes", OFFICIAL_NPX_PACKAGE) if shutil.which("npx") else None)
    )


def cached_official_cli_entry() -> tuple[str, str] | None:
    node = shutil.which("node") or "node"
    cache_root = Path(os.environ.get("ETHOS_NPX_CACHE_DIR", "") or Path.home() / ".npm" / "_npx")
    if not cache_root.exists():
        return None
    candidates: list[tuple[tuple[int, ...], Path]] = []
    for package_json in cache_root.glob("*/node_modules/@fission-ai/openspec/package.json"):
        try:
            payload = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        bin_value = payload.get("bin")
        entry = (
            str(bin_value.get("openspec") or "")
            if isinstance(bin_value, dict)
            else bin_value
            if isinstance(bin_value, str)
            else ""
        )
        if not entry:
            continue
        entry_path = (package_json.parent / entry).resolve()
        if not entry_path.exists():
            continue
        version = version_key(str(payload.get("version") or "0"))
        candidates.append((version, entry_path))
    if not candidates:
        return None
    _version, entry_path = max(candidates, key=lambda item: item[0])
    return (node, entry_path.as_posix())


def version_key(value: str) -> tuple[int, ...]:
    return tuple(
        int("".join(character for character in part if character.isdigit()) or 0)
        for part in value.split(".")
    )


def run_json(
    root: Path,
    base_command: tuple[str, ...],
    args: tuple[str, ...],
) -> dict[str, Any]:
    command = (*base_command, *args)
    timeout_seconds = OPENSPEC_COMMAND_TIMEOUT_SECONDS
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        if not stderr:
            stderr = f"openspec command timed out after {timeout_seconds} seconds"
        return {
            "command": list(command),
            "exit_code": 124,
            "stdout": stdout,
            "stderr": stderr,
            "json": {},
            "parse_error": "openspec_command_timeout",
        }
    payload: dict[str, Any] = {}
    parse_error = ""
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)
        else:
            if isinstance(parsed, dict):
                payload = parsed
            else:
                parse_error = "openspec_json_not_object"
    return {
        "command": list(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": payload,
        "parse_error": parse_error,
    }
