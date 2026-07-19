from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import ethos.surface.cli.rules as rules_surface
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import start_adopted_work_lane
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked

if TYPE_CHECKING:
    from pathlib import Path


LEGACY_RULES = """
[formats]
user_config = "TOML"

[quality]
coverage = 100

[gates.unit]
command = "pytest -q"
blocking = true

[[rule]]
id = "legacy.src"
risk = "source_regression"
paths = ["src/**"]
requires = ["unit"]
evidence = ["unit output"]
""".lstrip()


def _write_legacy_rules(root: Path) -> Path:
    path = root / ".ethos" / "rules.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(LEGACY_RULES, encoding="utf-8")
    return path


def test_rules_migrate_dry_run_reports_lossless_target_without_writing(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    path = _write_legacy_rules(repo)

    payload = run_ethos("rules", "migrate", "--root", repo.as_posix(), "--json", cwd=repo)

    assert payload["ok"] is True
    assert payload["state"] == "planned"
    assert payload["data"]["applied"] is False
    assert payload["data"]["target"]["quality"] == {"coverage": 100}
    assert path.read_text(encoding="utf-8") == LEGACY_RULES


def test_rules_migrate_apply_requires_authorization(
    tmp_path: Path,
    monkeypatch,
) -> None:
    lane = start_adopted_work_lane(tmp_path)
    path = _write_legacy_rules(lane.worktree)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    payload = run_ethos_blocked(
        "rules",
        "migrate",
        "--root",
        lane.worktree.as_posix(),
        "--apply",
        "--json",
        cwd=lane.worktree,
    )

    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]
    assert path.read_text(encoding="utf-8") == LEGACY_RULES


def test_rules_migrate_apply_rejects_head_mismatch(tmp_path: Path, monkeypatch) -> None:
    lane = start_adopted_work_lane(tmp_path)
    path = _write_legacy_rules(lane.worktree)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    payload = run_ethos_blocked(
        "rules",
        "migrate",
        "--root",
        lane.worktree.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        "0" * 40,
        "--json",
        cwd=lane.worktree,
    )

    assert "expect_head_mismatch" in payload["required_gaps"]
    assert path.read_text(encoding="utf-8") == LEGACY_RULES


def test_rules_migrate_apply_rejects_protected_root(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    path = _write_legacy_rules(repo)
    head = git(repo, "rev-parse", "HEAD")

    payload = run_ethos_blocked(
        "rules",
        "migrate",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )

    assert "protected_lane_prewrite_blocked" in payload["required_gaps"]
    assert path.read_text(encoding="utf-8") == LEGACY_RULES


def test_rules_migrate_apply_writes_only_after_work_lane_admission(
    tmp_path: Path,
    monkeypatch,
) -> None:
    lane = start_adopted_work_lane(tmp_path)
    path = _write_legacy_rules(lane.worktree)
    head = git(lane.worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")

    payload = run_ethos(
        "rules",
        "migrate",
        "--root",
        lane.worktree.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=lane.worktree,
    )

    assert payload["ok"] is True
    assert payload["state"] == "applied"
    migrated = tomllib.loads(path.read_text(encoding="utf-8"))
    assert migrated["quality"] == {"coverage": 100}
    assert migrated["rule"][0]["path_globs"] == ["src/**"]
    assert payload["data"]["prewrite"]["ok"] is True


def test_rules_migrate_apply_rechecks_head_after_prewrite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    lane = start_adopted_work_lane(tmp_path)
    path = _write_legacy_rules(lane.worktree)
    head = git(lane.worktree, "rev-parse", "HEAD")
    observed_heads = iter((head, "f" * 40))
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setattr(
        rules_surface.git_adapter,
        "current_head",
        lambda _root: next(observed_heads),
    )

    payload = run_ethos_blocked(
        "rules",
        "migrate",
        "--root",
        lane.worktree.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=lane.worktree,
    )

    assert payload["required_gaps"] == ["expect_head_mismatch"]
    assert path.read_text(encoding="utf-8") == LEGACY_RULES


def test_rules_migrate_apply_rechecks_head_inside_serialized_migration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    lane = start_adopted_work_lane(tmp_path)
    path = _write_legacy_rules(lane.worktree)
    head = git(lane.worktree, "rev-parse", "HEAD")
    observed_heads = iter((head, head, "f" * 40))
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setattr(
        rules_surface.git_adapter,
        "current_head",
        lambda _root: next(observed_heads),
    )

    payload = run_ethos_blocked(
        "rules",
        "migrate",
        "--root",
        lane.worktree.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=lane.worktree,
    )

    assert payload["required_gaps"] == ["expect_head_mismatch"]
    assert payload["data"]["applied"] is False
    assert path.read_text(encoding="utf-8") == LEGACY_RULES


def test_rules_migrate_dry_run_reports_current_v2_file(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    path = repo / ".ethos" / "rules.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    source = '[profiles]\nactive = ["generic"]\n'
    path.write_text(source, encoding="utf-8")

    payload = run_ethos("rules", "migrate", "--root", repo.as_posix(), "--json", cwd=repo)

    assert payload["ok"] is True
    assert payload["state"] == "current"
    assert payload["data"]["legacy_detected"] is False
    assert path.read_text(encoding="utf-8") == source


def test_plan_reports_invalid_rules_profiles_as_top_level_gap(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    path = repo / ".ethos" / "rules.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('[profiles]\nactive = "python"\n', encoding="utf-8")

    payload = run_ethos("plan", "--root", repo.as_posix(), "--json", cwd=repo)

    assert payload["ok"] is False
    assert "rules_profile_invalid:active_must_be_string_array" in payload["required_gaps"]
    assert payload["data"]["rule_validation_gaps"] == [
        "rules_profile_invalid:active_must_be_string_array"
    ]
