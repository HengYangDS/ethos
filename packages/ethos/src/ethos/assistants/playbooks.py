from __future__ import annotations

import fnmatch
import shlex
import tomllib
from pathlib import Path
from typing import Any

from ethos.assistants.skill_packages import DEFAULT_REQUIRED_SECTIONS
from ethos.assistants.skill_packages import validate_skill_markdown
from ethos.assistants.skill_packages import validate_skill_package_manifest
from ethos_core.contracts.skill_activation import normalize_skill_activation
from ethos_core.contracts.skill_activation import skill_registry_digest

PLAYBOOK_MODES = ("v2-strict",)


def _skills_root(root: Path) -> Path:
    return root / ".agents" / "skills"


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
    registry = normalize_skill_activation(payload, source=".agents/skills/activation.toml")
    registry["digest"] = skill_registry_digest(registry)
    records = []
    required_gaps = list(missing)
    advisory_gaps: list[str] = []
    v2_gaps: list[str] = []
    package_reports: list[dict[str, Any]] = []
    package_capabilities: list[dict[str, Any]] = []
    activation_version = int(registry.get("meta", {}).get("version") or 1)
    if activation_version < 2:
        v2_gaps.append(f"playbook_activation_unsupported_version:{activation_version}")
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
        v2_gaps.extend(_strict_record_gaps(record))
        if not path_gaps:
            quality = validate_skill_markdown(
                root,
                str(playbook_record["path"]),
                str(skill_id),
                DEFAULT_REQUIRED_SECTIONS,
            )
            v2_gaps.extend(str(gap) for gap in quality["required_gaps"])
        manifest_path = _manifest_path(record)
        package_report = validate_skill_package_manifest(root, manifest_path)
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
        v2_gaps.extend(_command_capability_gaps(record, package_report))
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
        "skills_root": ".agents/skills",
        "activation_path": ".agents/skills/activation.toml",
        "skills": [skill["id"] for skill in records],
        "records": records,
        "registry": registry,
        "coverage": _coverage(records),
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
        for record in report["records"]
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
    gaps = list(report["required_gaps"])
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
        "route_hints": {"registry_digest": report["registry"]["digest"]},
        "required_gaps": _dedupe(gaps),
        "advisory_gaps": list(report["advisory_gaps"]),
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
    subjects = [str(item).strip().lower() for item in record["subjects"]]
    if require_explicit_subject:
        return normalized in subjects
    return normalized in str(record["id"]).lower() or any(normalized in item for item in subjects)


def _coverage(records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "record_count": len(records),
        "path_glob_count": sum(len(record["path_globs"]) for record in records),
        "subjects": sorted({subject for record in records for subject in record["subjects"]}),
    }


def _select_for_changed_paths(
    records: list[dict[str, object]],
    changed_paths: tuple[str, ...],
) -> tuple[list[dict[str, object]], list[str]]:
    selected: list[dict[str, object]] = []
    matched_paths: set[str] = set()
    for record in records:
        path_globs = [str(item) for item in record["path_globs"]]
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


def _command_capability_gaps(
    record: dict[str, Any],
    package_report: dict[str, Any],
) -> list[str]:
    skill_id = str(record["id"] or "<missing>")
    capability_commands = [
        _command_key(item["command"])
        for item in package_report["capabilities"]
        if item.get("command")
    ]
    gaps: list[str] = []
    for command in record["commands"]:
        command_key = _command_key(_split_command(command))
        if not any(_command_covers(capability, command_key) for capability in capability_commands):
            gaps.append(f"skill_package_capability_missing_command:{skill_id}:{command}")
    return gaps


def _split_command(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _command_key(command: list[str]) -> tuple[str, ...]:
    return tuple(part for part in command if part != "--json")


def _command_covers(capability: tuple[str, ...], command: tuple[str, ...]) -> bool:
    return capability[: len(command)] == command


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
