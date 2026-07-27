from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.contracts.rules import PolicyException
from ethos.contracts.rules import Rule
from ethos.contracts.rules import RuleSet
from ethos.domain.plan import matching_rule_gates
from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.config import resolve_profile_stack
from ethos.repository.policy.rules.coverage import coverage_report
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path


def test_rule_contract_schemas_validate_minimal_payloads() -> None:
    rule = {
        "id": "starter.docs",
        "owner": "ethos",
        "authority_ref": "docs/start/quickstart.md",
        "contract_ref": "docs/start/quickstart.md",
        "path_globs": ["docs/**"],
        "severity": "advisory",
        "required_gates": ["docs-registry"],
        "stop_condition": "docs_registry_drift",
    }
    rule_set = {
        "schema_version": 1,
        "id": "starter",
        "profile_layers": ["generic"],
        "rules": [rule],
    }
    surface_coverage = {
        "ok": True,
        "coverage_tier": "starter",
        "covered_paths": ["docs/index.md"],
        "uncovered_paths": [],
        "matched_rules": [],
        "required_gaps": [],
    }
    rule_report = {
        "ok": True,
        "coverage_ok": True,
        "depth_ok": True,
        "exceptions_ok": True,
        "evidence_freshness_ok": True,
        "drift_ok": True,
        "required_gaps": [],
    }
    policy_exception = PolicyException(
        id="docs-waiver",
        rule_id="starter.docs",
        scope="repository",
        owner="ethos",
        approver="maintainer",
        reason="temporary docs migration",
        evidence_ref="evidence/example.md",
        created_at="2026-07-01",
        expires_at="2026-07-31",
    ).to_dict()
    assert validate_schema_instance("rule.schema.json", rule)["ok"] is True
    assert validate_schema_instance("rule-set.schema.json", rule_set)["ok"] is True
    assert validate_schema_instance("surface-coverage.schema.json", surface_coverage)["ok"]
    assert validate_schema_instance("rule-report.schema.json", rule_report)["ok"] is True
    assert validate_schema_instance("policy-exception.schema.json", policy_exception)["ok"]


def test_rule_contract_schema_rejects_missing_owner() -> None:
    payload = {
        "schema_version": 1,
        "id": "bad",
        "profile_layers": ["generic"],
        "rules": [
            {
                "id": "starter.docs",
                "authority_ref": "docs/start/quickstart.md",
                "contract_ref": "docs/start/quickstart.md",
                "path_globs": ["docs/**"],
                "severity": "advisory",
                "required_gates": ["docs-registry"],
                "stop_condition": "docs_registry_drift",
            }
        ],
    }

    validation = validate_schema_instance("rule-set.schema.json", payload)

    assert validation["ok"] is False
    assert validation["required_gaps"]


def test_contract_dataclasses_serialize_to_schema_payloads() -> None:
    rule = Rule(
        id="custom.docs",
        owner="docs-team",
        authority_ref="docs/governance/docs.md",
        contract_ref="docs/governance/docs.md",
        path_globs=("docs/**",),
        severity="advisory",
        required_gates=("docs-registry",),
        stop_condition="docs_gap",
    )
    rule_set = RuleSet(id="custom", profile_layers=("generic",), rules=(rule,))
    assert validate_schema_instance("rule-set.schema.json", rule_set.to_dict())["ok"]


def test_compile_rules_rejects_v1_keys_without_normalization(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[[rule]]
id = "legacy.docs"
risk = "docs"
paths = ["docs/**"]
requires = ["docs-registry"]
evidence = ["governance-proof"]
""".lstrip(),
        encoding="utf-8",
    )

    compiled = compile_rules(tmp_path)
    checked = rules_check_report(tmp_path)

    assert any(
        gap.startswith("rule_schema_invalid:legacy.docs:") for gap in compiled["compile_gaps"]
    )
    assert checked["ok"] is False
    assert any(
        gap.startswith("rule_schema_invalid:legacy.docs:") for gap in checked["required_gaps"]
    )


def test_noncanonical_profile_fails_closed_without_alias_normalization() -> None:
    profiles, gaps = resolve_profile_stack({"profiles": {"active": ["python-package"]}})

    assert profiles == ["generic"]
    assert gaps == ["rules_profile_invalid:unknown_profile:python-package"]


def test_unknown_rule_gate_is_a_compile_gap_without_synthetic_plan_gate(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[[rule]]
id = "custom.notes"
owner = "docs-team"
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["notes/**"]
severity = "advisory"
required_gates = ["missing-gate"]
stop_condition = "notes_gap"
""".lstrip(),
        encoding="utf-8",
    )

    compiled = compile_rules(tmp_path)
    matched_rules, required_gates, plan_gaps = matching_rule_gates(tmp_path, ("notes",))
    coverage = coverage_report(tmp_path, changed_paths=("notes",))

    assert "unknown_rule_gate:custom.notes:missing-gate" in compiled["compile_gaps"]
    assert matched_rules == [
        {
            "id": "custom.notes",
            "subject": "",
            "matched_paths": ["notes"],
            "required_gates": [],
            "evidence_requirements": [],
        }
    ]
    assert required_gates == []
    assert "unknown_rule_gate:custom.notes:missing-gate" in plan_gaps
    assert coverage["covered_paths"] == ["notes"]
    assert coverage["matched_rules"][0]["required_gates_detail"] == []


def test_compiled_rule_matching_treats_trailing_glob_as_its_directory(
    tmp_path: Path,
) -> None:
    matched_rules, _, plan_gaps = matching_rule_gates(tmp_path, ("docs",))
    coverage = coverage_report(tmp_path, changed_paths=("docs",))

    assert plan_gaps == []
    assert any(rule["id"] == "starter.docs" for rule in matched_rules)
    assert coverage["covered_paths"] == ["docs"]
    assert any(match["rule_id"] == "starter.docs" for match in coverage["matched_rules"])
