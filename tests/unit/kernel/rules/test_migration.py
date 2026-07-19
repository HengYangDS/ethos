from __future__ import annotations

import fcntl
import tomllib
from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.rules.config as rules_config
import ethos.repository.policy.rules.migration as migration

if TYPE_CHECKING:
    from pathlib import Path

from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.migration import migrate_legacy_rules


def _write_rules(tmp_path: Path, source: str) -> Path:
    path = tmp_path / ".ethos" / "rules.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_legacy_rules_migration_is_dry_run(tmp_path: Path) -> None:
    _write_rules(tmp_path, '[formats]\nuser_config = "TOML"\n')

    report = migrate_legacy_rules(tmp_path)

    assert report["ok"] is True
    assert report["legacy_detected"] is True
    assert report["applied"] is False
    assert (
        "ethos rules migrate --apply --authorize --expect-head <git-head>" in report["next_actions"]
    )


def test_v2_rules_with_gate_definitions_are_not_legacy(tmp_path: Path) -> None:
    _write_rules(
        tmp_path,
        """
[profiles]
active = ["generic"]

[gates.custom]
command = "ethos quality schemas --json"
blocking = true
""".lstrip(),
    )

    report = rules_check_report(tmp_path)

    assert report["legacy"]["legacy_detected"] is False
    assert report["legacy"]["has_v2_rules"] is True


def test_legacy_rules_migration_preserves_rule_semantics(tmp_path: Path) -> None:
    rules_path = _write_rules(
        tmp_path,
        """
[[rule]]
id = "legacy.docs"
version = 2
risk = "docs_drift"
paths = ["docs/**"]
requires = ["docs-registry"]
evidence = ["docs evidence"]
non_waivable = true
""".lstrip(),
    )

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is True
    assert report["legacy_detected"] is True
    assert report["applied"] is True
    assert report["target"]["rule"]
    written = rules_path.read_text(encoding="utf-8")
    assert 'id = "legacy.docs"' in written
    assert "version = 2" in written
    assert 'path_globs = ["docs/**"]' in written
    assert 'required_gates = ["docs-registry"]' in written
    assert "non_waivable = true" in written


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
    _write_rules(tmp_path, source)

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
    source = "[formats\nuser_config = 'TOML'\n"
    rules_path = _write_rules(tmp_path, source)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["applied"] is False
    assert report["required_gaps"]
    assert str(report["required_gaps"][0]).startswith("rules_config_parse_error:")
    assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_rejects_invalid_rule_shapes(tmp_path: Path) -> None:
    source = """
[[rule]]
id = "legacy.empty"
risk = "empty_scope"
path_globs = []
requires = []
version = true
non_waivable = "yes"
""".lstrip()
    rules_path = _write_rules(tmp_path, source)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["applied"] is False
    assert {
        "rules_migration_invalid:legacy.empty:[] should be non-empty",
        "rules_migration_invalid:legacy.empty:version_must_be_integer",
        "rules_migration_invalid:legacy.empty:non_waivable_must_be_boolean",
    } <= set(report["required_gaps"])
    assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_rejects_conflicting_legacy_and_v2_keys(
    tmp_path: Path,
) -> None:
    source = """
[[rule]]
id = "legacy.conflict"
risk = "source_regression"
subject = "other-subject"
stop_condition = "other-stop"
paths = ["src/**"]
path_globs = ["docs/**"]
requires = ["unit"]
required_gates = ["unit"]
""".lstrip()
    rules_path = _write_rules(tmp_path, source)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["applied"] is False
    assert report["required_gaps"] == [
        "rules_migration_ambiguous:legacy.conflict:paths:path_globs",
        "rules_migration_ambiguous:legacy.conflict:risk:subject",
        "rules_migration_ambiguous:legacy.conflict:risk:stop_condition",
    ]
    assert report["target_text"] == source
    assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_rejects_unpreserved_rule_keys(tmp_path: Path) -> None:
    source = """
[[rule]]
id = "legacy.extension"
risk = "source_regression"
paths = ["src/**"]
requires = []
custom_policy = "must-survive"
""".lstrip()
    rules_path = _write_rules(tmp_path, source)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["applied"] is False
    assert report["required_gaps"] == [
        "rules_migration_lossy:legacy.extension:unsupported_keys:custom_policy"
    ]
    assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_rejects_malformed_profiles_active(
    tmp_path: Path,
) -> None:
    source = """
[profiles]
active = "python"

[[rule]]
id = "legacy.python"
risk = "python_regression"
paths = ["src/**"]
requires = []
""".lstrip()
    rules_path = _write_rules(tmp_path, source)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["legacy_detected"] is True
    assert report["applied"] is False
    assert report["required_gaps"] == ["rules_profile_invalid:active_must_be_string_array"]
    assert report["target_text"] == source
    assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_rewrites_multiline_profiles_active(
    tmp_path: Path,
) -> None:
    source = """
[profiles]
active = [
  "python",
]

[[rule]]
id = "legacy.python"
risk = "python_regression"
paths = ["src/**"]
requires = []
""".lstrip()
    rules_path = _write_rules(tmp_path, source)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is True
    assert report["legacy_detected"] is True
    assert report["applied"] is True
    assert report["target"]["profiles"]["active"] == ["generic", "python"]
    migrated_rule = report["target"]["rule"][0]
    assert {"risk", "paths", "requires", "evidence"}.isdisjoint(migrated_rule)
    assert tomllib.loads(rules_path.read_text(encoding="utf-8")) == report["target"]


