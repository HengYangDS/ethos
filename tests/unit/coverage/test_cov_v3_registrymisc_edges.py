"""Coverage-closure v3: registrymisc reachable branches (100% no-exemption)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.repository.adoption.planner as planner
import ethos_core.contracts.system.contracts as system_contracts
from ethos.assistants import playbooks
from ethos.repository import context
from ethos.repository.adoption.scaffold.core import default_files
from ethos.repository.registry import commands
from ethos.repository.registry.docs.links import stable_paths_report
from ethos.repository.release import core as release_core
from ethos_core.contracts import rules
from tests.support import ethos_fixtures as fixtures

if TYPE_CHECKING:
    from pathlib import Path


def test_scan_retired_prefixes_skips_single_token_fenced_line(tmp_path: Path) -> None:
    # A fenced line with exactly one token gives len(tokens) < 2 -> commands.py 175->179
    # (skip the two-token prefix build) rather than 175->176.
    (tmp_path / "README.md").write_text("# Doc\n\n```bash\nethos\n```\n", encoding="utf-8")

    assert commands._scan_retired_public_command_prefixes(tmp_path) == []


def test_stable_paths_report_without_config_file(tmp_path: Path) -> None:
    # No docs/_meta/stable_paths.toml -> docs.py 347->357 skips the exists() block, configured empty.
    report = stable_paths_report(tmp_path)

    assert report["ok"] is False
    assert report["configured"] == []


def test_rule_attestation_gaps_skips_facts_when_not_dict() -> None:
    # input_snapshot is a dict but its 'facts' is absent (None) -> rules.py 267 isinstance False -> 267->274.
    gaps = rules.rule_attestation_gaps({"input": {"digest": "x"}}, {})

    assert "rule_attestation_output_missing" in gaps


def test_system_contracts_report_contract_without_schema_ref(tmp_path: Path) -> None:
    # A valid contract lacking a 'schema' key -> system/contracts.py 83 isinstance False -> 83->69 loop back.
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "authority.toml").write_text('title = "authority"\n', encoding="utf-8")

    report = system_contracts.system_contracts_report(tmp_path)

    assert report["contracts"]["authority"] is True


def test_transition_registry_keeps_explicit_subjects() -> None:
    # A skill item carrying non-empty subjects -> playbooks.py 194 `if not subjects` False -> 194->196.
    result = playbooks._transition_registry(
        {"skill": [{"id": "s1", "subjects": ["alpha"]}]}, skills_root="skills"
    )

    assert result["records"][0]["route_subjects"] == ["alpha"]


def test_detect_repo_profile_gitlab(tmp_path: Path) -> None:
    # .gitlab-ci.yml present -> planner.py line 43 return "gitlab".
    (tmp_path / ".gitlab-ci.yml").write_text("stages: []\n", encoding="utf-8")

    assert planner.detect_repo_profile(tmp_path) == "gitlab"


def test_detect_repo_profile_github(tmp_path: Path) -> None:
    # .github present (no .gitlab-ci.yml) -> planner.py line 45 return "github".
    (tmp_path / ".github").mkdir()

    assert planner.detect_repo_profile(tmp_path) == "github"


def test_write_plan_write_empty_action(tmp_path: Path) -> None:
    # Existing empty file with non-empty planned content -> planner.py line 86 action "write_empty".
    (tmp_path / "foo.txt").write_text("", encoding="utf-8")

    plan = planner._write_plan(tmp_path, {"foo.txt": "content"})

    assert plan[0]["action"] == "write_empty"


def test_workspace_toml_monorepo_empty_packages_falls_back(tmp_path: Path) -> None:
    # monorepo profile with a packages/ dir holding no subdirectories -> blocks empty ->
    # default_files() exercises the monorepo workspace fallback when packages/ has no directories.
    packages = tmp_path / "packages"
    packages.mkdir()
    (packages / "notadir.txt").write_text("x", encoding="utf-8")

    files = default_files(tmp_path, "monorepo")

    assert 'name = "root"' in files[".ethos/workspace.toml"]


def test_authority_order_returns_empty_when_order_not_list(tmp_path: Path) -> None:
    # authority.toml present but 'order' is a string, not a list -> context.py 24 True -> line 25 return ().
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "authority.toml").write_text('order = "flat"\n', encoding="utf-8")

    assert context._authority_order(tmp_path) == ()


def test_release_config_missing_file_returns_empty(tmp_path: Path) -> None:
    # No .ethos/release.toml -> release/core.py line 28 return {}.
    assert release_core.release_config(tmp_path) == {}


def test_sample_repository_names_returns_constant() -> None:
    # testing/fixtures.py line 22 return SAMPLE_REPOSITORIES.
    assert fixtures.sample_repository_names() == fixtures.SAMPLE_REPOSITORIES
