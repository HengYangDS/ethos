from __future__ import annotations

import fcntl
import tomllib
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


def test_legacy_rules_migration_preserves_all_active_policy_tables(
    tmp_path: Path,
) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    source = """
[standards]
json_schema = true

[determinism]
stable_json = "required"

[formats]
user_config = "TOML"

[artifacts]
durable_evidence_roots = ["evidence", "evidence/claims"]

[quality]
coverage = 100

[quality.source_budget]
baseline_head = "abc123"

[gates.unit]
command = "pytest -q"
blocking = true

[operator_extension]
mode = "active"

[[rule]]
id = "v2.docs"
owner = "repo-local"
authority_ref = ".ethos/rules.toml"
contract_ref = ".ethos/rules.toml"
subject = "docs"
severity = "advisory"
stop_condition = "docs_drift"
path_globs = ["docs/**"]
required_gates = ["unit"]

[[rule]]
id = "legacy.src"
risk = "source_regression"
paths = ["src/**"]
requires = ["unit"]
evidence = ["unit output"]
""".lstrip()
    rules_path.write_text(source, encoding="utf-8")

    report = migrate_legacy_rules(tmp_path)

    assert report["ok"] is True
    target = report["target"]
    assert isinstance(target, dict)
    parsed_source = tomllib.loads(source)
    for key in (
        "standards",
        "determinism",
        "formats",
        "artifacts",
        "quality",
        "gates",
        "operator_extension",
    ):
        assert target[key] == parsed_source[key]
    assert target["rule"][0] == parsed_source["rule"][0]
    migrated_rule = target["rule"][1]
    assert "paths" not in migrated_rule
    assert "requires" not in migrated_rule
    assert "evidence" not in migrated_rule
    assert migrated_rule["path_globs"] == ["src/**"]
    assert migrated_rule["required_gates"] == ["unit"]
    assert migrated_rule["evidence_requirements"] == ["unit output"]


def test_legacy_rules_migration_fails_closed_on_parse_error(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    source = "[formats\nuser_config = 'TOML'\n"
    rules_path.write_text(source, encoding="utf-8")

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["applied"] is False
    assert report["required_gaps"]
    assert str(report["required_gaps"][0]).startswith("rules_config_parse_error:")
    assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_inserts_missing_profiles_active(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    rules_path.write_text(
        """
[profiles]
mode = "custom"

[[rule]]
id = "legacy.docs"
paths = ["docs/**"]
requires = []
""".lstrip(),
        encoding="utf-8",
    )

    report = migrate_legacy_rules(tmp_path)

    assert report["target"]["profiles"] == {"active": ["generic"], "mode": "custom"}


def test_legacy_rules_migration_rejects_source_digest_mismatch(tmp_path: Path) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    source = '[formats]\nuser_config = "TOML"\n'
    rules_path.write_text(source, encoding="utf-8")

    report = migrate_legacy_rules(
        tmp_path,
        apply=True,
        expect_source_digest="sha256:" + "0" * 64,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["rules_migration_source_changed"]
    assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_rechecks_source_under_write_lock(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / ".ethos").mkdir()
    rules_path = tmp_path / ".ethos" / "rules.toml"
    source = '[formats]\nuser_config = "TOML"\n'
    drift = '[formats]\nuser_config = "YAML"\n'
    rules_path.write_text(source, encoding="utf-8")
    source_digest = migrate_legacy_rules(tmp_path)["source_digest"]
    original_flock = fcntl.flock

    def inject_drift(file_descriptor: int, operation: int) -> None:
        original_flock(file_descriptor, operation)
        if operation == fcntl.LOCK_EX:
            rules_path.write_text(drift, encoding="utf-8")

    monkeypatch.setattr(fcntl, "flock", inject_drift)

    report = migrate_legacy_rules(
        tmp_path,
        apply=True,
        expect_source_digest=str(source_digest),
    )

    assert report["ok"] is False
    assert report["applied"] is False
    assert report["required_gaps"] == ["rules_migration_source_changed"]
    assert rules_path.read_text(encoding="utf-8") == drift
