"""Validate rule models and deterministic matching without redundant projections."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomli_w
from pydantic import ValidationError

from ethos.contracts.rules import Rule
from ethos.contracts.rules import RuleSet
from ethos.domain.plan import matching_rule_gates
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.config import resolve_profile_stack
from ethos.repository.policy.schema import validate_schema_instance

if TYPE_CHECKING:
    from pathlib import Path


def _rule(**updates: object) -> dict[str, object]:
    return {
        "id": "custom.docs",
        "owner": "docs-team",
        "authority_ref": "docs/governance/docs.md",
        "contract_ref": "docs/governance/docs.md",
        "path_globs": ["docs/**"],
        "severity": "advisory",
        "required_gates": ["docs-registry"],
        "stop_condition": "docs_gap",
    } | updates


def _write_rules(root: Path, *rules: dict[str, object], **extra: object) -> None:
    path = root / ".ethos/rules.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(tomli_w.dumps({"rule": list(rules)} | extra), encoding="utf-8")


def test_rule_contract_schemas_validate_minimal_payloads() -> None:
    assert validate_schema_instance("rule.schema.json", _rule())["verdict"] == "pass"


def test_rule_contracts_serialize_to_schema_payloads_without_handwritten_conversion() -> None:
    rule = Rule.model_validate(_rule())
    rule_set = RuleSet(id="custom", profile_layers=("generic",), rules=(rule,))
    assert rule_set.model_dump(mode="json") == {
        "schema_version": 1,
        "id": "custom",
        "profile_layers": ["generic"],
        "rules": [_rule(version=1)],
    }
    with pytest.raises(ValidationError):
        Rule.model_validate(_rule(non_waivable=1))


@pytest.mark.parametrize(
    "updates", [{}, {"owner": "other"}, {"version": 2}, {"non_waivable": False}]
)
def test_rule_set_rejects_duplicate_resolved_identity(updates: dict[str, object]) -> None:
    """A version or native-owner difference cannot create two active meanings for one id."""
    first = Rule.model_validate(_rule(non_waivable=True))
    second = Rule.model_validate(_rule(non_waivable=True) | updates)
    with pytest.raises(ValidationError, match=r"rule_identity_conflict:custom\.docs"):
        RuleSet(id="custom", profile_layers=("generic",), rules=(first, second))


@pytest.mark.parametrize("identity", ["custom.docs", "starter.governance"])
def test_rule_conflict_reaches_selection_without_partial_policy(
    tmp_path: Path, identity: str
) -> None:
    """Both repository duplicates and baseline collisions block the real compiler consumer."""
    first = _rule(id=identity, non_waivable=True)
    records = (first, _rule(id=identity)) if identity == "custom.docs" else (first,)
    _write_rules(tmp_path, *records)
    expected = [f"rule_identity_conflict:{identity}"]
    compiled = compile_rules(tmp_path)
    assert compiled["compile_gaps"] == expected
    assert compiled["rules"] == []
    assert matching_rule_gates(tmp_path, ("docs",)) == ([], [], expected)


def test_compiled_rule_projection_omits_unconsumed_digests(tmp_path: Path) -> None:
    compiled = compile_rules(tmp_path)
    assert "rule_set_digest" not in compiled
    assert "compiled_policy_digest" not in compiled


def test_compile_rules_rejects_v1_keys_without_normalization(tmp_path: Path) -> None:
    _write_rules(
        tmp_path,
        {
            "id": "legacy.docs",
            "risk": "docs",
            "paths": ["docs/**"],
            "requires": ["docs-registry"],
            "evidence": ["governance-proof"],
        },
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
    _write_rules(
        tmp_path,
        _rule(
            id="custom.notes",
            path_globs=["notes/**"],
            required_gates=["missing-gate"],
            stop_condition="notes_gap",
        ),
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
    _write_rules(
        tmp_path,
        _rule(
            id="custom.notes",
            path_globs=["notes/**"],
            severity="blocking",
            required_gates=["shadow"],
            stop_condition="notes_gap",
        ),
        gates={"shadow": {"command": "python shadow.py", "blocking": True}},
    )
    compiled = compile_rules(tmp_path)
    assert "shadow" not in compiled["gate_definitions"]
    assert "unknown_rule_gate:custom.notes:shadow" in compiled["compile_gaps"]


def test_compiled_rule_matching_treats_trailing_glob_as_its_directory(tmp_path: Path) -> None:
    _write_rules(tmp_path, _rule(id="custom.first"), _rule(id="custom.second"))
    matched_rules, required_gates, plan_gaps = matching_rule_gates(tmp_path, ("docs",))
    assert plan_gaps == []
    assert {rule["id"] for rule in matched_rules} == {
        "starter.docs",
        "custom.first",
        "custom.second",
    }
    assert [gate["id"] for gate in required_gates] == ["docs-registry"]
