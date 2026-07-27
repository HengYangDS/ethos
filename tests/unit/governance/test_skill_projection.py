from __future__ import annotations

from ethos.contracts.skill.activation import normalize_skill_activation


def test_activation_metadata_does_not_duplicate_package_capabilities() -> None:
    registry = normalize_skill_activation(
        {
            "meta": {"version": 2},
            "skill": [{"id": "sample"}],
        },
        source="test",
    )

    record = registry["records"][0]
    assert "commands" not in record
    assert "commands" not in record["extensions"]
