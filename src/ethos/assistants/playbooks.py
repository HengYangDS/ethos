from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any
from typing import cast

from ethos.assistants.skills.capabilities import capability_command_strings
from ethos.assistants.skills.packages import DEFAULT_REQUIRED_SECTIONS
from ethos.assistants.skills.packages import validate_skill_markdown
from ethos.assistants.skills.packages import validate_skill_package_manifest
from ethos.assistants.skills.portfolio import portfolio_coverage
from ethos.assistants.skills.portfolio import portfolio_design
from ethos.contracts.skill.activation import normalize_skill_activation
from ethos.contracts.skill.activation import skill_registry_digest
from ethos.contracts.verdict import close_verdict
from ethos.repository.profile import DEFAULT_ROOTS
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_required_gaps

PLAYBOOK_MODES = ("v2-strict",)
PLAYBOOK_ACTIVATION_VERSION = 2


def _load_activation(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [".agents/skills/activation.toml"]
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}, [".agents/skills/activation.toml:invalid_toml"]
    return payload, []


def playbooks_report(root: Path, *, mode: str = "v2-strict") -> dict[str, object]:
    selected_mode = _mode(mode)
    profile = load_repository_profile(root)
    skills_root_relative = (
        profile.declaration.roots.agent_skills
        if profile.declaration
        else DEFAULT_ROOTS["agent_skills"]
    )
    skills_root = profile.root / skills_root_relative
    payload, missing = _load_activation(skills_root / "activation.toml")
    registry = normalize_skill_activation(payload, source=".agents/skills/activation.toml")
    registry["digest"] = skill_registry_digest(registry)
    required_gaps = [*profile_required_gaps(profile), *missing]
    advisory_gaps: list[str] = []
    activation_version = int(registry.get("meta", {}).get("version") or 1)
    collected = _collect_playbook_records(
        root,
        registry=registry,
    )
    records = collected["records"]
    package_reports = collected["package_reports"]
    package_capabilities = collected["package_capabilities"]
    required_gaps.extend(collected["required_gaps"])
    v2_gaps = list(collected["v2_gaps"])
    if activation_version < PLAYBOOK_ACTIVATION_VERSION:
        v2_gaps.append(f"playbook_activation_unsupported_version:{activation_version}")
    portfolio_coverage_report = portfolio_coverage(registry.get("coverage", {}), records)
    portfolio_design_report = portfolio_design(records, package_reports)
    v2_gaps.extend(
        str(gap) for gap in cast("list[object]", portfolio_coverage_report["required_gaps"])
    )
    v2_gaps.extend(
        str(gap) for gap in cast("list[object]", portfolio_design_report["required_gaps"])
    )
    if skills_root.exists() and not (skills_root / "README.md").exists():
        required_gaps.append(".agents/skills/README.md")
    if not skills_root.exists():
        required_gaps.append(".agents/skills")
    required_gaps.extend(dict.fromkeys(v2_gaps))
    package_quality_gaps = list(
        dict.fromkeys(
            str(gap)
            for report in package_reports
            for gap in cast("list[object]", report["required_gaps"])
        )
    )
    v2_required_gaps = list(dict.fromkeys(v2_gaps))
    score = max(0, 5 - min(5, len(dict.fromkeys(required_gaps))))
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required_gaps)),
        "schema_version": 2,
        "mode": selected_mode,
        "skills_root": skills_root_relative,
        "activation_path": (Path(skills_root_relative) / "activation.toml").as_posix(),
        "skills": [skill["id"] for skill in records],
        "records": records,
        "registry": registry,
        "coverage": _coverage(records),
        "portfolio_coverage": portfolio_coverage_report,
        "portfolio_design": portfolio_design_report,
        "package_quality": {
            "verdict": close_verdict("pass", required_gaps=tuple(package_quality_gaps)),
            "packages": package_reports,
            "capabilities": package_capabilities,
            "required_gaps": package_quality_gaps,
        },
        "v2_compliance": {
            "verdict": close_verdict("pass", required_gaps=tuple(v2_required_gaps)),
            "score": score,
            "max_score": 5,
            "required_gaps": v2_required_gaps,
        },
        "advisory_gaps": list(dict.fromkeys(advisory_gaps)),
        "required_gaps": list(dict.fromkeys(required_gaps)),
    }


