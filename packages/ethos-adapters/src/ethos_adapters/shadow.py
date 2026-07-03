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
        diff = _semantic_diff(command, external_json, embedded_json)
        accepted_differences = _accepted_semantic_differences(
            command,
            external_json,
            embedded_json,
        )
        command_label = "ethos " + " ".join(command)
        if _process_failed(external):
            required_gaps.append(f"external_command_failed:{' '.join(command)}")
        for gap in _list(embedded.get("required_gaps")):
            if str(gap) not in required_gaps:
                required_gaps.append(str(gap))
        if _process_failed(embedded):
            required_gaps.append(f"embedded_command_failed:{' '.join(command)}")
        if diff:
            required_gaps.append(f"shadow_diff:{' '.join(command)}")
        comparisons.append(
            {
                "command": command_label,
                "external": external,
                "embedded": embedded,
                "semantic_diff": diff,
                "accepted_summary": _accepted_summary(accepted_differences),
                "accepted_differences": accepted_differences,
            }
        )
    return {
        "ok": not required_gaps,
        "state": "matched" if not required_gaps else "different",
        "target": target.as_posix(),
        "required_gaps": required_gaps,
        "accepted_summary": _accepted_summary(
            difference
            for comparison in comparisons
            for difference in comparison["accepted_differences"]
        )
        | {
            "command_count": sum(
                1 for comparison in comparisons if comparison["accepted_differences"]
            )
        },
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
    target = target.resolve()
    backend = _embedded_backend(target, command)
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
    result = _run_json_command(
        embedded_command,
        cwd=target,
        timeout_seconds=timeout_seconds,
    )
    return {
        **result,
        "backend": {key: value for key, value in backend.items() if key != "argv"},
        "required_gaps": list(backend.get("required_gaps", [])),
    }


def _embedded_ethos_command(target: Path, command: tuple[str, ...]) -> list[str] | None:
    backend = _embedded_backend(target, command)
    argv = backend.get("argv")
    return argv if isinstance(argv, list) else None


def _embedded_backend(target: Path, command: tuple[str, ...]) -> dict[str, Any]:
    if _has_pixi_project(target):
        argv = ["pixi", "run", "ethos", *command, "--json"]
        return {
            "kind": "pixi",
            "command": " ".join(argv),
            "blocking": False,
            "required_gaps": [],
            "argv": argv,
        }
    if _has_uv_ethos_workspace(target):
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


def _has_pixi_project(target: Path) -> bool:
    if (target / "pixi.toml").exists():
        return True
    data = _pyproject_tool(target)
    return isinstance(data.get("pixi"), dict)


def _has_uv_ethos_workspace(target: Path) -> bool:
    tool = _pyproject_tool(target)
    uv = tool.get("uv")
    if not isinstance(uv, dict):
        return False
    workspace = uv.get("workspace")
    return isinstance(workspace, dict)


def _pyproject_tool(target: Path) -> dict[str, Any]:
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


def _process_failed(result: dict[str, Any]) -> bool:
    if result.get("exit_code") == 124:
        return True
    parsed = result.get("json")
    if not _is_ethos_verdict(parsed):
        return True
    exit_code = result.get("exit_code")
    return exit_code not in {0, 1}


def _is_ethos_verdict(payload: object) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("ok"), bool)
        and isinstance(payload.get("command"), str)
        and isinstance(payload.get("required_gaps"), list)
    )


def _semantic_diff(*args: Any) -> dict[str, Any]:
    command, external, embedded = _semantic_args(args)
    external_projection, embedded_projection, _accepted = _normalized_semantic_projections(
        command,
        external,
        embedded,
    )
    diff = {}
    for key in sorted(set(external_projection) | set(embedded_projection)):
        external_value = external_projection.get(key)
        embedded_value = embedded_projection.get(key)
        if embedded_value != external_value:
            diff[key] = {"external": external_value, "embedded": embedded_value}
    return diff


def _accepted_semantic_differences(*args: Any) -> list[dict[str, Any]]:
    command, external, embedded = _semantic_args(args)
    _external_projection, _embedded_projection, accepted = _normalized_semantic_projections(
        command,
        external,
        embedded,
    )
    return accepted


def _accepted_summary(differences: object) -> dict[str, Any]:
    items = list(differences) if not isinstance(differences, list) else differences
    kind_counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        if not kind:
            continue
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
    return {
        "total_count": sum(kind_counts.values()),
        "kind_counts": dict(sorted(kind_counts.items())),
    }


