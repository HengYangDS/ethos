from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast

MIN_ETHOS_COMMAND_PARTS = 2
CAPABILITY_KINDS = frozenset(
    {
        "resource_read",
        "schema_read",
        "docs_read",
        "prompt_template",
        "command_readonly",
        "command_proof",
        "command_mutation_guarded",
        "script_readonly",
        "script_mutation_guarded",
        "mcp_resource",
        "mcp_prompt",
        "mcp_tool_readonly",
        "mcp_tool_proof",
        "mcp_tool_mutation_guarded",
        "host_metadata_read",
        "projection_write",
    }
)
_MUTATING_ETHOS_COMMANDS = {"adopt", "land", "publish"}
_MUTATING_FLAGS = {"--apply", "--authorized", "--authorize", "--execute"}
_READONLY_ETHOS_COMMANDS = {
    "assistants",
    "audit",
    "campaign",
    "docs",
    "explain",
    "fleet",
    "openspec",
    "parity",
    "plan",
    "playbooks",
    "quality",
    "report",
    "status",
}


@dataclass(frozen=True, slots=True)
class CapabilityValidationContext:
    skill_id: str
    capability_id: str
    kind: str
    command: list[str]
    item: dict[str, Any]
    package_dir: Path
    included_files: frozenset[str]


def capability_records(
    skill_id: str,
    value: Any,
    *,
    package_dir: Path | None = None,
    included_files: frozenset[str] = frozenset(),
) -> tuple[list[str], list[dict[str, Any]]]:
    gaps: list[str] = []
    records: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return gaps, records
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            gaps.append(f"skill_package_capability_invalid:{skill_id}:{index}")
            continue
        item = cast("dict[str, Any]", item)
        kind = str(item.get("kind") or "")
        if kind not in CAPABILITY_KINDS:
            gaps.append(f"skill_package_capability_kind_unknown:{skill_id}:{kind}")
        command = item.get("command") or []
        if command and not all(isinstance(part, str) for part in command):
            gaps.append(f"skill_package_capability_command_invalid:{skill_id}:{index}")
            command = []
        capability_id = str(item.get("id") or f"{skill_id}:{index}")
        context = CapabilityValidationContext(
            skill_id=skill_id,
            capability_id=capability_id,
            kind=kind,
            command=command if isinstance(command, list) else [],
            item=item,
            package_dir=package_dir or Path(),
            included_files=included_files,
        )
        gaps.extend(capability_semantic_gaps(context))
        record = {
            "id": capability_id,
            "kind": kind,
            "command": list(command) if isinstance(command, list) else [],
        }
        if item.get("guard"):
            record["guard"] = str(item["guard"])
        records.append(record)
    return gaps, records


def capability_semantic_gaps(context: CapabilityValidationContext) -> list[str]:
    gaps: list[str] = []
    command_required = context.kind.startswith(("command_", "mcp_tool_", "script_"))
    if command_required and not context.command:
        gaps.append(capability_gap(context, "command_missing"))
    if context.kind in {"command_readonly", "mcp_tool_readonly"}:
        if is_mutating_command(context.command):
            gaps.append(capability_gap(context, "readonly_mutating"))
        elif not is_trusted_readonly_command(context.command):
            gaps.append(capability_gap(context, "readonly_untrusted"))
    if context.kind == "script_readonly":
        if is_mutating_command(context.command):
            gaps.append(capability_gap(context, "readonly_mutating"))
        elif not is_trusted_readonly_script(context):
            gaps.append(capability_gap(context, "readonly_untrusted"))
    if context.kind in {"command_proof", "mcp_tool_proof"} and not is_proof_command(
        context.command
    ):
        gaps.append(capability_gap(context, "proof_invalid"))
    if context.kind in {
        "command_mutation_guarded",
        "script_mutation_guarded",
        "mcp_tool_mutation_guarded",
    } and not str(context.item.get("guard") or ""):
        gaps.append(capability_gap(context, "guard_missing"))
    return gaps


def capability_gap(context: CapabilityValidationContext, kind: str) -> str:
    return f"skill_package_capability_{kind}:{context.skill_id}:{context.capability_id}"


def is_trusted_readonly_script(context: CapabilityValidationContext) -> bool:
    if not context.command:
        return False
    script = context.command[0]
    if script.startswith("-") or script in {".", ".."}:
        return False
    if script.startswith(("python", "python3", "bash", "sh", "uv", "npx")):
        return False
    return script in context.included_files and contained_package_path(context.package_dir, script)


def is_mutating_command(command: list[str]) -> bool:
    if not command:
        return False
    if any(part in _MUTATING_FLAGS for part in command):
        return True
    return (
        len(command) >= MIN_ETHOS_COMMAND_PARTS
        and command[0] == "ethos"
        and command[1] in _MUTATING_ETHOS_COMMANDS
    )


def is_trusted_readonly_command(command: list[str]) -> bool:
    if len(command) < MIN_ETHOS_COMMAND_PARTS or command[0] != "ethos":
        return False
    return command[1] in _READONLY_ETHOS_COMMANDS


def is_proof_command(command: list[str]) -> bool:
    return (
        len(command) >= MIN_ETHOS_COMMAND_PARTS and command[0] == "ethos" and command[1] == "prove"
    )


def contained_package_path(package_dir: Path, relative: str) -> bool:
    candidate = Path(relative)
    if candidate.is_absolute():
        return False
    try:
        (package_dir / candidate).resolve().relative_to(package_dir.resolve())
    except ValueError:
        return False
    return True
