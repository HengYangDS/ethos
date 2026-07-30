from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ethos._resources import resolve_declaration_path
from ethos.assistants.skills.capabilities import capability_records
from ethos.assistants.skills.capabilities import contained_package_path
from ethos.normalization.coercion import string_list

FRONTMATTER_PART_COUNT = 3
SKILL_DESCRIPTION_WORD_LIMIT = 60
PROGRESSIVE_DISCLOSURE_LINE_THRESHOLD = 90
DEFAULT_REQUIRED_SECTIONS = ("When to Use", "Workflow", "Evidence", "Trust Boundary")
_SKILL_SOFT_LINE_LIMIT = 160
_SKILL_WORKFLOW_STEP_LIMIT = 8
_MANIFEST_SCHEMA_PATH = Path("system/schemas/kernel/skill-package-manifest.schema.json")


@dataclass(frozen=True, slots=True)
class SkillPackageResult:
    skill_id: str
    manifest_path: str
    digest: str = ""
    expected_digest: str = ""
    required_gaps: tuple[str, ...] = ()
    capabilities: tuple[dict[str, Any], ...] = ()
    eval_metadata: dict[str, Any] | None = None
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
    absolute_manifest = (root / relative_manifest).resolve()
    manifest, early_result = _manifest_payload(
        root,
        relative_manifest,
        skill_id=skill_id,
        manifest_path=manifest_path,
    )
    if early_result is not None:
        return _manifest_result(early_result)
    package_dir = absolute_manifest.parent
    gaps = _schema_validation_gaps(root, skill_id, manifest)
    if gaps:
        return _manifest_result(
            SkillPackageResult(
                skill_id=skill_id,
                manifest_path=manifest_path,
                required_gaps=tuple(gaps),
            )
        )

    skill_id = str(manifest.get("id") or relative_manifest.parent.name)
    entrypoint = str(manifest.get("entrypoint") or "SKILL.md")
    include = string_list(manifest.get("include"), drop_empty=True) or [entrypoint]
    gaps.extend(
        f"skill_package_path_escape:{skill_id}:{relative}"
        for relative in [entrypoint, *include]
        if not contained_package_path(package_dir, relative)
    )
    safe_include = [
        relative for relative in include if contained_package_path(package_dir, relative)
    ]
    gaps.extend(
        f"skill_package_file_missing:{skill_id}:{relative}"
        for relative in safe_include
        if not (package_dir / relative).exists()
    )

    digest = ""
    has_missing_files = any(gap.startswith("skill_package_file_missing:") for gap in gaps)
    has_escaped_paths = any(gap.startswith("skill_package_path_escape:") for gap in gaps)
    if not has_escaped_paths and not has_missing_files and safe_include:
        digest = compute_skill_package_digest(package_dir, safe_include)
        expected = str(manifest.get("expected_digest") or "")
        if expected and expected != digest:
            gaps.append(f"skill_package_digest_mismatch:{skill_id}")

    required_sections = string_list(manifest.get("required_sections"), drop_empty=True) or list(
        DEFAULT_REQUIRED_SECTIONS
    )
    if contained_package_path(package_dir, entrypoint):
        quality_policy = (
            manifest.get("quality") if isinstance(manifest.get("quality"), dict) else {}
        )
        quality = validate_skill_markdown(
            root,
            (package_dir / entrypoint).relative_to(root),
            skill_id,
            required_sections,
            placeholder_allowed=bool(quality_policy.get("placeholder_allowed", True)),
        )
        gaps.extend(quality["required_gaps"])
    capability_gaps, capabilities = capability_records(
        skill_id,
        manifest.get("capability") or [],
        package_dir=package_dir,
        included_files=frozenset(safe_include),
    )
    gaps.extend(capability_gaps)
    eval_value = manifest.get("eval")
    eval_metadata = (
        {**eval_value, "truth_boundary": "skill_metadata_only"}
        if isinstance(eval_value, dict)
        else None
    )
    return _manifest_result(
        SkillPackageResult(
            skill_id=skill_id,
            manifest_path=manifest_path,
            digest=digest,
            expected_digest=str(manifest.get("expected_digest") or ""),
            required_gaps=tuple(gaps),
            capabilities=tuple(capabilities),
            eval_metadata=eval_metadata,
            files=tuple(safe_include),
            entrypoint=entrypoint,
            required_sections=tuple(required_sections),
        )
    )


