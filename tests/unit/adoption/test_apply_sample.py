from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.adoption.planner import detect_repo_profile

if TYPE_CHECKING:
    from pathlib import Path


def _assert_required_scaffold_files_exist(tmp_path: Path, planned: set[str]) -> None:
    required = {
        ".gitignore",
        ".config/ethos/generated-artifacts.toml",
        ".ethos/project.toml",
        ".ethos/workspace.toml",
        ".ethos/rules.toml",
        ".ethos/assistants.toml",
        ".ethos/state/.gitignore",
        ".agents/skills/README.md",
        ".agents/skills/activation.toml",
        ".agents/skills/ethos-repository-governance/SKILL.md",
        ".agents/skills/ethos-repository-governance/package.toml",
        ".agents/skills/ethos-skill-portfolio-governance/SKILL.md",
        ".agents/skills/ethos-skill-portfolio-governance/package.toml",
        ".agents/skills/ethos-adoption-profile-governance/SKILL.md",
        ".agents/skills/ethos-adoption-profile-governance/package.toml",
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
        "openspec/specs/kernel/spec.md",
        "openspec/specs/contracts/spec.md",
        "openspec/specs/repository-governance/spec.md",
        "openspec/specs/repository-governance/capability.toml",
        "openspec/specs/adapters/spec.md",
        "openspec/specs/assistant-projections/spec.md",
        "openspec/specs/command-plane/spec.md",
        "openspec/specs/distribution/spec.md",
        "openspec/specs/proof-hosts/spec.md",
        "openspec/changes/.gitkeep",
        "openspec/changes/archive/.gitkeep",
        "docs/README.md",
        "docs/index.md",
        "docs/decisions/README.md",
        "docs/decisions/decision-index.md",
        "docs/decisions/decision-dependency-map.md",
        "docs/decisions/decision-code-links.md",
        "docs/decisions/accepted/README.md",
        "docs/decisions/superseded/README.md",
        "docs/decisions/templates/README.md",
        "docs/decisions/templates/decision-record.md",
        "docs/evidence/README.md",
        "docs/history/README.md",
        "docs/reference/README.md",
        "docs/start/quickstart.md",
        "docs/governance/ethos.md",
        "evidence/.gitkeep",
        "evidence/claims/.gitkeep",
        "system/schemas/kernel/.gitkeep",
        ".gitlab-ci.yml",
    }

    assert required <= planned
    for relative in required:
        assert (tmp_path / relative).exists(), relative


