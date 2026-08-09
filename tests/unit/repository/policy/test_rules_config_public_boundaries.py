from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.rules.config import configured_rules
from ethos.repository.policy.rules.config import load_rules_config
from ethos.repository.policy.rules.config import path_matches
from ethos.repository.policy.rules.config import resolve_profile_stack
from ethos.repository.policy.rules.config import rules_path

if TYPE_CHECKING:
    from pathlib import Path


def test_rules_config_missing_and_canonical_boundaries(tmp_path: Path) -> None:
    assert rules_path(tmp_path) == tmp_path / ".ethos/rules.toml"
    assert load_rules_config(tmp_path) == {}
    assert resolve_profile_stack({}) == (["generic"], [])
    assert configured_rules(tmp_path) == []

    config = {
        "profiles": {"active": ["python", "strict"]},
        "rule": [{"id": "canonical"}, "malformed"],
    }
    assert resolve_profile_stack(config) == (["generic", "python", "strict"], [])
    assert configured_rules(tmp_path, config=config) == [
        {"id": "canonical"},
        {"id": "", "_invalid": "rule_not_table"},
    ]
    assert path_matches("src/ethos", ["src/**"])
    assert path_matches("src", ["src/**"])
    assert not path_matches("tests/unit", ["src/**"])


@pytest.mark.parametrize(
    ("config", "gap"),
    [
        ({"profiles": []}, "rules_profile_invalid:must_be_table"),
        ({"profiles": {"active": "python"}}, "rules_profile_invalid:active_must_be_string_array"),
        ({"profiles": {"active": []}}, "rules_profile_invalid:active_must_not_be_empty"),
        (
            {"profiles": {"active": ["python", ""]}},
            "rules_profile_invalid:active_must_not_contain_empty_values",
        ),
        (
            {"profiles": {"active": ["python", "python"]}},
            "rules_profile_ambiguous:active_contains_duplicates",
        ),
        (
            {"profiles": {"active": ["unknown", "foreign"]}},
            "rules_profile_invalid:unknown_profile:foreign|rules_profile_invalid:unknown_profile:unknown",
        ),
    ],
)
def test_rules_profile_malformed_shapes_fail_closed(config: dict[str, object], gap: str) -> None:
    expected = gap.split("|")
    assert resolve_profile_stack(config) == (["generic"], expected)


def test_rules_config_preserves_parse_error(tmp_path: Path) -> None:
    path = rules_path(tmp_path)
    path.parent.mkdir()
    path.write_text("profiles = [\n", encoding="utf-8")

    config = load_rules_config(tmp_path)

    assert "_parse_error" in config
    stack, gaps = resolve_profile_stack(config)
    assert stack == ["generic"]
    assert gaps[0].startswith("rules_config_parse_error:")
