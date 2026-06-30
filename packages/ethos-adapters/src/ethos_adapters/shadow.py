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
    ("assistants", "doctor"),
    ("playbooks", "route", "--changed"),
    ("land",),
    ("publish",),
)

ROOT_OPTION_COMMANDS = {
    ("status",),
    ("plan", "--changed"),
    ("prove",),
    ("report",),
    ("playbooks", "route", "--changed"),
    ("land",),
    ("publish",),
}

SEMANTIC_DIMENSIONS = [
    "branch_role",
    "mutation_allowed",
    "changed_path_classification",
    "required_gates",
    "required_gaps",
    "assistant_boundary",
    "evidence_freshness",
    "land_readiness",
    "publish_readiness",
    "blocking_vs_advisory",
]


def run_shadow_parity(target: Path, *, timeout_seconds: int = 30) -> dict[str, Any]:
    target = target.resolve()
    comparisons = []
    required_gaps: list[str] = []
    for command in READ_ONLY_COMMANDS:
        external = _run_external(target, command, timeout_seconds=timeout_seconds)
        embedded = _run_embedded(target, command, timeout_seconds=timeout_seconds)
        external_json = external.get("json", {})
        embedded_json = embedded.get("json", {})
        diff = _semantic_diff(external_json, embedded_json)
        accepted_differences = _accepted_semantic_differences(external_json, embedded_json)
        if external["exit_code"] != 0:
            required_gaps.append(f"external_command_failed:{' '.join(command)}")
        if embedded["exit_code"] != 0:
            required_gaps.append(f"embedded_command_failed:{' '.join(command)}")
        if diff:
            required_gaps.append(f"shadow_diff:{' '.join(command)}")
        comparisons.append(
            {
                "command": "ethos " + " ".join(command),
                "external": external,
                "embedded": embedded,
                "semantic_diff": diff,
                "accepted_differences": accepted_differences,
            }
        )
    return {
        "ok": not required_gaps,
        "state": "matched" if not required_gaps else "different",
        "target": target.as_posix(),
        "required_gaps": required_gaps,
        "comparisons": comparisons,
        "execution_packages": [
            _execution_package(gap=gap, target=target, comparisons=comparisons)
            for gap in required_gaps
        ],
    }


def _execution_package(
    *,
    gap: str,
    target: Path,
    comparisons: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "gap": gap,
        "state": "failed",
        "target": target.as_posix(),
        "commands": [str(comparison["command"]) for comparison in comparisons],
        "semantic_dimensions": list(SEMANTIC_DIMENSIONS),
        "blocking": True,
        "next_action": "inspect shadow parity comparison output",
    }


def _run_external(
    target: Path,
    command: tuple[str, ...],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    if command not in ROOT_OPTION_COMMANDS:
        return _run_json_command(
            [sys.executable, "-m", "ethos.cli", *command, "--json"],
            cwd=target.resolve(),
            timeout_seconds=timeout_seconds,
        )
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
    if not _has_pixi_project(target):
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": "pixi project missing",
            "json": {},
        }
    return _run_json_command(
        ["pixi", "run", "ethos", *command, "--json"],
        cwd=target,
        timeout_seconds=timeout_seconds,
    )


def _has_pixi_project(target: Path) -> bool:
    if (target / "pixi.toml").exists():
        return True
    pyproject = target / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return False
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return False
    return isinstance(tool.get("pixi"), dict)


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


def _semantic_diff(external: dict[str, Any], embedded: dict[str, Any]) -> dict[str, Any]:
    external_projection, embedded_projection, _accepted = _normalized_semantic_projections(
        external,
        embedded,
    )
    diff = {}
    for key, value in external_projection.items():
        if embedded_projection.get(key) != value:
            diff[key] = {"external": value, "embedded": embedded_projection.get(key)}
    return diff


def _accepted_semantic_differences(
    external: dict[str, Any],
    embedded: dict[str, Any],
) -> list[dict[str, Any]]:
    _external_projection, _embedded_projection, accepted = _normalized_semantic_projections(
        external,
        embedded,
    )
    return accepted


