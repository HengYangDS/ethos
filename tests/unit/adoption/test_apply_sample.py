from __future__ import annotations

import hashlib
import tomllib
from typing import TYPE_CHECKING

from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.adoption.scaffold.core import BASE_ADOPTION_FILES
from ethos.repository.adoption.scaffold.core import OPENSPEC_CAPABILITIES
from ethos.repository.policy.gates import ADOPTER_DEFAULT_GATE_IDS
from ethos.repository.policy.gates import PRODUCT_DEFAULT_GATE_IDS
from ethos.repository.policy.gates import _adopter_profile_active
from ethos.repository.policy.gates import default_gate_ids
from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path


def _assert_required_scaffold_files_exist(tmp_path: Path, planned: set[str]) -> None:
    required = set(BASE_ADOPTION_FILES) | {".gitlab-ci.yml"}
    required.update(
        f"openspec/specs/{family}/{name}"
        for family in OPENSPEC_CAPABILITIES
        for name in ("spec.md", "capability.toml")
    )
    assert required <= planned
    assert all((tmp_path / relative).exists() for relative in required)


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


def test_adopt_apply_makes_a_recognized_adopter_with_the_adopter_floor(
    tmp_path: Path,
) -> None:
    """A freshly scaffolded repository must be a recognized ETHOS adopter that gets the
    adopter proof floor — not left in a no-mans-land where it is neither the product nor
    an adopter and is handed the product-owned floor it can never run. The scaffolded
    .ethos/profile.toml is the binding-manifest entrypoint that makes this true."""
    result = adoption_plan(tmp_path, apply=True)
    assert result["applied"] is True

    profile = load_repository_profile(tmp_path)
    assert (tmp_path / ".ethos/profile.toml").exists()
    assert profile.exists is True
    assert profile.valid is True
    assert profile.identity.get("profile_id") == tmp_path.name
    assert profile.tables["openspec"]["material_paths"] == [
        ".ethos/profile.toml",
        "openspec/**",
        "docs/governance/**",
        "rules/**",
    ]
    assert f'name = "{tmp_path.name}"' in (tmp_path / ".ethos/project.toml").read_text(
        encoding="utf-8"
    )
    assert _adopter_profile_active(tmp_path) is True

    floor = default_gate_ids(root=tmp_path)
    assert floor == ADOPTER_DEFAULT_GATE_IDS
    assert floor != PRODUCT_DEFAULT_GATE_IDS


def test_adopt_apply_writes_complete_governance_skeleton(tmp_path: Path) -> None:
    (tmp_path / ".gitlab").mkdir()

    result = adoption_plan(tmp_path, profile="gitlab", apply=True)

    assert result["applied"] is True
    _assert_required_scaffold_files_exist(tmp_path, set(result["planned_files"]))
    _assert_generated_skill_scaffold(tmp_path)
    _assert_generated_artifact_scaffold(tmp_path)
    _assert_generated_docs_and_openspec(tmp_path)


def test_adopt_apply_omits_retired_projection_and_release_keys(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, profile="generic", apply=True)

    assert result["applied"] is True
    assert ".ethos/assistants.toml" not in result["planned_files"]
    assert not (tmp_path / ".ethos/assistants.toml").exists()
    project = tomllib.loads((tmp_path / ".ethos/project.toml").read_text(encoding="utf-8"))
    assert project["command_plane"] == {"public": "ethos"}
    release = tomllib.loads((tmp_path / ".ethos/release.toml").read_text(encoding="utf-8"))
    assert "release" not in release


def test_adopt_apply_merges_existing_gitignore_idempotently(
    tmp_path: Path,
) -> None:
    (tmp_path / ".gitignore").write_text(
        ".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8"
    )

    first = adoption_plan(tmp_path, profile="generic", apply=True)
    second = adoption_plan(tmp_path, profile="generic", apply=True)
    gitignore_plan = next(item for item in first["write_plan"] if item["path"] == ".gitignore")
    assert first["applied"] is True
    assert second["applied"] is True
    assert gitignore_plan["action"] == "merge_gitignore"
    assert gitignore_plan["conflict"] is False
    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert gitignore.startswith(".ethos/state/*\n!.ethos/state/.gitignore\n")
    assert ".import_linter_cache/" in gitignore
    assert "build/" in gitignore
    assert gitignore.count(".import_linter_cache/") == 1
    assert gitignore.count("# Semantic ignored generated homes") == 1


