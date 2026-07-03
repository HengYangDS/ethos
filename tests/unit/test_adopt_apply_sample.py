from __future__ import annotations

from typing import TYPE_CHECKING

from ethos_repository.planner import adoption_plan, detect_repo_profile

if TYPE_CHECKING:
    from pathlib import Path


def test_detect_repo_profile_for_python_package(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")

    assert detect_repo_profile(tmp_path) == "python"


def test_adopt_apply_writes_expected_files(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, apply=True)

    assert result["applied"] is True
    assert (tmp_path / ".ethos/project.toml").exists()
    assert f'name = "{tmp_path.name}"' in (tmp_path / ".ethos/project.toml").read_text(
        encoding="utf-8"
    )
    assert (tmp_path / ".ethos/state/.gitignore").read_text(encoding="utf-8").startswith("*")


def test_adopt_apply_writes_complete_governance_skeleton(tmp_path: Path) -> None:
    (tmp_path / ".gitlab").mkdir()

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
        ".agents/skills/ethos-repository-governance/package.toml",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "openspec/config.yaml",
        "openspec/README.md",
        "openspec/specs/README.md",
        "openspec/specs/families.toml",
        "openspec/specs/capability.template.toml",
        "openspec/changes/README.md",
        "openspec/changes/template.md",
        "openspec/specs/ethos-core/spec.md",
        "openspec/specs/ethos-contracts/spec.md",
        "openspec/specs/ethos-repository/spec.md",
        "openspec/specs/ethos-repository/capability.toml",
        "openspec/specs/ethos-adapters/spec.md",
        "openspec/specs/ethos-assistants/spec.md",
        "openspec/specs/ethos-cli/spec.md",
        "openspec/specs/ethos-distribution/spec.md",
        "openspec/specs/ethos-test/spec.md",
        "openspec/changes/.gitkeep",
        "openspec/changes/archive/.gitkeep",
        "docs/index.md",
        "docs/start/quickstart.md",
        "docs/governance/ethos.md",
        "docs/evidence/.gitkeep",
        "claims/.gitkeep",
        "schemas/ethos/.gitkeep",
        ".gitlab-ci.yml",
    }

    assert result["applied"] is True
    assert required <= planned
    for relative in required:
        assert (tmp_path / relative).exists(), relative
    assert "sourceOfTruth" not in (tmp_path / ".agents/skills/activation.toml").read_text(
        encoding="utf-8"
    )
    activation = (tmp_path / ".agents/skills/activation.toml").read_text(encoding="utf-8")
    package_manifest = (
        tmp_path / ".agents/skills/ethos-repository-governance/package.toml"
    ).read_text(encoding="utf-8")
    skill_text = (tmp_path / ".agents/skills/ethos-repository-governance/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "version = 2" in activation
    assert 'subject = "repository-governance"' in activation
    assert 'operation = "govern"' in activation
    assert 'authority = "primary"' in activation
    assert (
        'package_manifest = ".agents/skills/ethos-repository-governance/package.toml"' in activation
    )
    assert 'expected_digest = "sha256:' not in activation
    assert 'entrypoint = "SKILL.md"' in package_manifest
    assert 'expected_digest = "sha256:' in package_manifest
    assert 'kind = "command_readonly"' in package_manifest
    assert '"evolution/**"' in activation
    assert "## Workflow" in skill_text
    assert "## Evidence" in skill_text
    assert "## Trust Boundary" in skill_text
    assert "Authority" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "ethos prove" in (tmp_path / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "Unreleased" in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "ethos status" in (tmp_path / "docs/start/quickstart.md").read_text(
        encoding="utf-8"
    )
    assert "primary_invariant" in (
        tmp_path / "openspec/specs/ethos-repository/capability.toml"
    ).read_text(encoding="utf-8")
    repository_profile = (tmp_path / "openspec/specs/ethos-repository/capability.toml").read_text(
        encoding="utf-8"
    )
    assert "decision_axes" in repository_profile
    assert "[recommended_facets]" in repository_profile
    assert "OpenSpec Workspace" in (tmp_path / "openspec/README.md").read_text(
        encoding="utf-8"
    )
    assert "Change Template" in (tmp_path / "openspec/changes/template.md").read_text(
        encoding="utf-8"
    )


def test_generated_quickstart_teaches_first_hour_not_maintainer_checks(
    tmp_path: Path,
) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    quickstart = (tmp_path / "docs/start/quickstart.md").read_text(encoding="utf-8")
    first_hour = quickstart.split("## Maintainer Reference", 1)[0]

    for command in (
        "ethos status",
        "ethos plan --changed",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ):
        assert command in first_hour
    assert "ethos report" in first_hour
    assert "ethos prove --execute" not in first_hour
    assert "ethos quality" not in first_hour


def test_generated_skill_loop_uses_workflow_plus_scorecard(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    skill = (
        tmp_path / ".agents/skills/ethos-repository-governance/SKILL.md"
    ).read_text(encoding="utf-8")

    for command in (
        "ethos status",
        "ethos plan --changed",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ):
        assert command in skill
    assert "ethos report" in skill
    assert "ethos quality" not in skill


def test_adopt_rules_use_single_kernel_governance_entrypoints(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    rules = (tmp_path / ".ethos/rules.toml").read_text(encoding="utf-8")

    assert 'governance_audit = "ethos report --json"' in rules
    assert 'proof = "ethos prove --json"' in rules
    assert 'self_audit = "ethos self audit --json"' not in rules