def _semantic_args(args: tuple[Any, ...]) -> tuple[tuple[str, ...], dict[str, Any], dict[str, Any]]:
    if len(args) == 3:
        command = tuple(str(item) for item in args[0])
        return command, args[1], args[2]
    if len(args) == 2:
        command_name = str(args[0].get("command") or args[1].get("command") or "")
        return tuple(command_name.split()), args[0], args[1]
    raise TypeError("_semantic_diff expects external/embedded or command/external/embedded")


def _normalized_semantic_projections(
    command: tuple[str, ...],
    external: dict[str, Any],
    embedded: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    external_projection = _semantic_projection(command, external)
    embedded_projection = _semantic_projection(command, embedded)
    accepted: list[dict[str, Any]] = []
    embedded_gaps = _gap_list(embedded_projection.get("required_gaps"))
    external_gaps = _gap_list(external_projection.get("required_gaps"))
    if not embedded_gaps:
        external_gaps, repository_audit_gaps = _without_product_repository_audit_gaps(
            external,
            external_gaps,
        )
        if repository_audit_gaps:
            accepted.append(
                _accepted_difference(
                    "external_product_repository_audit_gap",
                    command=external_projection.get("command"),
                    gaps=repository_audit_gaps,
                )
            )
        external_gaps, route_gaps = _without_changed_route_noop_gaps(
            external,
            embedded,
            external_gaps,
        )
        if route_gaps:
            accepted.append(
                _accepted_difference(
                    "changed_route_noop",
                    command=external_projection.get("command"),
                    gaps=route_gaps,
                )
            )
        report_gaps = _report_parity_evidence_refresh_bootstrap_gaps(
            external,
            embedded,
            external_projection,
            embedded_projection,
        )
        if report_gaps:
            accepted.append(
                _accepted_difference(
                    "report_parity_evidence_refresh_bootstrap",
                    command=external_projection.get("command"),
                    gaps=report_gaps,
                )
            )
    external_projection["required_gaps"] = sorted(external_gaps)
    if accepted and not external_gaps and not embedded_gaps:
        external_projection["ok"] = True
        external_projection["state"] = _ready_state_for_command(
            external_projection.get("command")
        )
        _mark_projection_ready(external_projection)
    return external_projection, embedded_projection, accepted


def _accepted_difference(kind: str, *, command: object, gaps: list[str]) -> dict[str, Any]:
    if kind == "external_product_repository_audit_gap":
        scope = "external_product_repository_audit"
        reason = "external product repository audit gap is not an embedded adopter parity gap"
    elif kind == "changed_route_noop":
        scope = "changed_scope_route"
        reason = "changed-scope route has no changed paths to route"
    elif kind == "report_parity_evidence_refresh_bootstrap":
        scope = "parity_evidence_refresh"
        reason = "report parity freshness is being refreshed by the current shadow run"
    else:
        scope = "unknown"
        reason = "unclassified accepted difference"
    return {
        "kind": kind,
        "classification": "accepted",
        "scope": scope,
        "commands": [_command_label(command)],
        "gaps": sorted(set(gaps)),
        "reason": reason,
    }


def _command_label(command: object) -> str:
    text = str(command or "").strip()
    return text if text.startswith("ethos ") else f"ethos {text}".strip()


def _semantic_projection(command: tuple[str, ...], payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    command_name = _command_name(command, payload, summary)
    state = _semantic_state(payload, summary=summary, command=command_name)
    projection: dict[str, Any] = {
        "ok": payload.get("ok"),
        "command": command_name,
        "state": state,
        "required_gaps": sorted(_gap_list(payload.get("required_gaps"))),
    }
    command_root = command[0] if command else command_name.split()[0] if command_name else ""
    if command_root == "status":
        changed_paths = _first_list(data.get("changed_paths"), payload.get("changed_paths"))
        dirty = _first_present(
            data.get("dirty"),
            summary.get("dirty"),
            payload.get("dirty"),
        )
        if dirty is None and state == "ready":
            dirty = False
        projection.update(
            {
                "role": payload.get("role") or summary.get("role") or data.get("role"),
                "dirty": dirty,
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


def _mark_projection_ready(projection: dict[str, Any]) -> None:
    command = projection.get("command")
    if command == "prove":
        projection["proof_ready"] = True
    elif command == "report":
        projection["blocking_gap_count"] = 0
    elif command == "assistants doctor":
        projection["assistant_ready"] = True
    elif command == "playbooks route":
        projection["route_ready"] = True
    elif command in {"land", "publish"}:
        projection["readiness"] = True


def _command_name(
    command: tuple[str, ...],
    payload: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    explicit = payload.get("command") or summary.get("command")
    if explicit:
        return str(explicit)
    if command[:2] == ("assistants", "doctor"):
        return "assistants doctor"
    if command[:2] == ("playbooks", "route"):
        return "playbooks route"
    if command[:2] == ("quality", "command-surface"):
        return "quality command-surface"
    return command[0] if command else ""


def _semantic_state(
    payload: dict[str, Any],
    *,
    summary: dict[str, Any],
    command: object,
) -> object:
    state = payload.get("state")
    if isinstance(state, str):
        if (
            payload.get("ok") is True
            and command == "prove"
            and state == "ready"
            and not _gap_list(payload.get("required_gaps"))
        ):
            return "proven"
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
    if command == "quality command-surface":
        return "clean"
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


def _without_product_repository_audit_gaps(
    payload: dict[str, Any],
    gaps: list[str],
) -> tuple[list[str], list[str]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    repository_audit = (
        data.get("repository_audit")
        if isinstance(data.get("repository_audit"), dict)
        else {}
    )
    audit_gaps = {
        gap
        for gap in _gap_list(repository_audit.get("required_gaps"))
        if _is_product_repository_audit_gap(gap)
    }
    if not audit_gaps:
        return gaps, []
    filtered = [gap for gap in gaps if gap not in audit_gaps]
    removed = [gap for gap in gaps if gap in audit_gaps]
    return filtered, removed


_PRODUCT_REPOSITORY_AUDIT_GAP_PREFIXES = (
    "docs/",
    "schemas/",
    "packages/",
    "distribution_adapter_missing:",
    "adoption_scaffold_missing:",
    "openspec_family_missing:",
    "claims_",
    "claim_",
    "schema_",
    "openspec_",
    "command_",
)


def _is_product_repository_audit_gap(gap: str) -> bool:
    return gap.startswith(_PRODUCT_REPOSITORY_AUDIT_GAP_PREFIXES)


def _without_changed_route_noop_gaps(
    external: dict[str, Any],
    embedded: dict[str, Any],
    gaps: list[str],
) -> tuple[list[str], list[str]]:
    if not _is_changed_route_noop(external, embedded, gaps):
        return gaps, []
    filtered = [gap for gap in gaps if not _is_changed_route_noop_gap(gap)]
    removed = [gap for gap in gaps if _is_changed_route_noop_gap(gap)]
    return filtered, removed


def _is_changed_route_noop_gap(gap: str) -> bool:
    return gap in {
        "skill_missing_id",
        "playbook_route_missing:changed-scope",
    } or gap.startswith("playbook_activation_unsupported_version:")


def _is_changed_route_noop(
    external: dict[str, Any],
    embedded: dict[str, Any],
    gaps: list[str],
) -> bool:
    external_data = external.get("data") if isinstance(external.get("data"), dict) else {}
    embedded_summary = (
        embedded.get("summary") if isinstance(embedded.get("summary"), dict) else {}
    )
    return (
        (external.get("command") or external_data.get("command")) == "playbooks route"
        and external_data.get("subject") == "changed-scope"
        and embedded_summary.get("changed_requested") is True
        and embedded_summary.get("changed_path_count") == 0
        and bool(gaps)
        and all(_is_changed_route_noop_gap(gap) for gap in gaps)
    )


def _report_parity_evidence_refresh_bootstrap_gaps(
    external: dict[str, Any],
    embedded: dict[str, Any],
    external_projection: dict[str, Any],
    embedded_projection: dict[str, Any],
) -> list[str]:
    external_summary = (
        external.get("summary") if isinstance(external.get("summary"), dict) else {}
    )
    parity_pending_count = external_summary.get("parity_pending_count")
    governance_gap_count = external_summary.get("governance_gap_count")
    if not isinstance(parity_pending_count, int) or parity_pending_count <= 0:
        return []
    if governance_gap_count not in (None, 0):
        return []
    if external_projection.get("command") != "report":
        return []
    if embedded_projection.get("command") != "report":
        return []
    if external_projection.get("required_gaps") or embedded_projection.get("required_gaps"):
        return []
    if external_projection.get("ok") is not False or embedded_projection.get("ok") is not True:
        return []
    if external_projection.get("state") != "gapped":
        return []
    if embedded_projection.get("state") != "ready":
        return []
    return [f"parity_pending_count:{parity_pending_count}"]


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
