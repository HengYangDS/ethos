from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path
from typing import Any
from typing import cast

from ethos.assistants.playbook_utils import _command_capability_gaps
from ethos.assistants.skill_packages import DEFAULT_REQUIRED_SECTIONS
from ethos.assistants.skill_packages import validate_skill_markdown
from ethos.assistants.skill_packages import validate_skill_package_manifest
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_relative_root
from ethos.repository.profile import profile_root
from ethos.repository.profile import table_version
from ethos_core.contracts.skill_activation import normalize_skill_activation
from ethos_core.contracts.skill_activation import skill_registry_digest

PLAYBOOK_MODES = ("v2-strict",)
PLAYBOOK_ACTIVATION_VERSION = 2
SKILL_PACKAGE_FILE_LIMIT = 6
INTENT_TOKEN_OWNER_LIMIT = 2


def _skills_root(root: Path) -> Path:
    return profile_root(root, "agent_skills")


def _activation_path(root: Path) -> Path:
    return _skills_root(root) / "activation.toml"


def _load_activation(root: Path) -> tuple[dict[str, Any], list[str]]:
    path = _activation_path(root)
    if not path.exists():
        return {}, [".agents/skills/activation.toml"]
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}, [".agents/skills/activation.toml:invalid_toml"]
    return payload, []


def playbooks_report(root: Path, *, mode: str = "v2-strict") -> dict[str, object]:
    selected_mode = _mode(mode)
    skills_root = _skills_root(root)
    payload, missing = _load_activation(root)
    transition_adopter = _transition_adopter_activation(root, payload)
    registry = normalize_skill_activation(payload, source=".agents/skills/activation.toml")
    if transition_adopter:
        registry = _transition_registry(
            payload,
            skills_root=profile_relative_root(root, "agent_skills"),
        )
    registry["digest"] = skill_registry_digest(registry)
    required_gaps = list(missing)
    advisory_gaps: list[str] = []
    activation_version = int(registry.get("meta", {}).get("version") or 1)
    collected = _collect_playbook_records(
        root,
        registry=registry,
        transition_adopter=transition_adopter,
    )
    records = collected["records"]
    package_reports = collected["package_reports"]
    package_capabilities = collected["package_capabilities"]
    required_gaps.extend(collected["required_gaps"])
    v2_gaps = list(collected["v2_gaps"])
    if activation_version < PLAYBOOK_ACTIVATION_VERSION and not transition_adopter:
        v2_gaps.append(f"playbook_activation_unsupported_version:{activation_version}")
    portfolio_coverage = (
        _empty_portfolio_coverage()
        if transition_adopter
        else _portfolio_coverage(registry.get("coverage", {}), records)
    )
    portfolio_design = (
        _empty_portfolio_design()
        if transition_adopter
        else _portfolio_design(records, package_reports)
    )
    v2_gaps.extend(str(gap) for gap in cast("list[object]", portfolio_coverage["required_gaps"]))
    v2_gaps.extend(str(gap) for gap in cast("list[object]", portfolio_design["required_gaps"]))
    if skills_root.exists() and not (skills_root / "README.md").exists():
        required_gaps.append(".agents/skills/README.md")
    if not skills_root.exists():
        required_gaps.append(".agents/skills")
    required_gaps.extend(_dedupe(v2_gaps))
    score = _skills_v2_score(required_gaps, advisory_gaps, selected_mode)
    return {
        "ok": not required_gaps,
        "schema_version": 2,
        "mode": selected_mode,
        "skills_root": profile_relative_root(root, "agent_skills"),
        "activation_path": (
            Path(profile_relative_root(root, "agent_skills")) / "activation.toml"
        ).as_posix(),
        "skills": [skill["id"] for skill in records],
        "records": records,
        "registry": registry,
        "coverage": _coverage(records),
        "portfolio_coverage": portfolio_coverage,
        "portfolio_design": portfolio_design,
        "package_quality": {
            "ok": not any(report["required_gaps"] for report in package_reports),
            "packages": package_reports,
            "capabilities": package_capabilities,
        },
        "v2_compliance": {
            "ok": not v2_gaps,
            "score": score,
            "max_score": 5,
            "required_gaps": _dedupe(v2_gaps),
        },
        "advisory_gaps": _dedupe(advisory_gaps),
        "required_gaps": _dedupe(required_gaps),
    }


