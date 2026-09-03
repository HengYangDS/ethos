from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ethos.contracts.rules import Rule
from ethos.contracts.rules import RuleSet
from ethos.domain.plan import matching_rule_gates
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.config import resolve_profile_stack
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path


def test_rule_contract_schemas_validate_minimal_payloads() -> None:
    rule = {
        "id": "starter.docs",
        "owner": "ethos",
        "authority_ref": "docs/guides/quickstart.md",
        "contract_ref": "docs/guides/quickstart.md",
        "path_globs": ["docs/**"],
        "severity": "advisory",
        "required_gates": ["docs-registry"],
        "stop_condition": "docs_registry_drift",
    }
    assert validate_schema_instance("rule.schema.json", rule)["verdict"] == "pass"


def test_rule_contracts_serialize_to_schema_payloads_without_handwritten_conversion() -> None:
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
    payload = rule_set.model_dump(mode="json")
    assert payload == {
        "schema_version": 1,
        "id": "custom",
        "profile_layers": ["generic"],
        "rules": [
            {
                "id": "custom.docs",
                "owner": "docs-team",
                "authority_ref": "docs/governance/docs.md",
                "contract_ref": "docs/governance/docs.md",
                "path_globs": ["docs/**"],
                "severity": "advisory",
                "required_gates": ["docs-registry"],
                "stop_condition": "docs_gap",
                "version": 1,
            }
        ],
    }
    with pytest.raises(ValidationError):
        Rule(
            id="invalid",
            owner="docs-team",
            authority_ref="docs/governance/docs.md",
            contract_ref="docs/governance/docs.md",
            path_globs=("docs/**",),
            severity="advisory",
            required_gates=("docs-registry",),
            stop_condition="docs_gap",
            non_waivable=1,
        )


def test_compiled_rule_projection_omits_unconsumed_digests(tmp_path: Path) -> None:
    compiled = compile_rules(tmp_path)

    assert "rule_set_digest" not in compiled
    assert "compiled_policy_digest" not in compiled


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
    assert any(
        gap.startswith("rule_schema_invalid:legacy.docs:") for gap in compiled["compile_gaps"]
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


def test_rules_cannot_define_parallel_gate_commands(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[gates.shadow]
command = "python shadow.py"
blocking = true

[[rule]]
id = "custom.notes"
owner = "docs-team"
authority_ref = "docs/governance/docs.md"
contract_ref = "docs/governance/docs.md"
path_globs = ["notes/**"]
severity = "blocking"
required_gates = ["shadow"]
stop_condition = "notes_gap"
""".lstrip(),
        encoding="utf-8",
    )

    compiled = compile_rules(tmp_path)

    assert "shadow" not in compiled["gate_definitions"]
    assert "unknown_rule_gate:custom.notes:shadow" in compiled["compile_gaps"]


def test_compiled_rule_matching_treats_trailing_glob_as_its_directory(
    tmp_path: Path,
) -> None:
    matched_rules, _, plan_gaps = matching_rule_gates(tmp_path, ("docs",))

    assert plan_gaps == []
    assert any(rule["id"] == "starter.docs" for rule in matched_rules)
