from __future__ import annotations

from pathlib import Path

from ethos_adopt.planner import adoption_plan, available_profiles


def test_available_profiles_are_explicit() -> None:
    assert {"generic", "python-package", "monorepo", "github", "gitlab"} <= set(
        available_profiles()
    )


def test_gitlab_profile_adds_ci_projection(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, profile="gitlab", apply=True)

    assert result["profile"] == "gitlab"
    assert ".gitlab-ci.yml" in result["planned_files"]
    assert (tmp_path / ".gitlab-ci.yml").exists()


def test_monorepo_profile_projects_workspace_packages(tmp_path: Path) -> None:
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "alpha").mkdir()
    (tmp_path / "packages" / "beta").mkdir()

    result = adoption_plan(tmp_path, profile="monorepo", apply=True)
    workspace = (tmp_path / ".ethos/workspace.toml").read_text(encoding="utf-8")

    assert result["profile"] == "monorepo"
    assert 'name = "alpha"' in workspace
    assert 'name = "beta"' in workspace
