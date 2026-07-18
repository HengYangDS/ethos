from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.migration import migrate_legacy_rules


def test_legacy_rules_migration_is_dry_run(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        '[formats]\nuser_config = "TOML"\n',
        encoding="utf-8",
    )

    report = migrate_legacy_rules(tmp_path)

    assert report["ok"] is True
    assert report["legacy_detected"] is True
    assert report["applied"] is False
    assert (
        "ethos rules migrate --apply --authorize --expect-head <git-head>" in report["next_actions"]
    )


def test_v2_rules_with_gate_definitions_are_not_legacy(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos" / "rules.toml").write_text(
        """
[profiles]
active = ["generic"]

[gates.custom]
command = "ethos quality schemas --json"
blocking = true
""".lstrip(),
        encoding="utf-8",
    )

    report = rules_check_report(tmp_path)

    assert report["legacy"]["legacy_detected"] is False
    assert report["legacy"]["has_v2_rules"] is True


def test_legacy_rules_migration_preserves_rule_semantics(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    rules_path.write_text(
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

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is True
    assert report["legacy_detected"] is True
    assert report["applied"] is True
    assert report["target"]["rule"]
    written = rules_path.read_text(encoding="utf-8")
    assert 'id = "legacy.docs"' in written
    assert 'path_globs = ["docs/**"]' in written
    assert 'required_gates = ["docs-registry"]' in written


def test_legacy_rules_migration_preserves_profiles_and_custom_gates(
    tmp_path: Path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    rules_path.write_text(
        """
[profiles]
active = ["python"]

[gates.unit]
command = "uv run pytest -q"
blocking = true

[[rule]]
id = "legacy.src"
risk = "source_regression"
paths = ["src/**"]
requires = ["unit"]
evidence = ["unit test output"]
""".lstrip(),
        encoding="utf-8",
    )
    before = rules_check_report(tmp_path)
    assert before["ok"] is True

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is True
    assert report["target"]["profiles"]["active"] == ["generic", "python"]
    assert report["target"]["gates"]["unit"]["command"] == "uv run pytest -q"
    written = rules_path.read_text(encoding="utf-8")
    assert "[gates.unit]" in written
    assert 'command = "uv run pytest -q"' in written
    assert "blocking = true" in written
    after = rules_check_report(tmp_path)
    assert after["ok"] is True
    assert "unknown_rule_gate:legacy.src:unit" not in after["required_gaps"]