def _normalized_semantic_projections(
    external: dict[str, Any],
    embedded: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    external_projection = _semantic_projection(external)
    embedded_projection = _semantic_projection(embedded)
    accepted: list[dict[str, Any]] = []
    embedded_gaps = _gap_list(embedded_projection.get("required_gaps"))
    external_gaps = _gap_list(external_projection.get("required_gaps"))
    if not embedded_gaps:
        external_gaps, self_audit_gaps = _without_product_self_audit_gaps(
            external,
            external_gaps,
        )
        if self_audit_gaps:
            accepted.append(
                {
                    "kind": "external_product_self_audit_gap",
                    "gaps": sorted(set(self_audit_gaps)),
                }
            )
        external_gaps, route_gaps = _without_legacy_changed_route_noop_gaps(
            external,
            embedded,
            external_gaps,
        )
        if route_gaps:
            accepted.append(
                {
                    "kind": "legacy_changed_route_noop",
                    "gaps": sorted(set(route_gaps)),
                }
            )
    external_projection["required_gaps"] = external_gaps
    if accepted and not external_gaps and not embedded_gaps:
        external_projection["ok"] = True
        external_projection["state"] = _ready_state_for_command(external_projection.get("command"))
    return external_projection, embedded_projection, accepted


def _semantic_projection(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    command = payload.get("command") or summary.get("command")
    return {
        "ok": payload.get("ok"),
        "command": command,
        "state": _semantic_state(payload, summary=summary, command=command),
        "role": _semantic_role(payload, summary=summary, data=data, command=command),
        "required_gaps": _gap_list(payload.get("required_gaps")),
    }


def _semantic_role(
    payload: dict[str, Any],
    *,
    summary: dict[str, Any],
    data: dict[str, Any],
    command: object,
) -> object:
    if command != "status":
        return None
    return payload.get("role") or summary.get("role") or data.get("role")


def _semantic_state(
    payload: dict[str, Any],
    *,
    summary: dict[str, Any],
    command: object,
) -> object:
    state = payload.get("state")
    if isinstance(state, str):
        return state
    if payload.get("ok") is not True:
        return state
    if command == "status":
        dirty = payload.get("dirty", summary.get("dirty", False))
        return "dirty" if dirty else "ready"
    ready_state = _ready_state_for_command(command)
    if ready_state is not None:
        return ready_state
    return state


def _ready_state_for_command(command: object) -> str | None:
    if command == "plan":
        return "planned"
    if command == "assistants doctor":
        return "ready"
    if command == "prove":
        return "proven"
    if command == "report":
        return "ready"
    if command == "playbooks route":
        return "routed"
    if command == "land":
        return "ready_to_land"
    if command == "publish":
        return "ready_to_publish"
    return None


def _gap_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _without_product_self_audit_gaps(
    payload: dict[str, Any],
    gaps: list[str],
) -> tuple[list[str], list[str]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    self_audit = data.get("self_audit") if isinstance(data.get("self_audit"), dict) else {}
    audit_gaps = set(_gap_list(self_audit.get("required_gaps")))
    if not audit_gaps:
        return gaps, []
    filtered = [gap for gap in gaps if gap not in audit_gaps]
    removed = [gap for gap in gaps if gap in audit_gaps]
    return filtered, removed


def _without_legacy_changed_route_noop_gaps(
    external: dict[str, Any],
    embedded: dict[str, Any],
    gaps: list[str],
) -> tuple[list[str], list[str]]:
    if not _is_legacy_changed_route_noop(external, embedded, gaps):
        return gaps, []
    route_gap_codes = {"skill_missing_id", "playbook_route_missing:changed-scope"}
    filtered = [gap for gap in gaps if gap not in route_gap_codes]
    removed = [gap for gap in gaps if gap in route_gap_codes]
    return filtered, removed


def _is_legacy_changed_route_noop(
    external: dict[str, Any],
    embedded: dict[str, Any],
    gaps: list[str],
) -> bool:
    external_data = external.get("data") if isinstance(external.get("data"), dict) else {}
    embedded_summary = (
        embedded.get("summary") if isinstance(embedded.get("summary"), dict) else {}
    )
    route_gap_codes = {"skill_missing_id", "playbook_route_missing:changed-scope"}
    return (
        (external.get("command") or external_data.get("command")) == "playbooks route"
        and external_data.get("subject") == "changed-scope"
        and embedded_summary.get("changed_requested") is True
        and embedded_summary.get("changed_path_count") == 0
        and bool(gaps)
        and set(gaps).issubset(route_gap_codes)
    )