def _collect_playbook_records(
    root: Path,
    *,
    registry: dict[str, Any],
    transition_adopter: bool,
) -> dict[str, Any]:
    records = []
    required_gaps: list[str] = []
    v2_gaps: list[str] = []
    package_reports: list[dict[str, Any]] = []
    package_capabilities: list[dict[str, Any]] = []
    for record in registry["records"]:
        playbook_record = _playbook_record(record)
        records.append(playbook_record)
        skill_id = playbook_record["id"]
        if not skill_id:
            required_gaps.append("skill_missing_id")
            continue
        path_gaps = _record_path_gaps(root, str(skill_id), str(playbook_record["path"]))
        if path_gaps:
            v2_gaps.extend(path_gaps)
        elif not (root / str(playbook_record["path"])).exists():
            required_gaps.append(f"skill_missing_file:{skill_id}")
        if not transition_adopter:
            v2_gaps.extend(_strict_record_gaps(record))
        if not path_gaps and not transition_adopter:
            quality = validate_skill_markdown(
                root,
                str(playbook_record["path"]),
                str(skill_id),
                DEFAULT_REQUIRED_SECTIONS,
            )
            v2_gaps.extend(str(gap) for gap in quality["required_gaps"])
        manifest_path = _manifest_path(record)
        package_report = (
            _transition_package_report(str(skill_id), manifest_path)
            if transition_adopter
            else validate_skill_package_manifest(root, manifest_path)
        )
        package_reports.append(package_report)
        package_capabilities.extend(package_report["capabilities"])
        v2_gaps.extend(str(gap) for gap in package_report["required_gaps"])
        v2_gaps.extend(
            _package_entrypoint_gaps(
                root,
                str(skill_id),
                str(playbook_record["path"]),
                package_report,
            )
        )
        if not transition_adopter:
            v2_gaps.extend(_command_capability_gaps(record, package_report))
    return {
        "records": records,
        "required_gaps": required_gaps,
        "v2_gaps": v2_gaps,
        "package_reports": package_reports,
        "package_capabilities": package_capabilities,
    }


def _transition_adopter_activation(root: Path, payload: dict[str, Any]) -> bool:
    profile = load_repository_profile(root)
    return profile.exists and table_version(payload) < PLAYBOOK_ACTIVATION_VERSION


def _transition_registry(payload: dict[str, Any], *, skills_root: str) -> dict[str, Any]:
    records = []
    for item in payload.get("skill", []):
        if not isinstance(item, dict):
            continue
        skill_id = str(item.get("id") or item.get("name") or "")
        path = str(item.get("path") or (Path(skills_root) / skill_id / "SKILL.md").as_posix())
        subjects = [str(item) for item in item.get("subjects", []) if str(item)]
        if not subjects:
            subjects = ["changed-scope", skill_id]
        records.append(
            {
                "id": skill_id,
                "path": path,
                "route_subjects": subjects,
                "activation": {"path_globs": list(item.get("path_globs", []))},
                "routing": {"intent_tokens": list(item.get("intent_tokens", []))},
                "obligations": {
                    "pre_reads": list(item.get("pre_reads", [])),
                    "post_checks": list(item.get("post_checks", [])),
                },
                "relations": {"may_coactivate": list(item.get("may_coactivate", []))},
                "commands": list(item.get("commands", [])),
                "boundary": "adopter-transition-projection",
                "primary_subject": subjects[0],
                "operation": "route",
                "authority": "adopter",
                "lifecycle": "active",
                "package_manifest": "",
            }
        )
    return {
        "meta": dict(payload.get("meta", {})),
        "records": records,
        "coverage": {},
    }


def _transition_package_report(skill_id: str, manifest_path: str) -> dict[str, Any]:
    return {
        "ok": True,
        "id": skill_id,
        "manifest": manifest_path,
        "entrypoint": "",
        "files": [],
        "capabilities": [],
        "required_gaps": [],
    }


def _empty_portfolio_coverage() -> dict[str, object]:
    return {
        "ok": True,
        "contract": {"required_primary_subjects": [], "single_owner_subjects": []},
        "owners": {},
        "required_gaps": [],
    }


def _empty_portfolio_design() -> dict[str, object]:
    return {
        "ok": True,
        "command_owner_count": {},
        "path_glob_owner_count": {},
        "intent_token_owner_count": {},
        "required_gaps": [],
    }


def route_playbook(
    root: Path,
    subject: str,
    *,
    require_explicit_subject: bool = False,
    mode: str = "v2-strict",
    changed_paths: tuple[str, ...] = (),
) -> dict[str, object]:
    report = playbooks_report(root, mode=mode)
    normalized = subject.strip().lower()
    changed = subject == "changed-scope"
    selected = [
        record
        for record in cast("list[dict[str, object]]", report["records"])
        if _matches_route_subject(
            record,
            normalized,
            require_explicit_subject=require_explicit_subject,
        )
    ]
    unmatched_paths: list[str] = []
    if changed:
        if changed_paths:
            selected, unmatched_paths = _select_for_changed_paths(selected, changed_paths)
        else:
            selected = []
    gaps = list(cast("list[str]", report["required_gaps"]))
    if not selected and not (changed and not changed_paths):
        gaps.append(f"playbook_route_missing:{subject}")
    gaps.extend(f"playbook_changed_path_unmatched:{path}" for path in unmatched_paths)
    return {
        "ok": not gaps,
        "schema_version": 2,
        "mode": report["mode"],
        "subject": subject,
        "changed": changed,
        "changed_paths": list(changed_paths),
        "selected": selected,
        "unmatched_paths": unmatched_paths,
        "route_hints": {"registry_digest": cast("dict[str, object]", report["registry"])["digest"]},
        "required_gaps": _dedupe(gaps),
        "advisory_gaps": list(cast("list[str]", report["advisory_gaps"])),
        "skills_root": report["skills_root"],
    }


