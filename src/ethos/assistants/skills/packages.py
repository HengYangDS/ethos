from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast

from ethos.assistants.skills.capabilities import capability_records
from ethos.assistants.skills.capabilities import contained_package_path
from ethos.normalization.core import string_list

SKILL_PACKAGE_SCHEMA_VERSION = 2
FRONTMATTER_PART_COUNT = 3
SKILL_DESCRIPTION_WORD_LIMIT = 60
PROGRESSIVE_DISCLOSURE_LINE_THRESHOLD = 90
DEFAULT_REQUIRED_SECTIONS = ("When to Use", "Workflow", "Evidence", "Trust Boundary")
_SKILL_SOFT_LINE_LIMIT = 160
_SKILL_WORKFLOW_STEP_LIMIT = 8
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


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
    gaps: list[str] = []

    skill_id = str(manifest.get("id") or relative_manifest.parent.name)
    entrypoint = str(manifest.get("entrypoint") or "SKILL.md")
    include = string_list(manifest.get("include"), drop_empty=True) or [entrypoint]
    gaps.extend(_manifest_schema_gaps(skill_id, manifest))
    for relative in [entrypoint, *include]:
        if not contained_package_path(package_dir, relative):
            gaps.append(f"skill_package_path_escape:{skill_id}:{relative}")
    safe_include = [
        relative for relative in include if contained_package_path(package_dir, relative)
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

    required_sections = string_list(manifest.get("required_sections"), drop_empty=True) or list(
        DEFAULT_REQUIRED_SECTIONS
    )
    if contained_package_path(package_dir, entrypoint):
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
    capability_gaps, capabilities = capability_records(
        skill_id,
        manifest.get("capability"),
        package_dir=package_dir,
        included_files=frozenset(safe_include),
    )
    gaps.extend(capability_gaps)
    eval_gaps, eval_metadata = _eval_metadata(skill_id, manifest.get("eval"))
    gaps.extend(eval_gaps)
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
        "eval": result.eval_metadata or {},
        "required_gaps": gaps,
    }


def _manifest_schema_gaps(skill_id: str, manifest: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if manifest.get("schema_version") != SKILL_PACKAGE_SCHEMA_VERSION:
        gaps.append(f"skill_package_schema_version_invalid:{skill_id}")
    if manifest.get("digest_algorithm") != "sha256":
        gaps.append(f"skill_package_digest_algorithm_invalid:{skill_id}")
    include = string_list(manifest.get("include"), drop_empty=True)
    if not include:
        gaps.append(f"skill_package_include_missing:{skill_id}")
    expected = str(manifest.get("expected_digest") or "")
    if not expected:
        gaps.append(f"skill_package_expected_digest_missing:{skill_id}")
    elif not _SHA256_PATTERN.fullmatch(expected):
        gaps.append(f"skill_package_expected_digest_invalid:{skill_id}")
    required_sections = string_list(manifest.get("required_sections"), drop_empty=True)
    if not required_sections:
        gaps.append(f"skill_package_required_sections_missing:{skill_id}")
    return gaps


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


_ALLOWED_EVAL_METRICS = {"pass_at_k", "pass_power_k", "weighted_score", "instability_gap"}


def _eval_metadata(skill_id: str, value: Any) -> tuple[list[str], dict[str, Any]]:
    if value is None:
        return [], {}
    if not isinstance(value, dict):
        return [f"skill_package_eval_invalid:{skill_id}"], {}
    gaps: list[str] = []
    treatment_id = str(value.get("treatment_id") or "")
    if not treatment_id:
        gaps.append(f"skill_package_eval_treatment_missing:{skill_id}")
    metrics = string_list(value.get("metrics"), drop_empty=True)
    if not metrics:
        gaps.append(f"skill_package_eval_metrics_missing:{skill_id}")
    for metric in metrics:
        if metric not in _ALLOWED_EVAL_METRICS:
            gaps.append(f"skill_package_eval_metric_unknown:{skill_id}:{metric}")
    for key in _ALLOWED_EVAL_METRICS:
        if key in value and not _unit_interval(value.get(key)):
            gaps.append(f"skill_package_eval_metric_out_of_bounds:{skill_id}:{key}")
    evidence_refs = string_list(value.get("evidence_refs"), drop_empty=True)
    if not evidence_refs:
        gaps.append(f"skill_package_eval_evidence_refs_missing:{skill_id}")
    return gaps, {
        "treatment_id": treatment_id,
        "metrics": metrics,
        "pass_at_k": value.get("pass_at_k"),
        "pass_power_k": value.get("pass_power_k"),
        "weighted_score": value.get("weighted_score"),
        "instability_gap": value.get("instability_gap"),
        "evidence_refs": evidence_refs,
        "truth_boundary": "skill_metadata_only",
    }


def _unit_interval(value: Any) -> bool:
    return isinstance(value, int | float) and 0 <= float(value) <= 1