def _assert_generated_skill_scaffold(tmp_path: Path) -> None:
    activation = (tmp_path / ".agents/skills/activation.toml").read_text(encoding="utf-8")
    package_manifest = (
        tmp_path / ".agents/skills/ethos-repository-governance/package.toml"
    ).read_text(encoding="utf-8")
    skill_text = (tmp_path / ".agents/skills/ethos-repository-governance/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "sourceOfTruth" not in activation
    assert "version = 2" in activation
    assert 'subject = "repository-governance"' in activation
    assert 'operation = "govern"' in activation
    assert 'authority = "primary"' in activation
    assert (
        'package_manifest = ".agents/skills/ethos-repository-governance/package.toml"' in activation
    )
    assert 'expected_digest = "sha256:' not in activation
    assert 'id = "ethos-skill-portfolio-governance"' in activation
    assert 'id = "ethos-adoption-profile-governance"' in activation
    assert 'expected_registry_digest = "sha256:' in activation
    assert 'entrypoint = "SKILL.md"' in package_manifest
    assert 'expected_digest = "sha256:' in package_manifest
    assert 'kind = "command_readonly"' in package_manifest
    assert '"evolution/**"' in activation
    assert "## Workflow" in skill_text
    assert "## Evidence" in skill_text
    assert "## Trust Boundary" in skill_text
    assert (tmp_path / ".agents/skills/ethos-skill-portfolio-governance/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/ethos-adoption-profile-governance/SKILL.md").exists()


def _assert_generated_artifact_scaffold(tmp_path: Path) -> None:
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    generated_policy = (tmp_path / ".config/ethos/generated-artifacts.toml").read_text(
        encoding="utf-8"
    )
    evidence_docs = (tmp_path / "docs/evidence/README.md").read_text(encoding="utf-8")

    for denied_root in (
        ".import_linter_cache/",
        ".import-linter-cache/",
        ".pytest_cache/",
        ".ruff_cache/",
        ".mypy_cache/",
        ".tox/",
        ".nox/",
        ".uv-cache/",
        "dist/",
    ):
        assert denied_root in gitignore
    for semantic_home in (
        'tool_cache = "build/runtime/tool-cache/<tool>"',
        'provider_work = "build/runtime/work/<provider>"',
        'machine_evidence = "build/evidence/<concern>"',
        'local_artifact = "build/artifacts/<kind>"',
        "lifecycle.runtime_cache",
        "lifecycle.curated_evidence",
    ):
        assert semantic_home in generated_policy
    assert "Machine output belongs under ignored homes" in evidence_docs
    assert "`build/evidence/`" in evidence_docs
    assert "never promoted" in evidence_docs


def _assert_generated_docs_and_openspec(tmp_path: Path) -> None:
    assert "Authority" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "ethos prove" in (tmp_path / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "Unreleased" in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "ethos status" in (tmp_path / "docs/start/quickstart.md").read_text(encoding="utf-8")
    assert not (tmp_path / "docs/governance/README.md").exists()
    assert not (tmp_path / "docs/plans/README.md").exists()
    assert "Decision Records" in (tmp_path / "docs/decisions/README.md").read_text(encoding="utf-8")
    assert "docs/governance" in (tmp_path / "docs/README.md").read_text(encoding="utf-8")
    capability = (tmp_path / "openspec/specs/repository-governance/capability.toml").read_text(
        encoding="utf-8"
    )
    assert "primary_invariant" in capability
    assert "decision_axes" in capability
    assert "[recommended_facets]" in capability
    assert "OpenSpec Workspace" in (tmp_path / "openspec/README.md").read_text(encoding="utf-8")
    assert "Change Template" in (tmp_path / "openspec/changes/template.md").read_text(
        encoding="utf-8"
    )


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

    assert result["applied"] is True
    _assert_required_scaffold_files_exist(tmp_path, set(result["planned_files"]))
    _assert_generated_skill_scaffold(tmp_path)
    _assert_generated_artifact_scaffold(tmp_path)
    _assert_generated_docs_and_openspec(tmp_path)


def test_adopt_apply_extends_existing_gitignore_without_conflict(
    tmp_path: Path,
) -> None:
    (tmp_path / ".gitignore").write_text(
        ".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8"
    )

    result = adoption_plan(tmp_path, profile="generic", apply=True)

    assert result["applied"] is True
    gitignore_plan = next(item for item in result["write_plan"] if item["path"] == ".gitignore")
    assert gitignore_plan["action"] == "merge_gitignore"
    assert gitignore_plan["conflict"] is False
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert gitignore.startswith(".ethos/state/*\n!.ethos/state/.gitignore\n")
    assert ".import_linter_cache/" in gitignore
    assert "build/" in gitignore


def test_adopt_apply_extends_existing_gitignore_idempotently(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(
        ".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8"
    )

    first = adoption_plan(tmp_path, profile="generic", apply=True)
    second = adoption_plan(tmp_path, profile="generic", apply=True)

    assert first["applied"] is True
    assert second["applied"] is True
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert gitignore.count(".import_linter_cache/") == 1
    assert gitignore.count("# Semantic ignored generated homes") == 1


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

    skill = (tmp_path / ".agents/skills/ethos-repository-governance/SKILL.md").read_text(
        encoding="utf-8"
    )

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
