from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterable

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
    "external_false_negative",
]


def run_shadow_parity(
    target: Path,
    *,
    timeout_seconds: int = 30,
    product_root: Path | None = None,
) -> dict[str, Any]:
    target = target.resolve()
    product_root = (product_root or Path.cwd()).resolve()
    comparisons = []
    required_gaps: list[str] = []
    for command in READ_ONLY_COMMANDS:
        external = _run_external(target, command, timeout_seconds=timeout_seconds)
        embedded = _run_embedded(target, command, timeout_seconds=timeout_seconds)
        external_json = external.get("json", {})
        embedded_json = embedded.get("json", {})
        diff = _semantic_diff(command, external_json, embedded_json)
        false_negative_gaps = _false_negative_gaps(command, external_json, embedded_json)
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
        if false_negative_gaps:
            required_gaps.append(f"shadow_false_negative:{' '.join(command)}")
        if diff:
            required_gaps.append(f"shadow_diff:{' '.join(command)}")
        comparisons.append(
            {
                "command": command_label,
                "external": external,
                "embedded": embedded,
                "semantic_diff": diff,
                "false_negative_gaps": false_negative_gaps,
                "accepted_summary": _accepted_summary(accepted_differences),
                "accepted_differences": accepted_differences,
            }
        )
    identity = _identity_envelope(
        target,
        READ_ONLY_COMMANDS,
        product_root=product_root,
        comparisons=comparisons,
    )
    return {
        "ok": not required_gaps,
        "state": "matched" if not required_gaps else "different",
        "target": target.as_posix(),
        "identity": identity,
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
        "false_negative_count": sum(
            len(comparison["false_negative_gaps"]) for comparison in comparisons
        ),
        "comparisons": comparisons,
        "execution_packages": [
            _execution_package(gap=gap, target=target, comparisons=comparisons)
            for gap in required_gaps
        ],
    }


