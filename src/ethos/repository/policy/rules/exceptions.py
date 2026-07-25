"""Policy exceptions: validate and report on policy-exceptions.toml entries."""

from __future__ import annotations

import tomllib
from datetime import UTC
from datetime import date
from datetime import datetime
from typing import TYPE_CHECKING
from typing import cast

from ethos.contracts.rules import PolicyException
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path


def _exceptions_path(root: Path) -> Path:
    return root / "rules" / "ethos" / "policy-exceptions.toml"


def _is_product_root(root: Path) -> bool:
    return (root / "pyproject.toml").exists() and (root / "system" / "commands.toml").exists()


def date_or_none(value: str) -> date | None:
    """Parse an ISO-8601 date string, returning None if invalid."""
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def ttl_days_or_none(value: str) -> int | None:
    """Parse a TTL string like '30d' to an integer day count, returning None if invalid."""
    if not value.endswith("d"):
        return None
    raw = value.removesuffix("d")
    if not raw.isdigit():
        return None
    return int(raw)


def utc_calendar_day() -> str:
    """Return the current calendar day from the explicit UTC clock."""
    return datetime.now(UTC).date().isoformat()


def minimal_rule_skeleton(path: str) -> dict[str, object]:
    """Return a minimal rule skeleton dict for a given path glob."""
    return {
        "id": "custom.example",
        "owner": "team",
        "authority_ref": "docs/governance/example.md",
        "contract_ref": "docs/governance/example.md",
        "path_globs": [path] if path else [],
        "severity": "advisory",
        "required_gates": [],
        "stop_condition": "custom_rule_gap",
    }


def policy_exceptions_report(root: Path, *, today: str | None = None) -> dict[str, object]:
    """Validate and report on all entries in rules/ethos/policy-exceptions.toml."""
    path = _exceptions_path(root)
    if not path.exists():
        return {
            "ok": True,
            "owner": "rules/ethos/policy-exceptions.toml",
            "exceptions": [],
            "required_gaps": [],
        }
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {
            "ok": False,
            "owner": "rules/ethos/policy-exceptions.toml",
            "exceptions": [],
            "required_gaps": [f"policy_exception_parse_error:{exc}"],
        }
    exceptions = payload.get("exception", [])
    if not isinstance(exceptions, list):
        exceptions = []
    known_rules = cast(
        "dict[str, dict[str, object]]",
        {
            str(rule.get("id")): rule
            for rule in cast("list[object]", compile_rules(root)["rules"])
            if isinstance(rule, dict) and rule.get("id")
        },
    )
    known_rule_ids = set(known_rules)
    today_date = date_or_none(today or utc_calendar_day())
    normalized: list[dict[str, object]] = []
    gaps: list[str] = []
    for item in exceptions:
        if not isinstance(item, dict):
            gaps.append("policy_exception_malformed")
            continue
        record_result = _normalize_policy_exception_record(
            item,
            root=root,
            known_rules=known_rules,
            known_rule_ids=known_rule_ids,
            today_date=today_date,
        )
        normalized.append(cast("dict[str, object]", record_result["record"]))
        gaps.extend(cast("list[str]", record_result["gaps"]))
    return {
        "ok": not gaps,
        "owner": "rules/ethos/policy-exceptions.toml",
        "exceptions": normalized,
        "required_gaps": list(dict.fromkeys(gaps)),
    }


def _normalize_policy_exception_record(
    item: dict[str, object],
    *,
    root: Path,
    known_rules: dict[str, dict[str, object]],
    known_rule_ids: set[str],
    today_date: date | None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "id": str(item.get("id", "")),
        "rule_id": str(item.get("rule_id", "")),
        "scope": str(item.get("scope", "")),
        "owner": str(item.get("owner", "")),
        "approver": str(item.get("approver", "")),
        "reason": str(item.get("reason", "")),
        "evidence_ref": str(item.get("evidence_ref", "")),
        "created_at": str(item.get("created_at", "")),
        "expires_at": str(item.get("expires_at", "")),
        "status": str(item.get("status", "")),
        "digest": str(item.get("digest", "")),
    }
    if item.get("max_ttl"):
        record["max_ttl"] = str(item["max_ttl"])
    gaps: list[str] = []
    expected = _policy_exception_expected_digest(record)
    gaps.extend(_policy_exception_shape_gaps(record, expected=expected))
    gaps.extend(_policy_exception_rule_gaps(record, known_rules, known_rule_ids))
    gaps.extend(_policy_exception_scope_gaps(record, root=root, today_date=today_date))
    return {"record": {**record, "expected_digest": expected}, "gaps": gaps}


