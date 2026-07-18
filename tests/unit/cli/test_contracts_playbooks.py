from __future__ import annotations

import tomllib
from pathlib import Path

from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.playbooks import OFFICIAL_PLAYBOOK_SKILL
from tests.support.playbooks import write_v2_playbook_package


def test_playbooks_commands_expose_repo_local_skills() -> None:
    check = run_ethos("playbooks", "check", "--json")
    route = run_ethos("playbooks", "route", "--subject", "repository-governance", "--json")

    assert check["ok"] is True
    assert check["data"]["skills_root"] == ".agents/skills"
    assert {
        "ethos-repository-governance",
        "ethos-change-lifecycle",
        "ethos-skill-portfolio-governance",
        "ethos-quality-gate-governance",
        "ethos-adoption-profile-governance",
    } <= set(check["data"]["skills"])
    assert check["data"]["coverage"]["record_count"] == 5
    assert "skill-portfolio" in check["data"]["coverage"]["subjects"]
    assert check["data"]["portfolio_coverage"]["ok"] is True
    assert check["data"]["portfolio_coverage"]["contract"]["required_primary_subjects"] == [
        "repository-governance",
        "change-lifecycle",
        "skill-portfolio",
        "quality-gates",
        "adoption-profile",
    ]
    assert check["data"]["portfolio_coverage"]["owners"]["skill-portfolio"] == [
        "ethos-skill-portfolio-governance"
    ]
    assert route["ok"] is True
    assert route["data"]["selected"][0]["id"] == "ethos-repository-governance"


