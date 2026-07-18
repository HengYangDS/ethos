"""Rules check and layered coverage-depth reporting."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.config import _legacy_state
from ethos.repository.policy.rules.config import _load_rules_config
from ethos.repository.policy.rules.exceptions import policy_exceptions_report
from ethos.repository.policy.rules.exceptions import rules_docs_manifest_report

if TYPE_CHECKING:
    from pathlib import Path


def rules_check_report(root: Path) -> dict[str, object]:
    """Report rule-set integrity: parse errors, duplicate ids, unknown gates, owners."""
    config = _load_rules_config(root)
    compiled = compile_rules(root)
    legacy = _legacy_state(root)
    required_gaps: list[str] = []
    if "_parse_error" in config:
        required_gaps.append(f"rules_config_parse_error:{config['_parse_error']}")
    required_gaps.extend(str(gap) for gap in cast("list[object]", compiled["compile_gaps"]))
    rule_ids: set[str] = set()
    gate_definitions = cast("dict[str, object]", compiled["gate_definitions"])
    for rule in cast("list[dict[str, object]]", compiled["rules"]):
        if not isinstance(rule, dict):
            continue
        rule_id = str(rule.get("id", ""))
        if rule_id in rule_ids:
            required_gaps.append(f"duplicate_rule_id:{rule_id}")
        rule_ids.add(rule_id)
        if not rule.get("owner"):
            required_gaps.append(f"rule_missing_owner:{rule_id}")
        for gate in cast("list[object]", rule.get("required_gates", [])):
            if str(gate) not in gate_definitions:
                required_gaps.append(f"unknown_rule_gate:{rule_id}:{gate}")
    return {
        "ok": not required_gaps,
        "profile_stack": compiled["profile_stack"],
        "coverage_tier": compiled["coverage_tier"],
        "strict_enabled_source": "profile" if compiled["coverage_tier"] == "strict" else "",
        "resolved_rules": [
            rule["id"]
            for rule in cast("list[dict[str, object]]", compiled["rules"])
            if isinstance(rule, dict)
        ],
        "rule_set_digest": compiled["rule_set_digest"],
        "compiled_policy_digest": compiled["compiled_policy_digest"],
        "source_refs": compiled["source_refs"],
        "legacy": legacy,
        "required_gaps": required_gaps,
        "next_action_contract": []
        if not required_gaps
        else ["ethos rules explain <gap>", "ethos rules migrate --apply"],
    }


def rules_layer_report(root: Path) -> dict[str, object]:
    """Report layered rule coverage depth: subject/contract/transition/evidence/stop tiers."""
    check = rules_check_report(root)
    exceptions = policy_exceptions_report(root)
    docs_manifest = rules_docs_manifest_report(root)
    required_gaps = list(cast("list[str]", check["required_gaps"]))
    required_gaps.extend(
        f"policy_exception:{gap}" for gap in cast("list[object]", exceptions["required_gaps"])
    )
    required_gaps.extend(
        f"rules_docs_manifest:{gap}" for gap in cast("list[object]", docs_manifest["required_gaps"])
    )
    strict = check["coverage_tier"] == "strict"
    subjects = {
        str(rule.get("subject", ""))
        for rule in cast("list[object]", compile_rules(root)["rules"])
        if isinstance(rule, dict)
    }
    depth_tiers = {
        "subject": any(subjects),
        "contract": "contract" in subjects,
        "transition": "transition" in subjects,
        "evidence": "evidence" in subjects,
        "stop": "stop" in subjects,
    }
    depth_gaps: list[str] = []
    if strict:
        missing = sorted(
            subject
            for subject in ("contract", "transition", "evidence", "stop")
            if not depth_tiers[subject]
        )
        if missing:
            depth_gaps.append("rules_strict_subject_coverage_missing")
            depth_gaps.extend(f"rules_strict_missing_subject:{subject}" for subject in missing)
    required_gaps.extend(depth_gaps)
    coverage_ok = not check["required_gaps"]
    depth_ok = not depth_gaps
    exceptions_ok = bool(exceptions["ok"])
    docs_manifest_ok = bool(docs_manifest["ok"])
    evidence_freshness_ok = not any("evidence" in gap for gap in required_gaps)
    drift_ok = not any("digest_mismatch" in gap for gap in required_gaps)
    return {
        "ok": (
            coverage_ok
            and depth_ok
            and exceptions_ok
            and docs_manifest_ok
            and evidence_freshness_ok
            and drift_ok
        ),
        "coverage_ok": coverage_ok,
        "depth_ok": depth_ok,
        "exceptions_ok": exceptions_ok,
        "docs_manifest_ok": docs_manifest_ok,
        "evidence_freshness_ok": evidence_freshness_ok,
        "drift_ok": drift_ok,
        "strict": strict,
        "depth_tiers": depth_tiers,
        "required_gaps": list(dict.fromkeys(required_gaps)),
        "check": check,
        "exceptions": exceptions,
        "docs_manifest": docs_manifest,
    }
