from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.planner import adoption_plan
from ethos.repository.planner import available_profiles

if TYPE_CHECKING:
    from pathlib import Path


def test_available_profiles_are_explicit() -> None:
    assert {"generic", "python", "monorepo", "github", "gitlab"} <= set(available_profiles())


def test_python_package_profile_alias_is_not_current_product_surface(
    tmp_path: Path,
) -> None:
    current = adoption_plan(tmp_path, profile="python", apply=False)

    assert current["profile"] == "python"
    assert current["profile_aliases"] == []
    assert "python-package" not in available_profiles()

    with pytest.raises(ValueError, match="unknown ETHOS adoption profile: python-package"):
        adoption_plan(tmp_path, profile="python-package", apply=False)


def test_adoption_plan_explains_dry_run_apply_and_rollback(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, profile="python", apply=False)

    assert result["applied"] is False
    assert "pyproject.toml" in result["read_files"]
    assert result["planned_files"]
    assert result["apply_criteria"]
    assert result["profile_match"]["ok"] is False
    assert "missing:pyproject.toml" in result["profile_match"]["reasons"]
    assert result["next_action"] == "review profile mismatch before apply"
    assert result["rollback"]["mode"] == "remove_generated_files_or_restore_git_state"
    assert result["rollback"]["generated_files"] == result["planned_files"]
    first = result["write_plan"][0]
    assert set(first) == {
        "path",
        "action",
        "conflict",
        "existed",
        "content_sha256",
        "preview",
    }


def test_adoption_plan_blocks_profile_mismatch_from_apply(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, profile="python", apply=True)

    assert result["applied"] is False
    assert "profile_mismatch:python" in result["required_gaps"]
    assert result["next_action"] == "review profile mismatch before apply"
    assert not (tmp_path / ".ethos" / "project.toml").exists()


def test_adoption_plan_reports_profile_match_when_observed_files_fit(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")

    result = adoption_plan(tmp_path, profile="python", apply=False)

    assert result["detected_profile"] == "python"
    assert result["profile_match"] == {"ok": True, "reasons": ["matched:python"]}
    assert result["observed_files"]["pyproject.toml"] is True
    assert result["next_action"] == "review dry-run write plan"


def test_adoption_plan_blocks_conflicting_existing_files_from_apply(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# local instructions\n", encoding="utf-8")

    result = adoption_plan(tmp_path, profile="generic", apply=True)

    assert result["applied"] is False
    assert result["required_gaps"] == ["adoption_conflict:AGENTS.md"]
    conflict = next(item for item in result["write_plan"] if item["path"] == "AGENTS.md")
    assert conflict["action"] == "skip_existing_nonempty"
    assert conflict["conflict"] is True
    assert "AGENTS.md" not in result["rollback"]["generated_files"]


def test_gitlab_profile_adds_ci_projection(tmp_path: Path) -> None:
    (tmp_path / ".gitlab").mkdir()

    result = adoption_plan(tmp_path, profile="gitlab", apply=True)
    release = (tmp_path / ".ethos" / "release.toml").read_text(encoding="utf-8")

    assert result["profile"] == "gitlab"
    assert ".gitlab-ci.yml" in result["planned_files"]
    assert (tmp_path / ".gitlab-ci.yml").exists()
    assert "[host_profile]" in release
    assert 'provider = "gitlab"' in release
    assert "[host_profile.surfaces]" in release
    assert 'ci = ".gitlab-ci.yml"' in release


def test_monorepo_profile_projects_workspace_packages(tmp_path: Path) -> None:
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "alpha").mkdir()
    (tmp_path / "packages" / "beta").mkdir()

    result = adoption_plan(tmp_path, profile="monorepo", apply=True)
    workspace = (tmp_path / ".ethos/workspace.toml").read_text(encoding="utf-8")

    assert result["profile"] == "monorepo"
    assert 'name = "alpha"' in workspace
    assert 'name = "beta"' in workspace
