"""Validate the repository skill portfolio through one semantic owner."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any
from typing import cast

from ethos.assistants.skills.capabilities import capability_command_strings
from ethos.assistants.skills.packages import DEFAULT_REQUIRED_SECTIONS
from ethos.assistants.skills.packages import validate_skill_markdown
from ethos.assistants.skills.packages import validate_skill_package_manifest
from ethos.contracts.skill.activation import normalize_skill_activation
from ethos.contracts.verdict import close_verdict
from ethos.normalization.coercion import string_list
from ethos.repository.policy.schema import validate_schema_instance
from ethos.repository.profile import DEFAULT_ROOTS
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_required_gaps

SKILL_PACKAGE_FILE_LIMIT = 6
INTENT_TOKEN_OWNER_LIMIT = 2


def _load_activation(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [".agents/skills/activation.toml"]
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}, [".agents/skills/activation.toml:invalid_toml"]
    validation = validate_schema_instance("skill-activation.schema.json", payload)
    if validation["verdict"] != "pass":
        return {}, [f"skill_activation_invalid:{path}:{gap}" for gap in validation["required_gaps"]]
    return payload, []


def skill_portfolio_report(root: Path) -> dict[str, object]:
    """Validate the native portfolio and project its sole current interpretation."""
    profile = load_repository_profile(root)
    skills_root_relative = (
        profile.declaration.roots.agent_skills
        if profile.declaration
        else DEFAULT_ROOTS["agent_skills"]
    )
    skills_root = profile.root / skills_root_relative
    payload, missing = _load_activation(skills_root / "activation.toml")
    registry = normalize_skill_activation(payload, source=".agents/skills/activation.toml")
    required_gaps = [*profile_required_gaps(profile), *missing]
    advisory_gaps: list[str] = []
    collected = _collect_skill_records(
        root,
        registry=registry,
    )
    records = collected["records"]
    package_reports = collected["package_reports"]
    package_capabilities = collected["package_capabilities"]
    record_gaps = list(collected["record_gaps"])
    portfolio_coverage_report = portfolio_coverage(registry.get("coverage", {}), records)
    portfolio_design_report = portfolio_design(records, package_reports)
    portfolio_retirement_report = portfolio_retirement(registry, records, root)
    record_gaps.extend(
        str(gap) for gap in cast("list[object]", portfolio_coverage_report["required_gaps"])
    )
    record_gaps.extend(
        str(gap) for gap in cast("list[object]", portfolio_design_report["required_gaps"])
    )
    record_gaps.extend(
        str(gap) for gap in cast("list[object]", portfolio_retirement_report["required_gaps"])
    )
    if skills_root.exists() and not (skills_root / "README.md").exists():
        required_gaps.append(".agents/skills/README.md")
    if not skills_root.exists():
        required_gaps.append(".agents/skills")
    required_gaps.extend(dict.fromkeys(record_gaps))
    package_quality_gaps = list(
        dict.fromkeys(
            str(gap)
            for report in package_reports
            for gap in cast("list[object]", report["required_gaps"])
        )
    )
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required_gaps)),
        "skills_root": skills_root_relative,
        "activation_path": (Path(skills_root_relative) / "activation.toml").as_posix(),
        "skills": [skill["id"] for skill in records],
        "records": records,
        "registry": registry,
        "coverage": _coverage(records),
        "portfolio_coverage": portfolio_coverage_report,
        "portfolio_design": portfolio_design_report,
        "portfolio_retirement": portfolio_retirement_report,
        "package_quality": {
            "verdict": close_verdict("pass", required_gaps=tuple(package_quality_gaps)),
            "packages": package_reports,
            "capabilities": package_capabilities,
            "required_gaps": package_quality_gaps,
        },
        "advisory_gaps": list(dict.fromkeys(advisory_gaps)),
        "required_gaps": list(dict.fromkeys(required_gaps)),
    }


def _collect_skill_records(
    root: Path,
    *,
    registry: dict[str, Any],
) -> dict[str, Any]:
    records = []
    record_gaps: list[str] = []
    package_reports: list[dict[str, Any]] = []
    package_capabilities: list[dict[str, Any]] = []
    for record in registry["records"]:
        skill_id = record["id"]
        skill_id_text = str(skill_id)
        path_gaps = _record_path_gaps(root, skill_id_text, str(record["path"]))
        if path_gaps:
            record_gaps.extend(path_gaps)
        elif not (root / str(record["path"])).exists():
            record_gaps.append(f"skill_missing_file:{skill_id_text}")
        if not path_gaps:
            quality = validate_skill_markdown(
                root,
                str(record["path"]),
                skill_id_text,
                DEFAULT_REQUIRED_SECTIONS,
            )
            record_gaps.extend(str(gap) for gap in quality["required_gaps"])
        manifest_path = str(record["package_manifest"])
        package_report = validate_skill_package_manifest(root, manifest_path)
        package_reports.append(package_report)
        package_capabilities.extend(package_report["capabilities"])
        record_gaps.extend(str(gap) for gap in package_report["required_gaps"])
        if not capability_command_strings(package_report["capabilities"]):
            record_gaps.append(f"skill_missing_commands:{record['id']}")
        record_gaps.extend(
            _package_entrypoint_gaps(
                root,
                skill_id_text,
                str(record["path"]),
                package_report,
            )
        )
        skill_record = _skill_record(record, package_report)
        records.append(skill_record)
    return {
        "records": records,
        "record_gaps": record_gaps,
        "package_reports": package_reports,
        "package_capabilities": package_capabilities,
    }


def _skill_record(
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
        "requires": list(record["relations"]["requires"]),
        "excludes": list(record["relations"]["excludes"]),
        "commands": capability_command_strings(package_report["capabilities"]),
        "boundary": record["boundary"],
        "primary_subject": record["primary_subject"],
        "operation": record["operation"],
        "authority": record["authority"],
        "lifecycle": record["lifecycle"],
        "package_manifest": record["package_manifest"],
    }


def _record_path_gaps(root: Path, skill_id: str, relative_path: str) -> list[str]:
    if not _root_relative(root, relative_path):
        return [f"skill_path_escape:{skill_id}"]
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


def portfolio_coverage(
    coverage_contract: object,
    records: list[dict[str, object]],
) -> dict[str, object]:
    contract = coverage_contract if isinstance(coverage_contract, dict) else {}
    required_subjects = list(
        dict.fromkeys(string_list(contract.get("required_primary_subjects"), drop_empty=True))
    )
    single_owner_subjects = list(
        dict.fromkeys(
            [
                *required_subjects,
                *string_list(contract.get("single_owner_subjects"), drop_empty=True),
            ]
        )
    )
    owners: dict[str, list[str]] = {}
    for record in records:
        if str(record["authority"]) != "primary" or str(record["lifecycle"]) != "active":
            continue
        subject = str(record["primary_subject"])
        skill_id = str(record["id"])
        if not subject or not skill_id:
            continue
        owners.setdefault(subject, []).append(skill_id)
    gaps: list[str] = []
    gaps.extend(
        f"skill_portfolio_subject_missing:{subject}"
        for subject in required_subjects
        if not owners.get(subject)
    )
    for subject in single_owner_subjects:
        subject_owners = owners.get(subject, [])
        if len(subject_owners) > 1:
            gaps.append(f"skill_portfolio_subject_duplicate:{subject}:{','.join(subject_owners)}")
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "contract": {
            "required_primary_subjects": required_subjects,
            "single_owner_subjects": single_owner_subjects,
        },
        "owners": {subject: list(ids) for subject, ids in sorted(owners.items())},
        "required_gaps": gaps,
    }


def portfolio_design(
    records: list[dict[str, object]],
    package_reports: list[dict[str, Any]],
) -> dict[str, object]:
    gaps: list[str] = []
    command_owners: dict[str, list[str]] = {}
    path_owners: dict[str, list[str]] = {}
    token_owners: dict[str, list[str]] = {}
    route_owners: dict[str, list[str]] = {}
    package_by_id = {str(report.get("id") or ""): report for report in package_reports}
    for record in records:
        skill_id = str(record["id"])
        subjects = [str(item) for item in cast("list[str]", record["subjects"])]
        if str(record["primary_subject"]) not in subjects:
            gaps.append(f"skill_portfolio_primary_subject_not_routed:{skill_id}")
        package = package_by_id.get(skill_id, {})
        for command in capability_command_strings(package.get("capabilities", [])):
            command_owners.setdefault(command, []).append(skill_id)
        for pattern in cast("list[str]", record["path_globs"]):
            path_owners.setdefault(pattern, []).append(skill_id)
        for token in cast("list[str]", record["intent_tokens"]):
            token_owners.setdefault(token, []).append(skill_id)
        route_key = ":".join(
            value for value in (str(record["primary_subject"]), str(record["operation"])) if value
        )
        if route_key:
            route_owners.setdefault(route_key, []).append(skill_id)
        file_count = len(cast("list[object]", package.get("files", [])))
        if file_count > SKILL_PACKAGE_FILE_LIMIT:
            gaps.append(f"skill_portfolio_package_overloaded:{skill_id}:{file_count}")
    duplicate_paths = {key: ids for key, ids in path_owners.items() if len(ids) > 1}
    duplicate_tokens = {
        key: ids for key, ids in token_owners.items() if len(ids) > INTENT_TOKEN_OWNER_LIMIT
    }
    for pattern, owners in sorted(duplicate_paths.items()):
        gaps.append(f"skill_portfolio_path_glob_duplicate:{pattern}:{','.join(owners)}")
    for token, owners in sorted(duplicate_tokens.items()):
        gaps.append(f"skill_portfolio_intent_token_overclaimed:{token}:{','.join(owners)}")
    novelty = _portfolio_novelty(route_owners)
    gaps.extend(cast("list[str]", novelty["required_gaps"]))
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "command_owner_count": {key: len(ids) for key, ids in sorted(command_owners.items())},
        "path_glob_owner_count": {key: len(ids) for key, ids in sorted(path_owners.items())},
        "intent_token_owner_count": {key: len(ids) for key, ids in sorted(token_owners.items())},
        "novelty": novelty,
        "required_gaps": gaps,
    }


def _portfolio_novelty(route_owners: dict[str, list[str]]) -> dict[str, object]:
    duplicates = {key: ids for key, ids in route_owners.items() if len(ids) > 1}
    gaps = [
        f"skill_portfolio_route_duplicate:{route}:{','.join(owners)}"
        for route, owners in sorted(duplicates.items())
    ]
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "route_owner_count": {key: len(ids) for key, ids in sorted(route_owners.items())},
        "duplicate_routes": {key: list(ids) for key, ids in sorted(duplicates.items())},
        "required_gaps": gaps,
    }


def portfolio_retirement(
    registry: dict[str, object],
    records: list[dict[str, object]],
    root: Path,
) -> dict[str, object]:
    """Ensure retired routes cannot remain active or leave a live carrier behind."""
    retired = registry.get("retired")
    retired_entries = retired if isinstance(retired, dict) else {}
    active_ids = {str(record["id"]) for record in records}
    gaps: list[str] = []
    for raw_skill_id, entry in sorted(retired_entries.items()):
        skill_id = str(raw_skill_id)
        if skill_id in active_ids:
            gaps.append(f"skill_retirement_active_duplicate:{skill_id}")
            continue
        if not isinstance(entry, dict):
            gaps.append(f"skill_retirement_invalid:{skill_id}")
            continue
        gaps.extend(
            f"skill_retirement_field_missing:{skill_id}:{field}"
            for field in ("reason", "retired_on", "kill_signal")
            if not str(entry.get(field) or "").strip()
        )
        path = str(entry.get("path") or "")
        if path and (root / path).exists():
            gaps.append(f"skill_retirement_live_path:{skill_id}:{path}")
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "retired": sorted(str(skill_id) for skill_id in retired_entries),
        "required_gaps": gaps,
    }