def _identity_envelope(
    target: Path,
    commands: Iterable[tuple[str, ...]],
    *,
    product_root: Path,
    comparisons: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    target = target.resolve()
    product_root = product_root.resolve()
    return {
        "target_root": target.as_posix(),
        "target_head": _git_head(target),
        "product_head": _git_head(product_root),
        "changed_paths": _changed_paths(target),
        "commands": [_command_label_from_tuple(command) for command in commands],
        "external_commands": [_external_command_label(target, command) for command in commands],
        "embedded_commands": _embedded_command_labels(target, commands, comparisons),
        "evidence_inputs": _evidence_inputs(target),
    }


def _command_label_from_tuple(command: tuple[str, ...]) -> str:
    return "ethos " + " ".join(command) + " --json"


def _external_command_label(target: Path, command: tuple[str, ...]) -> str:
    if command not in ROOT_OPTION_COMMANDS:
        return " ".join([sys.executable, "-m", "ethos.cli", *command, "--json"])
    return " ".join(
        [
            sys.executable,
            "-m",
            "ethos.cli",
            *command,
            "--root",
            target.resolve().as_posix(),
            "--json",
        ]
    )


def _embedded_command_labels(
    target: Path,
    commands: Iterable[tuple[str, ...]],
    comparisons: list[dict[str, Any]] | None,
) -> list[str]:
    labels: list[str] = []
    if comparisons is not None:
        for comparison in comparisons:
            embedded = comparison.get("embedded") if isinstance(comparison, dict) else None
            backend = embedded.get("backend") if isinstance(embedded, dict) else None
            command = backend.get("command") if isinstance(backend, dict) else None
            if isinstance(command, str) and command:
                labels.append(command)
        if labels:
            return labels
    for command in commands:
        backend = _embedded_backend(target, command)
        label = backend.get("command")
        if isinstance(label, str) and label:
            labels.append(label)
    return labels


def _git_head(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _changed_paths(root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "-uall"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if not line:
            continue
        raw = line[3:] if len(line) > 3 else line
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        if raw:
            paths.append(raw.strip())
    return sorted(dict.fromkeys(paths))


def _evidence_inputs(target: Path) -> list[dict[str, Any]]:
    candidates = _evidence_root_candidates(target)
    return [item for item in (_evidence_input(target, path) for path in candidates) if item]


def _evidence_root_candidates(target: Path) -> list[str]:
    profile_path = target / ".ethos" / "profile.toml"
    candidates = [
        ".ethos/profile.toml",
        "rules",
        "claims",
        "evidence/claims",
        "openspec",
        "docs/evidence",
        "evidence",
    ]
    if profile_path.exists():
        try:
            profile = tomllib.loads(profile_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            profile = {}
        roots = profile.get("roots") if isinstance(profile, dict) else None
        if isinstance(roots, dict):
            for key in ("rules", "claims", "openspec", "durable_evidence", "docs"):
                value = roots.get(key)
                if isinstance(value, str) and value:
                    candidates.append(value)
        evidence = profile.get("evidence") if isinstance(profile, dict) else None
        if isinstance(evidence, dict):
            for key in ("durable_roots", "generated_roots", "host_local_roots"):
                value = evidence.get(key)
                if isinstance(value, list):
                    candidates.extend(str(item) for item in value if str(item))
    return sorted(dict.fromkeys(candidates))


def _evidence_input(target: Path, relative: str) -> dict[str, Any] | None:
    path = target / relative
    if not path.exists():
        return None
    if path.is_file():
        digest = _file_sha256(path)
        kind = "file"
    elif path.is_dir():
        digest = _tree_sha256(path)
        kind = "directory"
    else:
        return None
    return {"path": relative, "kind": kind, "sha256": digest}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        if ".git" in file_path.parts:
            continue
        rel = file_path.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


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


def _false_negative_gaps(
    command: tuple[str, ...],
    external: dict[str, Any],
    embedded: dict[str, Any],
) -> list[str]:
    external_projection, embedded_projection, _accepted = _normalized_semantic_projections(
        command,
        external,
        embedded,
    )
    external_required = set(_gap_list(external_projection.get("required_gaps")))
    embedded_required = set(_gap_list(embedded_projection.get("required_gaps")))
    return sorted(embedded_required - external_required)


def _accepted_semantic_differences(*args: Any) -> list[dict[str, Any]]:
    command, external, embedded = _semantic_args(args)
    _external_projection, _embedded_projection, accepted = _normalized_semantic_projections(
        command,
        external,
        embedded,
    )
    return accepted


def _accepted_summary(differences: Iterable[object]) -> dict[str, Any]:
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
    message = "_semantic_diff expects external/embedded or command/external/embedded"
    raise TypeError(message)


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
    if embedded_gaps:
        missing_embedded_gaps = sorted(set(embedded_gaps) - set(external_gaps))
        external_extra_gaps = sorted(set(external_gaps) - set(embedded_gaps))
        if external_extra_gaps and not missing_embedded_gaps:
            accepted.append(
                _accepted_difference(
                    "external_required_gap_superset",
                    command=external_projection.get("command"),
                    gaps=external_extra_gaps,
                )
            )
            external_gaps = embedded_gaps
    else:
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
        external_projection["state"] = _ready_state_for_command(external_projection.get("command"))
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
    elif kind == "external_required_gap_superset":
        scope = "external_required_gap_superset"
        reason = "external product reports the embedded blocking gaps plus stricter required gaps"
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
    summary_value = payload.get("summary")
    summary = summary_value if isinstance(summary_value, dict) else {}
    data_value = payload.get("data")
    data = data_value if isinstance(data_value, dict) else {}
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
    data_value = payload.get("data")
    data = data_value if isinstance(data_value, dict) else {}
    repository_audit_value = data.get("repository_audit")
    repository_audit = repository_audit_value if isinstance(repository_audit_value, dict) else {}
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
    external_data_value = external.get("data")
    external_data = external_data_value if isinstance(external_data_value, dict) else {}
    embedded_summary_value = embedded.get("summary")
    embedded_summary = embedded_summary_value if isinstance(embedded_summary_value, dict) else {}
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
    external_summary_value = external.get("summary")
    external_summary = external_summary_value if isinstance(external_summary_value, dict) else {}
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
