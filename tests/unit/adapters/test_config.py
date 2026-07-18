from __future__ import annotations

from pathlib import Path

import ethos.adapters.config as config
from ethos.adapters.config import code_size_policy
from ethos.adapters.config import rules_config
from ethos.adapters.config import source_budget_policy


def test_rules_config_returns_empty_for_missing_config(tmp_path):
    assert rules_config(tmp_path) == {}
    assert code_size_policy(tmp_path) == {}
    result = source_budget_policy(tmp_path)
    assert result.policy is None
    assert result.required_gaps == ("source_budget_policy_missing",)


def test_code_size_policy_projects_only_dict_subtable(tmp_path):
    config_dir = tmp_path / ".ethos"
    config_dir.mkdir()
    (config_dir / "rules.toml").write_text(
        """
[quality.code_size]
default_effective_max_lines = 123
surface_path_globs = ["ethos/surface/**"]
""".strip(),
        encoding="utf-8",
    )

    assert rules_config(tmp_path)["quality"]["code_size"]["default_effective_max_lines"] == 123
    assert code_size_policy(tmp_path) == {
        "default_effective_max_lines": 123,
        "surface_path_globs": ["ethos/surface/**"],
    }


def test_code_size_policy_ignores_non_dict_quality_tables(tmp_path):
    config_dir = tmp_path / ".ethos"
    config_dir.mkdir()
    (config_dir / "rules.toml").write_text('quality = "not-a-table"\n', encoding="utf-8")

    assert code_size_policy(tmp_path) == {}
    assert source_budget_policy(tmp_path).policy is None


def test_source_budget_policy_treats_non_mapping_subtable_as_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config,
        "rules_config",
        lambda _root: {"quality": {"source_budget": "not-a-table"}},
    )

    assert source_budget_policy(tmp_path).required_gaps == ("source_budget_policy_missing",)


def test_source_budget_policy_reports_invalid_contract_without_filtering(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config,
        "rules_config",
        lambda _root: {
            "quality": {
                "source_budget": {
                    "baseline_head": "a" * 40,
                    "enforcement": "transition",
                    "baseline": {"global_total": 0, "python_total": 0},
                    "terminal": {"global_total": 0, "python_total": 0},
                    "debt": {
                        "maximum_total": 0,
                        "waves": [{"id": "w1", "due_on": "2026-12-01", "state": "active"}],
                        "records": [
                            {
                                "id": "debt-1",
                                "owner": "owner",
                                "replacement": "replacement",
                                "deletion_wave": "w1",
                                "expiry": "not-a-date",
                                "allowance": 0,
                                "expected_net_deletion": 1,
                                "allowance_by_category": {},
                            }
                        ],
                    },
                }
            }
        },
    )

    result = source_budget_policy(tmp_path)

    assert result.policy is None
    assert result.required_gaps == ("source_budget_policy_invalid:debt.records.0.expiry",)


def test_repository_source_budget_policy_has_a_complete_lifecycle_contract():
    root = Path(__file__).resolve().parents[3]

    result = source_budget_policy(root)

    assert result.required_gaps == ()
    assert result.policy is not None
    assert all(
        record.expected_net_deletion >= record.allowance for record in result.policy.debt.records
    )
