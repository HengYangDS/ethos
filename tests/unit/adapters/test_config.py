from __future__ import annotations

from ethos.adapters.config import code_size_policy
from ethos.adapters.config import rules_config
from ethos.adapters.config import source_budget_policy


def test_rules_config_returns_empty_for_missing_config(tmp_path):
    assert rules_config(tmp_path) == {}
    assert code_size_policy(tmp_path) == {}
    assert source_budget_policy(tmp_path) == {}


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
    assert source_budget_policy(tmp_path) == {}