def _playbook_record(record: dict[str, Any]) -> dict[str, object]:
    return {
        "id": record["id"],
        "path": record["path"],
        "subjects": list(record["route_subjects"]),
        "path_globs": list(record["activation"]["path_globs"]),
        "intent_tokens": list(record["routing"]["intent_tokens"]),
        "pre_reads": list(record["obligations"]["pre_reads"]),
        "post_checks": list(record["obligations"]["post_checks"]),
        "may_coactivate": list(record["relations"]["may_coactivate"]),
        "commands": list(record["commands"]),
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
    if not record["commands"]:
        gaps.append(f"playbook_skill_missing_commands:{skill_id}")
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


def _matches_route_subject(
    record: dict[str, object],
    normalized: str,
    *,
    require_explicit_subject: bool,
) -> bool:
    subjects = [str(item).strip().lower() for item in cast("list[str]", record["subjects"])]
    if require_explicit_subject:
        return normalized in subjects
    return normalized in str(record["id"]).lower() or any(normalized in item for item in subjects)


def _coverage(records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "record_count": len(records),
        "path_glob_count": sum(len(cast("list[str]", record["path_globs"])) for record in records),
        "subjects": sorted(
            {subject for record in records for subject in cast("list[str]", record["subjects"])}
        ),
    }


def _portfolio_coverage(
    coverage_contract: object,
    records: list[dict[str, object]],
) -> dict[str, object]:
    contract = coverage_contract if isinstance(coverage_contract, dict) else {}
    required_subjects = _dedupe(_coverage_subjects(contract.get("required_primary_subjects")))
    single_owner_subjects = _dedupe(
        [
            *required_subjects,
            *_coverage_subjects(contract.get("single_owner_subjects")),
        ]
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
        "ok": not gaps,
        "contract": {
            "required_primary_subjects": required_subjects,
            "single_owner_subjects": single_owner_subjects,
        },
        "owners": {subject: list(ids) for subject, ids in sorted(owners.items())},
        "required_gaps": gaps,
    }


def _portfolio_design(
    records: list[dict[str, object]],
    package_reports: list[dict[str, Any]],
) -> dict[str, object]:
    gaps: list[str] = []
    command_owners: dict[str, list[str]] = {}
    path_owners: dict[str, list[str]] = {}
    token_owners: dict[str, list[str]] = {}
    package_by_id = {str(report.get("id") or ""): report for report in package_reports}
    for record in records:
        skill_id = str(record["id"])
        subjects = [str(item) for item in cast("list[str]", record["subjects"])]
        if str(record["primary_subject"]) not in subjects:
            gaps.append(f"skill_portfolio_primary_subject_not_routed:{skill_id}")
        for command in cast("list[str]", record["commands"]):
            command_owners.setdefault(command, []).append(skill_id)
        for pattern in cast("list[str]", record["path_globs"]):
            path_owners.setdefault(pattern, []).append(skill_id)
        for token in cast("list[str]", record["intent_tokens"]):
            token_owners.setdefault(token, []).append(skill_id)
        package = package_by_id.get(skill_id, {})
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
    return {
        "ok": not gaps,
        "command_owner_count": {key: len(ids) for key, ids in sorted(command_owners.items())},
        "path_glob_owner_count": {key: len(ids) for key, ids in sorted(path_owners.items())},
        "intent_token_owner_count": {key: len(ids) for key, ids in sorted(token_owners.items())},
        "required_gaps": gaps,
    }


def _coverage_subjects(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _select_for_changed_paths(
    records: list[dict[str, object]],
    changed_paths: tuple[str, ...],
) -> tuple[list[dict[str, object]], list[str]]:
    selected: list[dict[str, object]] = []
    matched_paths: set[str] = set()
    for record in records:
        path_globs = [str(item) for item in cast("list[str]", record["path_globs"])]
        matches = [
            path
            for path in changed_paths
            if any(fnmatch.fnmatch(path, pattern) for pattern in path_globs)
        ]
        if not matches:
            continue
        enriched = dict(record)
        enriched["matched_paths"] = matches
        enriched["matched_globs"] = [
            pattern
            for pattern in path_globs
            if any(fnmatch.fnmatch(path, pattern) for path in matches)
        ]
        selected.append(enriched)
        matched_paths.update(matches)
    return selected, [path for path in changed_paths if path not in matched_paths]


def _skills_v2_score(required: list[str], advisory: list[str], mode: str) -> int:
    gaps = required
    return max(0, 5 - min(5, len(_dedupe(gaps))))


def _mode(mode: str) -> str:
    if mode not in PLAYBOOK_MODES:
        msg = f"unsupported playbook mode: {mode}"
        raise ValueError(msg)
    return mode


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