def test_legacy_rules_migration_reports_target_parse_error_without_writing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = '[formats]\nuser_config = "TOML"\n'
    rules_path = _write_rules(tmp_path, source)
    monkeypatch.setattr(migration, "_migrated_rules_text", lambda *_args: "[profiles\n")

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["legacy_detected"] is True
    assert report["applied"] is False
    assert str(report["required_gaps"][0]).startswith("rules_migration_target_parse_error:")
    assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_rejects_quoted_rule_header_that_stays_legacy(
    tmp_path: Path,
) -> None:
    source = """
[["rule"]]
id = "legacy.quoted"
risk = "quoted_regression"
paths = ["src/**"]
requires = []
""".lstrip()
    rules_path = _write_rules(tmp_path, source)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["legacy_detected"] is True
    assert report["applied"] is False
    assert report["required_gaps"] == ["rules_migration_target_legacy_keys:legacy.quoted"]
    assert rules_path.read_text(encoding="utf-8") == source


def test_rules_config_exposes_public_rule_and_profile_contracts(tmp_path: Path) -> None:
    assert rules_config.rules_path(tmp_path) == tmp_path / ".ethos" / "rules.toml"
    legacy = {
        "id": "legacy.python",
        "risk": "python_regression",
        "paths": ["src/**"],
        "requires": [],
        "non_waivable": "yes",
    }
    assert rules_config.is_legacy_rule_item(legacy) is True
    configured = rules_config.configured_rules(
        tmp_path,
        config={"rule": ["invalid", legacy]},
    )
    assert configured[0] == {"id": "", "_invalid": "rule_not_table"}
    assert configured[1]["path_globs"] == ["src/**"]
    assert configured[1]["non_waivable"] == "yes"
    assert rules_config.resolve_profile_stack({"profiles": {"active": ["python-package"]}}) == (
        ["generic", "python"],
        [],
    )
    for config, gap in (
        ({"profiles": "python"}, "rules_profile_invalid:must_be_table"),
        (
            {"profiles": {"active": []}},
            "rules_profile_invalid:active_must_not_be_empty",
        ),
        (
            {"profiles": {"active": ["python", " "]}},
            "rules_profile_invalid:active_must_not_contain_empty_values",
        ),
    ):
        assert rules_config.resolve_profile_stack(config) == (["generic"], [gap])


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
    source = '[formats]\nuser_config = "TOML"\n'
    rules_path = _write_rules(tmp_path, source)

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
    source = '[formats]\nuser_config = "TOML"\n'
    drift = '[formats]\nuser_config = "YAML"\n'
    rules_path = _write_rules(tmp_path, source)
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


