from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.admission import ethos_command_is_readonly
from ethos.contracts.admission import ethos_command_mutates

if TYPE_CHECKING:
    from collections.abc import Iterable


def capability_records(
    skill_id: str,
    value: list[dict[str, Any]],
    *,
    package_dir: Path | None = None,
    included_files: frozenset[str] = frozenset(),
) -> tuple[list[str], list[dict[str, Any]]]:
    """Project schema-valid declarations and enforce command semantics."""
    gaps: list[str] = []
    records: list[dict[str, Any]] = []
    for item in value:
        kind = str(item["kind"])
        command = list(item.get("command") or [])
        capability_id = str(item["id"])
        gaps.extend(
            _semantic_gaps(
                skill_id,
                capability_id,
                kind,
                command,
                package_dir or Path(),
                included_files,
            )
        )
        record = {
            "id": capability_id,
            "kind": kind,
            "command": list(command) if isinstance(command, list) else [],
        }
        if item.get("guard"):
            record["guard"] = str(item["guard"])
        records.append(record)
    return gaps, records


def capability_command_strings(capabilities: Iterable[dict[str, Any]]) -> list[str]:
    return [
        " ".join(str(part) for part in capability["command"])
        for capability in capabilities
        if capability.get("command")
    ]


def _semantic_gaps(
    skill_id: str,
    capability_id: str,
    kind: str,
    command: list[str],
    package_dir: Path,
    included_files: frozenset[str],
) -> list[str]:
    """Validate the semantics schema declarations cannot establish."""
    gaps: list[str] = []
    if kind in {"command_readonly", "mcp_tool_readonly"}:
        if ethos_command_mutates(command):
            gaps.append(_capability_gap(skill_id, capability_id, "readonly_mutating"))
        elif not ethos_command_is_readonly(command):
            gaps.append(_capability_gap(skill_id, capability_id, "readonly_untrusted"))
    if kind == "script_readonly":
        if ethos_command_mutates(command):
            gaps.append(_capability_gap(skill_id, capability_id, "readonly_mutating"))
        elif not _trusted_readonly_script(command, package_dir, included_files):
            gaps.append(_capability_gap(skill_id, capability_id, "readonly_untrusted"))
    if kind in {"command_proof", "mcp_tool_proof"} and not _proof_command(command):
        gaps.append(_capability_gap(skill_id, capability_id, "proof_invalid"))
    return gaps


def _capability_gap(skill_id: str, capability_id: str, kind: str) -> str:
    return f"skill_package_capability_{kind}:{skill_id}:{capability_id}"


def _trusted_readonly_script(
    command: list[str], package_dir: Path, included_files: frozenset[str]
) -> bool:
    if not command:
        return False
    script = command[0]
    if script.startswith("-") or script in {".", ".."}:
        return False
    if script.startswith(("python", "python3", "bash", "sh", "uv", "npx")):
        return False
    return script in included_files and contained_package_path(package_dir, script)


def _proof_command(command: list[str]) -> bool:
    return command[:2] == ["ethos", "prove"]


def contained_package_path(package_dir: Path, relative: str) -> bool:
    candidate = Path(relative)
    if candidate.is_absolute():
        return False
    try:
        (package_dir / candidate).resolve().relative_to(package_dir.resolve())
    except ValueError:
        return False
    return True
