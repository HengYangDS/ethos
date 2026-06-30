from __future__ import annotations

from pathlib import Path

from ethos_project.planner import adoption_plan, detect_repo_profile


def test_detect_repo_profile_for_python_package(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")

    assert detect_repo_profile(tmp_path) == "python-package"


def test_adopt_apply_writes_expected_files(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, apply=True)

    assert result["applied"] is True
    assert (tmp_path / ".ethos/project.toml").exists()
    assert f'name = "{tmp_path.name}"' in (tmp_path / ".ethos/project.toml").read_text(
        encoding="utf-8"
    )
    assert (tmp_path / ".ethos/state/.gitignore").read_text(encoding="utf-8").startswith("*")


def test_adopt_apply_writes_complete_governance_skeleton(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, profile="gitlab", apply=True)

    planned = set(result["planned_files"])
    required = {
        ".ethos/project.toml",
        ".ethos/workspace.toml",
        ".ethos/rules.toml",
        ".ethos/assistants.toml",
        ".ethos/state/.gitignore",
        ".agents/skills/README.md",
        ".agents/skills/activation.toml",
        ".agents/skills/ethos-repository-governance/SKILL.md",
        "openspec/config.yaml",
        "openspec/specs/ethos-kernel/spec.md",
        "openspec/specs/ethos-project/spec.md",
        "openspec/specs/ethos-governance/spec.md",
        "openspec/specs/ethos-workspace/spec.md",
        "openspec/specs/ethos-agent/spec.md",
        "openspec/changes/.gitkeep",
        "openspec/changes/archive/.gitkeep",
        "docs/index.md",
        "docs/start/quickstart.md",
        "docs/governance/ethos.md",
        "docs/evidence/.gitkeep",
        "claims/.gitkeep",
        ".gitlab-ci.yml",
    }

    assert required <= planned
    for relative in required:
        assert (tmp_path / relative).exists(), relative
    assert "sourceOfTruth" not in (tmp_path / ".agents/skills/activation.toml").read_text(
        encoding="utf-8"
    )
    assert "ethos status" in (tmp_path / "docs/start/quickstart.md").read_text(
        encoding="utf-8"
    )