def test_overlay_adoption_preserves_existing_adopter_governance_surfaces(
    tmp_path: Path,
) -> None:
    preserved_contents = {
        "AGENTS.md": "# Existing agent entrypoint\n",
        "CONTRIBUTING.md": "# Existing contribution guide\n",
        "docs/README.md": "# Existing docs\n",
        "openspec/config.yaml": "schema: existing-adopter\n",
        "openspec/specs/kernel/spec.md": "# Existing OpenSpec\n",
        ".gitlab-ci.yml": "stages: [test]\n",
    }
    for relative, content in preserved_contents.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    strict = adoption_plan(tmp_path, profile="gitlab", apply=True)

    assert strict["applied"] is False
    assert "adoption_conflict:AGENTS.md" in strict["required_gaps"]

    overlay = adoption_plan(tmp_path, profile="gitlab", overlay=True, apply=True)

    assert overlay["applied"] is True
    assert overlay["mode"] == "overlay"
    preserved = {item["path"]: item for item in overlay["preserved_files"]}
    assert set(preserved_contents) <= set(preserved)
    for relative, content in preserved_contents.items():
        assert (tmp_path / relative).read_text(encoding="utf-8") == content
        assert preserved[relative]["sha256"] == hashlib.sha256(content.encode()).hexdigest()
    assert (tmp_path / ".ethos" / "profile.toml").exists()
    assert (tmp_path / ".agents" / "skills" / "activation.toml").exists()
    assert not (tmp_path / "docs" / "index.md").exists()
    assert not (tmp_path / "openspec" / "specs" / "repository-governance" / "spec.md").exists()
    assert "docs/index.md" in overlay["skipped_files"]
    assert "openspec/specs/repository-governance/spec.md" in overlay["skipped_files"]


def test_overlay_adoption_keeps_ethos_owned_conflicts_blocking(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text("profile_id = 'foreign'\n", encoding="utf-8")

    result = adoption_plan(tmp_path, overlay=True, apply=True)

    assert result["applied"] is False
    assert "adoption_conflict:.ethos/profile.toml" in result["required_gaps"]


def test_overlay_adoption_skips_missing_provider_projection_and_writes_empty_binding(
    tmp_path: Path,
) -> None:
    (tmp_path / ".gitlab").mkdir()
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("", encoding="utf-8")

    result = adoption_plan(tmp_path, profile="gitlab", overlay=True, apply=True)

    actions = {item["path"]: item["action"] for item in result["write_plan"]}
    assert result["applied"] is True
    assert actions[".gitlab-ci.yml"] == "preserve_adopter_root"
    assert actions[".ethos/profile.toml"] == "write_empty"
    assert profile.read_text(encoding="utf-8")


def _assert_maintainer_loop(text: str) -> None:
    for command in (
        "ethos status",
        "ethos plan --changed",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ):
        assert command in text
    assert "ethos report" in text
    assert "ethos prove --execute" not in text
    assert "ethos quality" not in text


def test_generated_quickstart_teaches_first_hour_not_maintainer_checks(
    tmp_path: Path,
) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)
    _assert_maintainer_loop(
        (tmp_path / "docs/start/quickstart.md")
        .read_text(encoding="utf-8")
        .split("## Maintainer Reference", 1)[0]
    )


def test_generated_skill_loop_uses_workflow_plus_scorecard(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)
    _assert_maintainer_loop(
        (tmp_path / ".agents/skills/ethos-repository-governance/SKILL.md").read_text(
            encoding="utf-8"
        )
    )


def test_adopt_rules_use_single_kernel_governance_entrypoints(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    rules = (tmp_path / ".ethos/rules.toml").read_text(encoding="utf-8")
    rules_data = tomllib.loads(rules)
    report = rules_check_report(tmp_path)

    assert rules_data["profiles"]["active"] == ["generic"]
    assert report["legacy"]["legacy_detected"] is False
    assert 'governance_audit = "ethos report --json"' in rules
    assert 'proof = "ethos prove --json"' in rules
    assert 'self_audit = "ethos self audit --json"' not in rules