def test_playbooks_portfolio_coverage_ignores_invalid_subject_list_type(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "repository-governance"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[coverage]
required_primary_subjects = "repository-governance"
single_owner_subjects = "repository-governance"

[[skill]]
id = "repository-governance"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["portfolio_coverage"]["contract"] == {
        "required_primary_subjects": [],
        "single_owner_subjects": [],
    }


def test_playbooks_strict_mode_requires_portfolio_primary_subjects(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "repository-governance"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[coverage]
required_primary_subjects = ["repository-governance", "quality-gates"]
single_owner_subjects = ["repository-governance", "quality-gates"]

[[skill]]
id = "repository-governance"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is False
    assert "skill_portfolio_subject_missing:quality-gates" in payload["required_gaps"]
    assert payload["data"]["portfolio_coverage"]["ok"] is False
    assert payload["data"]["portfolio_coverage"]["owners"] == {
        "repository-governance": ["repository-governance"]
    }


def test_playbooks_strict_mode_rejects_duplicate_primary_subject_owner(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    first_manifest = Path(write_v2_playbook_package(skills_root, "repository-governance"))
    second_manifest = Path(write_v2_playbook_package(skills_root, "repository-governance-helper"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[coverage]
required_primary_subjects = ["repository-governance"]
single_owner_subjects = ["repository-governance"]

[[skill]]
id = "repository-governance"
package_manifest = "{first_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"

[[skill]]
id = "repository-governance-helper"
package_manifest = "{second_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["rules/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is False
    assert (
        "skill_portfolio_subject_duplicate:repository-governance:"
        "repository-governance,repository-governance-helper"
    ) in payload["required_gaps"]
    assert payload["data"]["portfolio_coverage"]["owners"]["repository-governance"] == [
        "repository-governance",
        "repository-governance-helper",
    ]


def test_playbooks_accept_repo_local_activation_schema_with_path_globs(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    package_manifest = Path(write_v2_playbook_package(skills_root, "code-change"))
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "code-change"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "implementation"
operation = "implement"
authority = "primary"
lifecycle = "active"
path_globs = ["src/**"]
intent_tokens = ["implement"]
pre_reads = ["README.md"]
post_checks = ["ethos prove"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add playbook routing",
    )
    (root / "src").mkdir()
    (root / "src" / "code.py").write_text("VALUE = 1\n", encoding="utf-8")

    check = run_ethos("playbooks", "check", "--root", root.as_posix(), "--json")
    route = run_ethos("playbooks", "route", "--changed", "--root", root.as_posix(), "--json")

    assert check["ok"] is True
    assert check["data"]["records"][0]["id"] == "code-change"
    assert check["data"]["records"][0]["path_globs"] == ["src/**"]
    assert "changed-scope" in check["data"]["records"][0]["subjects"]
    assert route["ok"] is True
    assert route["data"]["selected"][0]["id"] == "code-change"
    assert "changed-scope" in route["data"]["selected"][0]["subjects"]
    assert route["data"]["selected"][0]["pre_reads"] == ["README.md"]
    assert route["data"]["selected"][0]["post_checks"] == ["ethos prove"]
    assert route["data"]["selected"][0]["matched_paths"] == ["src/code.py"]


def test_product_playbook_activation_routes_evolution_campaigns() -> None:
    activation = tomllib.loads(Path(".agents/skills/activation.toml").read_text(encoding="utf-8"))
    record = next(
        item for item in activation["skill"] if item["id"] == "ethos-repository-governance"
    )

    skill_record = next(
        item for item in activation["skill"] if item["id"] == "ethos-skill-portfolio-governance"
    )

    assert "evolution/**" in record["path_globs"]
    assert ".agents/skills/**" not in record["path_globs"]
    assert ".agents/skills/**" in skill_record["path_globs"]


def test_playbooks_changed_scope_route_requires_explicit_subject(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "ethos-repository-governance"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "ethos-repository-governance"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["changed_paths"] == []


def test_playbooks_changed_scope_route_ignores_id_and_subject_substrings(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "changed-scope-helper"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "changed-scope-helper"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "changed-scope-shadow"
operation = "inspect"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["changed_paths"] == []


def test_playbooks_route_rejects_name_only_activation_entries(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "changed-scope-router" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Changed Scope Router\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "changed-scope-router"
path = ".agents/skills/changed-scope-router/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["src/**"]
commands = ["ethos playbooks route --changed"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add unsupported route",
    )
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert "skill_missing_id" in payload["required_gaps"]
    assert "playbook_activation_unsupported_version:1" in payload["required_gaps"]


def test_playbooks_strict_mode_rejects_activation_path_escape(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "escape-skill"))
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "escape-skill"
path = "../outside/SKILL.md"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is False
    assert "playbook_skill_path_escape:escape-skill" in payload["required_gaps"]


def test_playbooks_strict_mode_requires_activation_path_to_match_package_entrypoint(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    package_manifest = Path(write_v2_playbook_package(skills_root, "entrypoint-skill"))
    alternate = skills_root / "entrypoint-skill" / "ALT.md"
    alternate.write_text(OFFICIAL_PLAYBOOK_SKILL, encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        f"""
[meta]
version = 2

[[skill]]
id = "entrypoint-skill"
path = ".agents/skills/entrypoint-skill/ALT.md"
package_manifest = "{package_manifest.relative_to(root).as_posix()}"
subject = "repository-governance"
operation = "govern"
authority = "primary"
lifecycle = "active"
path_globs = ["docs/**"]
pre_reads = ["README.md"]
post_checks = ["ethos report --json"]
commands = ["ethos status"]
boundary = "workflow-package-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is False
    assert "skill_package_entrypoint_mismatch:entrypoint-skill" in payload["required_gaps"]


def test_playbooks_report_rejects_name_only_skill_activation(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "unsupported-router" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Unsupported Router\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[[skill]]
name = "unsupported-router"
subjects = ["repository-governance"]
commands = ["ethos status"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("playbooks", "check", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert "skill_missing_id" in payload["required_gaps"]
    assert "playbook_activation_unsupported_version:1" in payload["required_gaps"]


def test_playbooks_strict_mode_rejects_placeholder_v1_skill(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    skill_path = skills_root / "placeholder" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text("# Placeholder\n\nThin routing note.\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[meta]
version = 1

[[skill]]
id = "placeholder"
path = ".agents/skills/placeholder/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["src/**"]
commands = ["ethos status"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos(
        "playbooks",
        "check",
        "--mode",
        "v2-strict",
        "--root",
        str(root),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["data"]["mode"] == "v2-strict"
    assert "playbook_activation_unsupported_version:1" in payload["required_gaps"]
    assert "skill_package_manifest_missing:placeholder" in payload["required_gaps"]
    assert "skill_quality_missing_frontmatter:placeholder" in payload["required_gaps"]


def test_playbooks_removed_compatibility_mode_is_not_available(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")

    completed = run_ethos_raw(
        "playbooks",
        "route",
        "--changed",
        "--mode",
        "compat",
        "--root",
        str(root),
        "--json",
    )

    assert completed.returncode != 0
    assert "unsupported playbook mode: compat" in completed.stderr


def test_report_uses_strict_playbooks_for_external_adopter_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    skills_root = root / ".agents" / "skills"
    skill_path = skills_root / "unsupported-router" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("# Unsupported Router\n", encoding="utf-8")
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        """
[meta]
version = 1

[[skill]]
name = "unsupported-router"
path = ".agents/skills/unsupported-router/SKILL.md"
subjects = ["changed-scope"]
path_globs = ["src/**"]
commands = ["ethos playbooks route --changed"]
boundary = "thin-playbook-projection"
""".lstrip(),
        encoding="utf-8",
    )

    payload = run_ethos("report", "--root", str(root), "--json")

    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert payload["data"]["playbooks"]["mode"] == "v2-strict"
    assert "skill_missing_id" in payload["data"]["playbooks"]["required_gaps"]
    assert (
        "playbook_activation_unsupported_version:1" in payload["data"]["playbooks"]["required_gaps"]
    )


def test_product_playbooks_strict_mode_passes_after_v2_migration() -> None:
    payload = run_ethos("playbooks", "check", "--mode", "v2-strict", "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["registry"]["digest"].startswith("sha256:")
    assert payload["data"]["package_quality"]["ok"] is True


def test_playbooks_v2_gate_can_execute() -> None:
    payload = run_ethos("prove", "--execute", "--gate", "playbooks-v2", "--json")

    assert payload["ok"] is True
    assert payload["data"]["executed"] is True
    assert payload["data"]["evidence"]["runs"][0]["action_id"] == "playbooks-v2"
    assert payload["data"]["evidence"]["runs"][0]["state"] == "proven"
