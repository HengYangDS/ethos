from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.coverage import coverage_report


def test_rules_check_passes_for_starter_profile(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        '[profiles]\nactive = ["generic"]\n',
        encoding="utf-8",
    )

    report = rules_check_report(tmp_path)

    assert report["ok"] is True
    assert report["coverage_tier"] == "starter"
    assert report["required_gaps"] == []
    assert report["profile_stack"] == ["generic"]


def test_rules_check_blocks_malformed_and_invalid_config(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    rules_path.write_text('[profiles\nactive = ["generic"]\n', encoding="utf-8")

    malformed = rules_check_report(tmp_path)

    assert malformed["ok"] is False
    assert "rules_config_parse_error" in malformed["required_gaps"][0]

    rules_path.write_text(
        """
[profiles]
active = ["generic"]

[[rule]]
id = "bad"
path_globs = []
severity = "fatal"
required_gates = []
authority_ref = ".ethos/rules.toml"
contract_ref = ".ethos/rules.toml"
stop_condition = "bad_rule"
""".lstrip(),
        encoding="utf-8",
    )

    invalid = rules_check_report(tmp_path)

    assert invalid["ok"] is False
    assert any(gap.startswith("rule_schema_invalid:bad:") for gap in invalid["required_gaps"])


def test_compile_rules_reports_invalid_profiles_active(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        '[profiles]\nactive = "python"\n',
        encoding="utf-8",
    )

    compiled = compile_rules(tmp_path)

    assert compiled["profile_stack"] == ["generic"]
    assert compiled["compile_gaps"] == ["rules_profile_invalid:active_must_be_string_array"]


def test_legacy_v1_rules_normalize_to_canonical_rule_ir(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[[rule]]
id = "legacy.docs"
risk = "docs_drift"
paths = ["docs/**"]
requires = ["docs-registry"]
evidence = ["docs evidence"]
""".lstrip(),
        encoding="utf-8",
    )

    compiled = compile_rules(tmp_path)
    coverage = coverage_report(tmp_path, changed_paths=("docs/index.md",))

    assert not [
        gap for gap in compiled["compile_gaps"] if str(gap).startswith("rule_schema_invalid")
    ]
    legacy_rule = next(rule for rule in compiled["rules"] if rule["id"] == "legacy.docs")
    assert legacy_rule["owner"] == "repo-local"
    assert legacy_rule["authority_ref"] == ".ethos/rules.toml"
    assert legacy_rule["contract_ref"] == ".ethos/rules.toml"
    assert legacy_rule["subject"] == "docs_drift"
    assert legacy_rule["severity"] == "advisory"
    assert legacy_rule["stop_condition"] == "docs_drift"
    assert legacy_rule["path_globs"] == ["docs/**"]
    assert legacy_rule["required_gates"] == ["docs-registry"]
    assert legacy_rule["evidence_requirements"] == ["docs evidence"]
    assert any(match["rule_id"] == "legacy.docs" for match in coverage["matched_rules"])


def test_compile_rules_is_deterministic(tmp_path: Path) -> None:
    first = compile_rules(tmp_path)
    second = compile_rules(tmp_path)

    assert first["compiled_policy_digest"] == second["compiled_policy_digest"]
    assert first["rule_set_digest"] == second["rule_set_digest"]
    assert first["rules"]


def test_coverage_report_names_uncovered_paths(tmp_path: Path) -> None:
    report = coverage_report(tmp_path, changed_paths=("unknown/file.xyz",))

    assert report["ok"] is False
    assert report["uncovered_paths"] == ["unknown/file.xyz"]
    assert report["next_action_contract"]
    assert "ethos rules migrate --dry-run" not in report["next_action_contract"]


def test_starter_docs_cover_package_and_distribution_readmes(tmp_path: Path) -> None:
    report = coverage_report(
        tmp_path,
        changed_paths=(
            "packages/ethos-core/README.md",
            "distributions/npm/README.md",
        ),
    )

    assert report["ok"] is True
    assert report["uncovered_paths"] == []
    assert {match["rule_id"] for match in report["matched_rules"]} == {"starter.docs"}