def test_legacy_rules_migration_does_not_overwrite_edit_after_digest_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = '[formats]\nuser_config = "TOML"\n'
    drift = '[formats]\nuser_config = "YAML"\n'
    rules_path = _write_rules(tmp_path, source)
    source_digest = migrate_legacy_rules(tmp_path)["source_digest"]
    original_write = migration._write_text_atomic

    def inject_drift(path: Path, *args: str, **kwargs: object) -> object:
        path.write_text(drift, encoding="utf-8")
        return original_write(path, *args, **kwargs)

    monkeypatch.setattr(migration, "_write_text_atomic", inject_drift)

    report = migrate_legacy_rules(
        tmp_path,
        apply=True,
        expect_source_digest=str(source_digest),
    )

    assert report["ok"] is False
    assert report["applied"] is False
    assert report["required_gaps"] == ["rules_migration_source_changed"]
    assert rules_path.read_text(encoding="utf-8") == drift


@pytest.mark.parametrize("head_result", ["other-head", "expected-head"])
def test_legacy_rules_migration_enforces_head_guard_then_rechecks_source(
    tmp_path: Path,
    head_result: str,
) -> None:
    source = '[formats]\nuser_config = "TOML"\n'
    drift = '[formats]\nuser_config = "YAML"\n'
    rules_path = _write_rules(tmp_path, source)

    def read_head() -> str:
        if head_result == "expected-head":
            rules_path.write_text(drift, encoding="utf-8")
        return head_result

    report = migrate_legacy_rules(
        tmp_path,
        apply=True,
        expect_source_digest=migration._text_digest(source),
        expect_head="expected-head",
        read_head=read_head,
    )

    assert report["ok"] is False
    assert report["applied"] is False
    if head_result == "expected-head":
        assert report["required_gaps"] == ["rules_migration_source_changed"]
        assert rules_path.read_text(encoding="utf-8") == drift
    else:
        assert report["required_gaps"] == ["expect_head_mismatch"]
        assert rules_path.read_text(encoding="utf-8") == source


@pytest.mark.parametrize("write_errno", [None, 13])
def test_legacy_rules_migration_uses_one_atomic_replace_and_fails_closed(
    tmp_path: Path,
    monkeypatch,
    write_errno: int | None,
) -> None:
    source = '[formats]\nuser_config = "TOML"\n'
    rules_path = _write_rules(tmp_path, source)
    path_type = type(rules_path)
    original_replace = path_type.replace
    replace_targets: list[Path] = []

    def replace(source_path: Path, target: Path) -> Path:
        replace_targets.append(target)
        if write_errno is not None:
            raise OSError(write_errno, "permission denied")
        return original_replace(source_path, target)

    monkeypatch.setattr(path_type, "replace", replace)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert replace_targets == [rules_path]
    if write_errno is None:
        assert report["ok"] is True
        assert report["applied"] is True
    else:
        assert report["ok"] is False
        assert report["applied"] is False
        assert report["required_gaps"] == [f"rules_migration_write_failed:{write_errno}"]
        assert rules_path.read_text(encoding="utf-8") == source


def test_legacy_rules_migration_fails_closed_if_source_disappears_before_lock(
    tmp_path: Path,
    monkeypatch,
) -> None:
    rules_path = _write_rules(tmp_path, '[formats]\nuser_config = "TOML"\n')
    original_prepare = migration._prepared_temporary

    def remove_source(path: Path, text: str) -> Path:
        temporary = original_prepare(path, text)
        path.unlink()
        return temporary

    monkeypatch.setattr(migration, "_prepared_temporary", remove_source)

    report = migrate_legacy_rules(tmp_path, apply=True)

    assert report["ok"] is False
    assert report["applied"] is False
    assert report["required_gaps"] == ["rules_migration_source_changed"]
    assert not rules_path.exists()
    assert not list(rules_path.parent.glob(f".{rules_path.name}.migration.*"))


def test_profiles_assignment_parser_requires_active_and_fails_closed() -> None:
    with pytest.raises(ValueError, match="could not be isolated"):
        migration._profiles_active_assignment_end(["[profiles]\n", "active = [\n"], 1)