def _collect_playbook_records(
    root: Path,
    *,
    registry: dict[str, Any],
) -> dict[str, Any]:
    records = []
    required_gaps: list[str] = []
    v2_gaps: list[str] = []
    package_reports: list[dict[str, Any]] = []
    package_capabilities: list[dict[str, Any]] = []
    for record in registry["records"]:
        skill_id = record["id"]
        skill_id_text = str(skill_id)
        if not skill_id:
            required_gaps.append("skill_missing_id")
            continue
        path_gaps = _record_path_gaps(root, skill_id_text, str(record["path"]))
        if path_gaps:
            v2_gaps.extend(path_gaps)
        elif not (root / str(record["path"])).exists():
            required_gaps.append(f"skill_missing_file:{skill_id_text}")
        v2_gaps.extend(_strict_record_gaps(record))
        if not path_gaps:
            quality = validate_skill_markdown(
                root,
                str(record["path"]),
                skill_id_text,
                DEFAULT_REQUIRED_SECTIONS,
            )
            v2_gaps.extend(str(gap) for gap in quality["required_gaps"])
        manifest_path = _manifest_path(record)
        package_report = validate_skill_package_manifest(root, manifest_path)
        package_reports.append(package_report)
        package_capabilities.extend(package_report["capabilities"])
        v2_gaps.extend(str(gap) for gap in package_report["required_gaps"])
        if not capability_command_strings(package_report["capabilities"]):
            v2_gaps.append(f"playbook_skill_missing_commands:{record['id']}")
        v2_gaps.extend(
            _package_entrypoint_gaps(
                root,
                skill_id_text,
                str(record["path"]),
                package_report,
            )
        )
        playbook_record = _playbook_record(record, package_report)
        records.append(playbook_record)
    return {
        "records": records,
        "required_gaps": required_gaps,
        "v2_gaps": v2_gaps,
        "package_reports": package_reports,
        "package_capabilities": package_capabilities,
    }


def _playbook_record(
    record: dict[str, Any],
    package_report: dict[str, Any],
) -> dict[str, object]:
    return {
        "id": record["id"],
        "path": record["path"],
        "subjects": list(record["route_subjects"]),
        "path_globs": list(record["activation"]["path_globs"]),
        "intent_tokens": list(record["routing"]["intent_tokens"]),
        "pre_reads": list(record["obligations"]["pre_reads"]),
        "post_checks": list(record["obligations"]["post_checks"]),
        "may_coactivate": list(record["relations"]["may_coactivate"]),
        "commands": capability_command_strings(package_report["capabilities"]),
        "boundary": record["boundary"],
        "contract_version": 2,
        "primary_subject": record["primary_subject"],
        "operation": record["operation"],
        "authority": record["authority"],
        "lifecycle": record["lifecycle"],
        "package_manifest": _manifest_path(record),
    }


def _strict_record_gaps(record: dict[str, Any]) -> list[str]:
    skill_id = str(record["id"] or "<missing>")
    gaps = []
    if not record["primary_subject"]:
        gaps.append(f"playbook_skill_missing_subject:{skill_id}")
    if not record["operation"]:
        gaps.append(f"playbook_skill_missing_operation:{skill_id}")
    if not record["authority"]:
        gaps.append(f"playbook_skill_missing_authority:{skill_id}")
    if not record["lifecycle"]:
        gaps.append(f"playbook_skill_missing_lifecycle:{skill_id}")
    if not record["activation"]["path_globs"]:
        gaps.append(f"playbook_skill_missing_path_globs:{skill_id}")
    if not record["obligations"]["pre_reads"]:
        gaps.append(f"playbook_skill_missing_pre_reads:{skill_id}")
    if not record["obligations"]["post_checks"]:
        gaps.append(f"playbook_skill_missing_post_checks:{skill_id}")
    if not record["package_manifest"]:
        gaps.append(f"skill_package_manifest_missing:{skill_id}")
    return gaps


def _manifest_path(record: dict[str, Any]) -> str:
    declared = str(record.get("package_manifest") or "")
    if declared:
        return declared
    skill_path = Path(str(record["path"]))
    return (skill_path.parent / "package.toml").as_posix()


def _record_path_gaps(root: Path, skill_id: str, relative_path: str) -> list[str]:
    if not _root_relative(root, relative_path):
        return [f"playbook_skill_path_escape:{skill_id}"]
    return []


def _package_entrypoint_gaps(
    root: Path,
    skill_id: str,
    activation_path: str,
    package_report: dict[str, Any],
) -> list[str]:
    entrypoint = str(package_report.get("entrypoint") or "")
    manifest = str(package_report.get("manifest") or "")
    if not entrypoint or not manifest:
        return []
    manifest_dir = Path(manifest).parent
    expected_path = (manifest_dir / entrypoint).as_posix()
    activation_relative = _root_relative(root, activation_path)
    expected_relative = _root_relative(root, expected_path)
    if not activation_relative or not expected_relative:
        return []
    if activation_relative != expected_relative:
        return [f"skill_package_entrypoint_mismatch:{skill_id}"]
    return []


def _root_relative(root: Path, relative_path: str) -> str:
    relative = Path(relative_path)
    if relative.is_absolute():
        return ""
    try:
        return (root / relative).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return ""


def _coverage(records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "record_count": len(records),
        "path_glob_count": sum(len(cast("list[str]", record["path_globs"])) for record in records),
        "subjects": sorted(
            {subject for record in records for subject in cast("list[str]", record["subjects"])}
        ),
    }


def _mode(mode: str) -> str:
    if mode not in PLAYBOOK_MODES:
        msg = f"unsupported playbook mode: {mode}"
        raise ValueError(msg)
    return mode
