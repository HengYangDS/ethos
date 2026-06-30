from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

READ_ONLY_COMMANDS = (
    ("status",),
    ("plan", "--changed"),
    ("prove",),
    ("report",),
    ("quality", "command-surface"),
    ("assistants", "doctor"),
    ("playbooks", "route", "--changed"),
    ("land",),
    ("publish",),
)


def run_shadow_parity(target: Path, *, timeout_seconds: int = 30) -> dict[str, Any]:
    target = target.resolve()
    comparisons = []
    required_gaps: list[str] = []
    for command in READ_ONLY_COMMANDS:
        external = _run_external(target, command, timeout_seconds=timeout_seconds)
        embedded = _run_embedded(target, command, timeout_seconds=timeout_seconds)
        diff = _semantic_diff(command, external.get("json", {}), embedded.get("json", {}))
        if _process_failed(external):
            required_gaps.append(f"external_command_failed:{' '.join(command)}")
        if _process_failed(embedded):
            required_gaps.append(f"embedded_command_failed:{' '.join(command)}")
        if diff:
            required_gaps.append(f"shadow_diff:{' '.join(command)}")
        comparisons.append(
            {
                "command": "ethos " + " ".join(command),
                "external": external,
                "embedded": embedded,
                "semantic_diff": diff,
            }
        )
    return {
        "ok": not required_gaps,
        "state": "matched" if not required_gaps else "different",
        "target": target.as_posix(),
        "required_gaps": required_gaps,
        "comparisons": comparisons,
    }


def _run_external(
    target: Path,
    command: tuple[str, ...],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    return _run_json_command(
        [sys.executable, "-m", "ethos.cli", *command, "--root", target.as_posix(), "--json"],
        cwd=Path.cwd(),
        timeout_seconds=timeout_seconds,
    )


def _run_embedded(
    target: Path,
    command: tuple[str, ...],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    if not _has_pixi_ethos_task(target):
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": "pixi ethos task missing",
            "json": {},
        }
    return _run_json_command(
        ["pixi", "run", "ethos", *command, "--json"],
        cwd=target,
        timeout_seconds=timeout_seconds,
    )


def _run_json_command(
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
        "json": _parse_json_from_stdout(completed.stdout),
    }


def _parse_json_from_stdout(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start < 0 or end < start:
        return {}
    try:
        parsed = json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _has_pixi_ethos_task(target: Path) -> bool:
    if (target / "pixi.toml").exists():
        return True
    pyproject = target / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return False
    tool = payload.get("tool")
    pixi = tool.get("pixi") if isinstance(tool, dict) else None
    if not isinstance(pixi, dict):
        return False
    tasks = pixi.get("tasks")
    return isinstance(tasks, dict) and "ethos" in tasks


def _process_failed(result: dict[str, Any]) -> bool:
    if result.get("exit_code") == 124:
        return True
    parsed = result.get("json")
    return not isinstance(parsed, dict) or not parsed


def _semantic_diff(
    command: tuple[str, ...],
    external: dict[str, Any],
    embedded: dict[str, Any],
) -> dict[str, Any]:
    external_projection = _semantic_projection(command, external)
    embedded_projection = _semantic_projection(command, embedded)
    diff = {}
    for key in sorted(set(external_projection) | set(embedded_projection)):
        external_value = external_projection.get(key)
        embedded_value = embedded_projection.get(key)
        if embedded_value != external_value:
            diff[key] = {"external": external_value, "embedded": embedded_value}
    return diff


def _semantic_projection(command: tuple[str, ...], payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    projection: dict[str, Any] = {
        "ok": payload.get("ok"),
        "command": payload.get("command"),
        "required_gaps": sorted(str(gap) for gap in payload.get("required_gaps", [])),
    }
    command_root = command[0]
    if command_root == "status":
        changed_paths = _first_list(data.get("changed_paths"), payload.get("changed_paths"))
        projection.update(
            {
                "role": payload.get("role") or summary.get("role") or data.get("role"),
                "dirty": _first_present(
                    data.get("dirty"),
                    summary.get("dirty"),
                    payload.get("dirty"),
                ),
                "changed_path_count": len(changed_paths),
            }
        )
    elif command_root == "plan":
        required_gates = _first_list(data.get("required_gates"), payload.get("required_gates"))
        projection.update(
            {
                "changed_path_count": len(
                    _first_list(data.get("changed_paths"), payload.get("changed_paths"))
                ),
                "matched_rule_ids": sorted(
                    str(rule.get("id"))
                    for rule in _first_list(data.get("matched_rules"), payload.get("matched_rules"))
                    if isinstance(rule, dict)
                ),
                "required_gate_ids": _gate_ids(required_gates),
            }
        )
    elif command_root == "prove":
        projection.update(
            {"proof_ready": bool(payload.get("ok")) and not payload.get("required_gaps")}
        )
    elif command_root == "report":
        projection.update(
            {
                "blocking_gap_count": summary.get("blocking_gap_count")
                if summary.get("blocking_gap_count") is not None
                else len(payload.get("required_gaps", [])),
            }
        )
    elif command_root == "quality":
        projection.update(
            {
                "retired_violation_count": summary.get("retired_violation_count")
                or len(_list(data.get("retired_public_root_mentions"))),
            }
        )
    elif command_root == "assistants":
        projection.update({"assistant_ready": bool(payload.get("ok"))})
    elif command_root == "playbooks":
        projection.update({"route_ready": bool(payload.get("ok"))})
    elif command_root in {"land", "publish"}:
        remote_push = data.get("remote_push") or summary.get("remote_push")
        projection.update(
            {
                "readiness": bool(payload.get("ok")) and not payload.get("required_gaps"),
                "remote_push": remote_push,
            }
        )
    return projection


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_list(*values: Any) -> list[Any]:
    for value in values:
        if isinstance(value, list):
            return value
    return []


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _gate_ids(value: Any) -> list[str]:
    return sorted(str(gate.get("id")) for gate in _list(value) if isinstance(gate, dict))