def _manifest_payload(
    root: Path,
    relative_manifest: Path,
    *,
    skill_id: str,
    manifest_path: str,
) -> tuple[dict[str, Any], SkillPackageResult | None]:
    if relative_manifest.is_absolute() or not _contained_root_path(root, relative_manifest):
        return {}, SkillPackageResult(
            skill_id=skill_id,
            manifest_path=manifest_path,
            required_gaps=(f"skill_package_manifest_path_escape:{skill_id}",),
        )
    try:
        return tomllib.loads((root / relative_manifest).read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return {}, SkillPackageResult(
            skill_id=skill_id,
            manifest_path=manifest_path,
            required_gaps=(f"skill_package_manifest_missing:{skill_id}",),
        )
    except tomllib.TOMLDecodeError:
        return {}, SkillPackageResult(
            skill_id=skill_id,
            manifest_path=manifest_path,
            required_gaps=(f"skill_package_manifest_invalid_toml:{skill_id}",),
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
    gaps.extend(
        f"skill_quality_missing_section:{skill_id}:{section}"
        for section in required_sections
        if f"## {section}" not in text
    )
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
        "eval": result.eval_metadata or {},
        "required_gaps": gaps,
    }


def _schema_validation_gaps(root: Path, skill_id: str, manifest: dict[str, Any]) -> list[str]:
    try:
        schema_path = root / _MANIFEST_SCHEMA_PATH
        if not schema_path.is_file():
            schema_path = resolve_declaration_path(
                None,
                canonical=_MANIFEST_SCHEMA_PATH,
                module_file=__file__,
            )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = Draft202012Validator(schema).iter_errors(manifest)
    except (OSError, json.JSONDecodeError, SchemaError):
        return [f"skill_package_manifest_schema_invalid:{skill_id}"]
    gaps = [
        _schema_gap(skill_id, schema, error)
        for error in sorted(errors, key=lambda item: item.json_path)
    ]
    return list(dict.fromkeys(gaps))


def _schema_gap(skill_id: str, schema: dict[str, Any], error: Any) -> str:
    node: Any = schema
    nodes = [node]
    for part in error.absolute_schema_path:
        node = node[part] if isinstance(node, list) else node.get(part, {})
        nodes.append(node)
    path = tuple(error.absolute_path)
    if error.validator == "required":
        missing = next(key for key in error.validator_value if key not in error.instance)
        template = next(
            (
                candidate.get("x-ethos-required-gaps", {}).get(missing)
                for candidate in reversed(nodes)
                if isinstance(candidate, dict)
                and candidate.get("x-ethos-required-gaps", {}).get(missing)
            ),
            "",
        )
    else:
        template = next(
            (
                candidate.get("x-ethos-gap")
                for candidate in reversed(nodes)
                if isinstance(candidate, dict) and candidate.get("x-ethos-gap")
            ),
            "",
        )
    capability_id = str(error.instance.get("id") or "") if isinstance(error.instance, dict) else ""
    values = {
        "skill_id": skill_id,
        "field": str(path[-1]) if path and isinstance(path[-1], str) else "",
        "index": next((str(part) for part in path if isinstance(part, int)), "0"),
        "value": str(error.instance),
        "capability_id": capability_id,
    }
    return str(template or "skill_package_manifest_invalid:{skill_id}").format(**values)


def _contained_root_path(root: Path, relative: Path) -> bool:
    try:
        (root / relative).resolve().relative_to(root.resolve())
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