def _policy_exception_expected_digest(record: dict[str, object]) -> object:
    return PolicyException(
        id=str(record["id"]),
        rule_id=str(record["rule_id"]),
        scope=str(record["scope"]),
        owner=str(record["owner"]),
        approver=str(record["approver"]),
        reason=str(record["reason"]),
        evidence_ref=str(record["evidence_ref"]),
        created_at=str(record["created_at"]),
        expires_at=str(record["expires_at"]),
        status=str(record["status"]),
        max_ttl=str(record.get("max_ttl", "")),
    ).to_dict()["digest"]


def _policy_exception_shape_gaps(record: dict[str, object], *, expected: object) -> list[str]:
    gaps: list[str] = []
    validation = validate_schema_instance("policy-exception.schema.json", record)
    if not validation["ok"]:
        gaps.extend(
            f"policy_exception_schema_invalid:{record['id']}:{gap}"
            for gap in cast("list[object]", validation["required_gaps"])
        )
    if record["digest"] != expected:
        gaps.append(f"policy_exception_digest_mismatch:{record['id']}")
    return gaps


def _policy_exception_rule_gaps(
    record: dict[str, object],
    known_rules: dict[str, dict[str, object]],
    known_rule_ids: set[str],
) -> list[str]:
    rule_id = str(record["rule_id"])
    if rule_id not in known_rule_ids:
        return [f"policy_exception_unknown_rule:{record['id']}:{rule_id}"]
    if bool(known_rules[rule_id].get("non_waivable", False)):
        return [f"policy_exception_non_waivable_rule:{record['id']}:{rule_id}"]
    return []


def _policy_exception_scope_gaps(
    record: dict[str, object],
    *,
    root: Path,
    today_date: date | None,
) -> list[str]:
    gaps: list[str] = []
    scope_value = str(record["scope"])
    if (scope_value != "repository" and not scope_value.startswith("path:")) or (
        scope_value.startswith("path:") and not scope_value.removeprefix("path:").strip("/")
    ):
        gaps.append(f"policy_exception_scope_invalid:{record['id']}")
    evidence_ref = str(record["evidence_ref"])
    if evidence_ref and not (root / evidence_ref).exists():
        gaps.append(f"policy_exception_evidence_missing:{record['id']}:{evidence_ref}")
    created_at = date_or_none(str(record["created_at"]))
    expires_at = date_or_none(str(record["expires_at"]))
    gaps.extend(_policy_exception_date_gaps(record, created_at, expires_at, today_date))
    return gaps


def _policy_exception_date_gaps(
    record: dict[str, object],
    created_at: date | None,
    expires_at: date | None,
    today_date: date | None,
) -> list[str]:
    gaps: list[str] = []
    if created_at is None:
        gaps.append(f"policy_exception_date_invalid:{record['id']}:created_at")
    if expires_at is None:
        gaps.append(f"policy_exception_date_invalid:{record['id']}:expires_at")
    max_ttl = str(record.get("max_ttl", ""))
    if max_ttl:
        ttl_days = ttl_days_or_none(max_ttl)
        if ttl_days is None:
            gaps.append(f"policy_exception_ttl_invalid:{record['id']}")
        elif created_at and expires_at and (expires_at - created_at).days > ttl_days:
            gaps.append(f"policy_exception_ttl_exceeded:{record['id']}")
    if record["status"] == "active" and expires_at and today_date and expires_at < today_date:
        gaps.append(f"policy_exception_expired:{record['id']}")
    return gaps


def rules_docs_manifest_report(root: Path) -> dict[str, object]:
    """Report missing doc refs in authority_ref and contract_ref of compiled rules."""
    product_root = _is_product_root(root)
    refs = sorted(
        {
            str(ref)
            for rule in cast("list[object]", compile_rules(root)["rules"])
            if isinstance(rule, dict) and (product_root or rule.get("owner") != "ethos")
            for ref in (rule.get("authority_ref"), rule.get("contract_ref"))
            if isinstance(ref, str) and ref.endswith(".md")
        }
    )
    missing = [ref for ref in refs if not (root / ref).exists()]
    return {
        "ok": not missing,
        "generated_from": "compiled-rules",
        "refs": refs,
        "missing": missing,
        "required_gaps": [f"missing_doc_ref:{ref}" for ref in missing],
    }
