from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast

SKILL_PACKAGE_SCHEMA_VERSION = 2
MIN_ETHOS_COMMAND_PARTS = 2
FRONTMATTER_PART_COUNT = 3
SKILL_DESCRIPTION_WORD_LIMIT = 60
PROGRESSIVE_DISCLOSURE_LINE_THRESHOLD = 90
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
DEFAULT_REQUIRED_SECTIONS = ("When to Use", "Workflow", "Evidence", "Trust Boundary")
_SKILL_SOFT_LINE_LIMIT = 160
_SKILL_WORKFLOW_STEP_LIMIT = 8
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
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


@dataclass(frozen=True)
class CapabilityValidationContext:
    skill_id: str
    capability_id: str
    kind: str
    command: list[str]
    item: dict[str, Any]
    package_dir: Path
    included_files: frozenset[str]


@dataclass(frozen=True)
class SkillPackageResult:
    skill_id: str
    manifest_path: str
    digest: str = ""
    expected_digest: str = ""
    required_gaps: tuple[str, ...] = ()
    capabilities: tuple[dict[str, Any], ...] = ()
    files: tuple[str, ...] = ()
    entrypoint: str = ""
    required_sections: tuple[str, ...] = ()


def compute_skill_package_digest(package_dir: Path, include: list[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(include):
        path = package_dir / relative
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def validate_skill_package_manifest(root: Path, manifest_path: str) -> dict[str, Any]:
    relative_manifest = Path(manifest_path)
    root = root.resolve()
    skill_id = relative_manifest.parent.name or relative_manifest.stem
    if relative_manifest.is_absolute() or not _contained_root_path(root, relative_manifest):
        return _manifest_result(
            SkillPackageResult(
                skill_id=skill_id,
                manifest_path=manifest_path,
                required_gaps=(f"skill_package_manifest_path_escape:{skill_id}",),
            )
        )
    absolute_manifest = (root / relative_manifest).resolve()
    package_dir = absolute_manifest.parent
    gaps: list[str] = []
    try:
        manifest = tomllib.loads(absolute_manifest.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _manifest_result(
            SkillPackageResult(
                skill_id=skill_id,
                manifest_path=manifest_path,
                required_gaps=(f"skill_package_manifest_missing:{skill_id}",),
            )
        )
    except tomllib.TOMLDecodeError:
        return _manifest_result(
            SkillPackageResult(
                skill_id=skill_id,
                manifest_path=manifest_path,
                required_gaps=(f"skill_package_manifest_invalid_toml:{skill_id}",),
            )
        )

    skill_id = str(manifest.get("id") or relative_manifest.parent.name)
    entrypoint = str(manifest.get("entrypoint") or "SKILL.md")
    include = _string_list(manifest.get("include")) or [entrypoint]
    gaps.extend(_manifest_schema_gaps(skill_id, manifest))
    for relative in [entrypoint, *include]:
        if not _contained_package_path(package_dir, relative):
            gaps.append(f"skill_package_path_escape:{skill_id}:{relative}")
    safe_include = [
        relative for relative in include if _contained_package_path(package_dir, relative)
    ]
    for relative in safe_include:
        if not (package_dir / relative).exists():
            gaps.append(f"skill_package_file_missing:{skill_id}:{relative}")

    digest = ""
    has_missing_files = any(gap.startswith("skill_package_file_missing:") for gap in gaps)
    has_escaped_paths = any(gap.startswith("skill_package_path_escape:") for gap in gaps)
    if not has_escaped_paths and not has_missing_files and safe_include:
        digest = compute_skill_package_digest(package_dir, safe_include)
        expected = str(manifest.get("expected_digest") or "")
        if expected and expected != digest:
            gaps.append(f"skill_package_digest_mismatch:{skill_id}")

    required_sections = _string_list(manifest.get("required_sections")) or list(
        DEFAULT_REQUIRED_SECTIONS
    )
    if _contained_package_path(package_dir, entrypoint):
        quality_policy = cast(
            "dict[str, Any]",
            manifest.get("quality") if isinstance(manifest.get("quality"), dict) else {},
        )
        quality = validate_skill_markdown(
            root,
            (package_dir / entrypoint).relative_to(root),
            skill_id,
            required_sections,
            placeholder_allowed=bool(quality_policy.get("placeholder_allowed", True)),
        )
        gaps.extend(quality["required_gaps"])
    capability_gaps, capabilities = _capability_records(
        skill_id,
        manifest.get("capability"),
        package_dir=package_dir,
        included_files=frozenset(safe_include),
    )
    gaps.extend(capability_gaps)
    return _manifest_result(
        SkillPackageResult(
            skill_id=skill_id,
            manifest_path=manifest_path,
            digest=digest,
            expected_digest=str(manifest.get("expected_digest") or ""),
            required_gaps=tuple(gaps),
            capabilities=tuple(capabilities),
            files=tuple(safe_include),
            entrypoint=entrypoint,
            required_sections=tuple(required_sections),
        )
    )


def validate_skill_markdown(
    root: Path,
    relative_path: str | Path,
    skill_id: str,
    required_sections: list[str] | tuple[str, ...] = DEFAULT_REQUIRED_SECTIONS,
    *,
    placeholder_allowed: bool = True,
) -> dict[str, Any]:
    path = root / relative_path
    gaps: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"ok": False, "required_gaps": [f"skill_missing_file:{skill_id}"]}
    if not _frontmatter_ok(text):
        gaps.append(f"skill_quality_missing_frontmatter:{skill_id}")
    gaps.extend(_frontmatter_gaps(skill_id, text))
    gaps.extend(_progressive_disclosure_gaps(skill_id, text))
    for section in required_sections:
        if f"## {section}" not in text:
            gaps.append(f"skill_quality_missing_section:{skill_id}:{section}")
    lower_text = text.lower()
    if (
        "source of truth" not in lower_text
        and "repository truth" not in lower_text
        and "are truth" not in lower_text
    ):
        gaps.append(f"skill_quality_missing_truth_boundary:{skill_id}")
    if not placeholder_allowed:
        for section in required_sections:
            body = _section_body(text, section)
            if _is_placeholder_body(body):
                gaps.append(f"skill_quality_placeholder_section:{skill_id}:{section}")
    return {"ok": not gaps, "required_gaps": gaps}


def _manifest_result(result: SkillPackageResult) -> dict[str, Any]:
    gaps = list(result.required_gaps)
    return {
        "ok": not gaps,
        "id": result.skill_id,
        "manifest": result.manifest_path,
        "digest": result.digest,
        "expected_digest": result.expected_digest,
        "entrypoint": result.entrypoint,
        "files": list(result.files),
        "required_sections": list(result.required_sections),
        "capabilities": list(result.capabilities),
        "required_gaps": gaps,
    }


def _capability_records(
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
        gaps.extend(_capability_semantic_gaps(context))
        record = {
            "id": capability_id,
            "kind": kind,
            "command": list(command) if isinstance(command, list) else [],
        }
        if item.get("guard"):
            record["guard"] = str(item["guard"])
        records.append(record)
    return gaps, records


def _manifest_schema_gaps(skill_id: str, manifest: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if manifest.get("schema_version") != SKILL_PACKAGE_SCHEMA_VERSION:
        gaps.append(f"skill_package_schema_version_invalid:{skill_id}")
    if manifest.get("digest_algorithm") != "sha256":
        gaps.append(f"skill_package_digest_algorithm_invalid:{skill_id}")
    include = _string_list(manifest.get("include"))
    if not include:
        gaps.append(f"skill_package_include_missing:{skill_id}")
    expected = str(manifest.get("expected_digest") or "")
    if not expected:
        gaps.append(f"skill_package_expected_digest_missing:{skill_id}")
    elif not _SHA256_PATTERN.fullmatch(expected):
        gaps.append(f"skill_package_expected_digest_invalid:{skill_id}")
    required_sections = _string_list(manifest.get("required_sections"))
    if not required_sections:
        gaps.append(f"skill_package_required_sections_missing:{skill_id}")
    return gaps


def _capability_semantic_gaps(context: CapabilityValidationContext) -> list[str]:
    gaps: list[str] = []
    command_required = context.kind.startswith(("command_", "mcp_tool_", "script_"))
    if command_required and not context.command:
        gaps.append(_capability_gap(context, "command_missing"))
    if context.kind in {"command_readonly", "mcp_tool_readonly"}:
        if _is_mutating_command(context.command):
            gaps.append(_capability_gap(context, "readonly_mutating"))
        elif not _is_trusted_readonly_command(context.command):
            gaps.append(_capability_gap(context, "readonly_untrusted"))
    if context.kind == "script_readonly":
        if _is_mutating_command(context.command):
            gaps.append(_capability_gap(context, "readonly_mutating"))
        elif not _is_trusted_readonly_script(context):
            gaps.append(_capability_gap(context, "readonly_untrusted"))
    if context.kind in {"command_proof", "mcp_tool_proof"} and not _is_proof_command(
        context.command
    ):
        gaps.append(_capability_gap(context, "proof_invalid"))
    if context.kind in {
        "command_mutation_guarded",
        "script_mutation_guarded",
        "mcp_tool_mutation_guarded",
    } and not str(context.item.get("guard") or ""):
        gaps.append(_capability_gap(context, "guard_missing"))
    return gaps


def _capability_gap(context: CapabilityValidationContext, kind: str) -> str:
    return f"skill_package_capability_{kind}:{context.skill_id}:{context.capability_id}"


def _is_trusted_readonly_script(context: CapabilityValidationContext) -> bool:
    if not context.command:
        return False
    script = context.command[0]
    if script.startswith("-") or script in {".", ".."}:
        return False
    if script.startswith(("python", "python3", "bash", "sh", "uv", "npx")):
        return False
    return script in context.included_files and _contained_package_path(context.package_dir, script)


def _is_mutating_command(command: list[str]) -> bool:
    if not command:
        return False
    if any(part in _MUTATING_FLAGS for part in command):
        return True
    return (
        len(command) >= MIN_ETHOS_COMMAND_PARTS
        and command[0] == "ethos"
        and command[1] in _MUTATING_ETHOS_COMMANDS
    )


def _is_trusted_readonly_command(command: list[str]) -> bool:
    if len(command) < MIN_ETHOS_COMMAND_PARTS or command[0] != "ethos":
        return False
    return command[1] in _READONLY_ETHOS_COMMANDS


def _is_proof_command(command: list[str]) -> bool:
    return (
        len(command) >= MIN_ETHOS_COMMAND_PARTS and command[0] == "ethos" and command[1] == "prove"
    )


def _contained_root_path(root: Path, relative: Path) -> bool:
    try:
        (root / relative).resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _contained_package_path(package_dir: Path, relative: str) -> bool:
    candidate = Path(relative)
    if candidate.is_absolute():
        return False
    try:
        (package_dir / candidate).resolve().relative_to(package_dir.resolve())
    except ValueError:
        return False
    return True


def _frontmatter_gaps(skill_id: str, text: str) -> list[str]:
    header = _frontmatter_header(text)
    if not header:
        return []
    fields: dict[str, str] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    gaps: list[str] = []
    name = fields.get("name", "")
    description = fields.get("description", "")
    if name and name != skill_id:
        gaps.append(f"skill_quality_name_mismatch:{skill_id}:{name}")
    if description and not description.startswith("Use when"):
        gaps.append(f"skill_quality_description_not_trigger:{skill_id}")
    if description and len(description.split()) > SKILL_DESCRIPTION_WORD_LIMIT:
        gaps.append(f"skill_quality_description_too_long:{skill_id}")
    return gaps


def _progressive_disclosure_gaps(skill_id: str, text: str) -> list[str]:
    gaps: list[str] = []
    line_count = len(text.splitlines())
    if line_count > _SKILL_SOFT_LINE_LIMIT:
        gaps.append(f"skill_quality_entrypoint_too_long:{skill_id}:{line_count}")
    workflow = _section_body(text, "Workflow")
    step_count = sum(
        1 for line in workflow.splitlines() if re.match(r"^\s*(?:\d+\.|[-*])\s+", line)
    )
    if step_count > _SKILL_WORKFLOW_STEP_LIMIT:
        gaps.append(f"skill_quality_workflow_too_many_steps:{skill_id}:{step_count}")
    has_references = "references/" in text
    has_scripts = "scripts/" in text
    if line_count > PROGRESSIVE_DISCLOSURE_LINE_THRESHOLD and not (has_references or has_scripts):
        gaps.append(f"skill_quality_progressive_disclosure_missing:{skill_id}")
    return gaps


def _frontmatter_header(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < FRONTMATTER_PART_COUNT:
        return ""
    return parts[1]


def _frontmatter_ok(text: str) -> bool:
    if not text.startswith("---\n"):
        return False
    parts = text.split("---", 2)
    if len(parts) < FRONTMATTER_PART_COUNT:
        return False
    header = parts[1]
    return "name:" in header and "description:" in header


def _section_body(text: str, section: str) -> str:
    marker = f"## {section}"
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[1]
    if "\n## " in tail:
        tail = tail.split("\n## ", 1)[0]
    return tail.strip()


def _is_placeholder_body(body: str) -> bool:
    normalized = body.strip().lower().strip(".")
    return normalized in {"", "tbd", "todo", "placeholder", "coming soon"}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]
