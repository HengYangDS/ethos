from __future__ import annotations

from typing import Any
from typing import cast

SKILL_PACKAGE_FILE_LIMIT = 6
INTENT_TOKEN_OWNER_LIMIT = 2


def empty_portfolio_coverage() -> dict[str, object]:
    return {
        "ok": True,
        "contract": {"required_primary_subjects": [], "single_owner_subjects": []},
        "owners": {},
        "required_gaps": [],
    }


def empty_portfolio_design() -> dict[str, object]:
    return {
        "ok": True,
        "command_owner_count": {},
        "path_glob_owner_count": {},
        "intent_token_owner_count": {},
        "required_gaps": [],
    }


def portfolio_coverage(
    coverage_contract: object,
    records: list[dict[str, object]],
) -> dict[str, object]:
    contract = coverage_contract if isinstance(coverage_contract, dict) else {}
    required_subjects = dedupe(coverage_subjects(contract.get("required_primary_subjects")))
    single_owner_subjects = dedupe(
        [
            *required_subjects,
            *coverage_subjects(contract.get("single_owner_subjects")),
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


def portfolio_design(
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


def coverage_subjects(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
